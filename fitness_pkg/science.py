# -*- coding: utf-8 -*-
"""
训练科学规则层 (v9.1 新增) — 把 Lzheng-fitness 知识库里的判断规则收敛为可配置、可测试的参数。

覆盖来源:
- Eric Helms《训练金字塔 v2.0》
  Level 2 训练量 (每肌群/动作模式每周 10–20 组起始区间, 非上限)
  Level 2 强度与 RPE/RIR (RPE10 = 0 RIR, 9 ≈ 1 RIR, 8 ≈ 2 RIR, 7 ≈ 3 RIR)
  Level 3 训练年龄与减载 (反应式减载清单: 0–1 项前进, 2+ 项减载; 连续 3 个中周期未减载则预防性减载)
  Level 5 组间休息 (小肌群 ≥1.5 min, 复合主项 ≥2.5 min; 拮抗肌配对组省时但不牺牲主项质量)
- Brad Schoenfeld《增肌科学》
  大多数组保留约 1–2 RIR, 力竭只选择性放在最后一组; 多关节动作比单关节更谨慎
  一次只改变一个主要变量并观察 2–4 周趋势
  全活动范围是基础, 拉长位刺激优先; 刻意超慢节奏不是默认更优
- Greg Nuckols《Stronger by Science》
  训练量是可检验剂量而非固定靶值; 真平台且恢复良好时每次只加 1–2 组
  AMRAP / e1RM 趋势性评估优于频繁硬测 1RM; 变量改变必须是一次可验证实验
  自动调节 (RPE / 回退组表现) 处理当日波动, 但不替代长期记录
- Dan John《Intervention》
  缺口审计 (推/拉/髋铰链/深蹲/负重行走/单腿) 用作训练审计表; 只做最小必要纠正
- Lzheng 自有规则
  一次只优先改变重量/次数/组数中的一个主要变量; 短版不补课; 疼痛与危险信号先安全分流

设计约定:
- 仅使用标准库, 不引入新依赖; 不依赖 PySide6, 可被 CLI 脚本与测试直接导入。
- 本模块只做“规则 → 参数”的换算与判定, 不读写个人数据、不引入随机性 (对给定输入确定性输出)。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════
# 一、RPE / RIR 换算与负荷-次数表
# ═══════════════════════════════════════════════════════════

# RPE → 剩余可完成次数 (RIR)。来源: Helms, 训练金字塔 v2.0, pp.64-65
# 口径: RPE 10 ≈ 0 RIR, 9 ≈ 1 RIR, 8 ≈ 2 RIR, 7 ≈ 3 RIR; 半档 (.5) 取更保守的一侧
RPE_TO_RIR: Dict[float, int] = {
    10.0: 0, 9.5: 0, 9.0: 1, 8.5: 1, 8.0: 2, 7.5: 3, 7.0: 3, 6.5: 4, 6.0: 4, 5.0: 5,
}

# 次数 → 最大可完成次数百分比 (Helms 表 2.2 的简化刻度, 用于按次数反推负荷)
REPS_TO_PCT_1RM: Dict[int, float] = {
    1: 1.000, 2: 0.955, 3: 0.925, 4: 0.900, 5: 0.875,
    6: 0.855, 7: 0.833, 8: 0.812, 9: 0.792, 10: 0.774,
    11: 0.758, 12: 0.742, 13: 0.727, 14: 0.714, 15: 0.700,
    16: 0.688, 17: 0.675, 18: 0.663, 19: 0.652, 20: 0.641,
}

# 目标 RPE 相对“表内最大次数”的负荷折减系数 (每少留 1 RIR 大约多扛 2–3% 负荷)
RIR_LOAD_STEP = 0.025

# e1RM 计算口径说明:
#   1) 先把实际重量折算成“当天力竭会用的重量”  实际重量 / (1 + RIR×步长)
#   2) 再按“实际次数 + RIR”作为到力竭等效次数套 Epley 公式
# 该口径与 reps_to_intensity / load_for_target_reps 互逆, 且离力竭越远 e1RM 越高。
# 说明: RIR=0 时退化为标准 Epley, 所有估算只用于趋势观察与起点建议, 不替代实测。
RIR_EFFORT_REPS = 0

# 动作类型: 决定力竭使用与休息下限 (Schoenfeld: 多关节更谨慎; Helms: 复合休息更长)
COMPOUND_KEYWORDS = (
    '深蹲', '硬拉', '卧推', '推举', '引体', '划船', '分腿蹲', '弓步',
    '蹲', '拉', '推', 'squat', 'deadlift', 'bench', 'press', 'row', 'pull',
)
ISOLATION_KEYWORDS = (
    '弯举', '臂屈伸', '下压', '飞鸟', '侧平举', '前平举', '面拉', '提踵',
    '腿屈伸', '腿弯举', '夹胸', 'curl', 'raise', 'fly', 'pushdown', 'extension',
)

# 休息时长下限 (秒)。来源: Helms, Level 5, pp.171-187
REST_SECONDS = {
    'compound': (150, 300),   # 复合主项 ≥2.5 min, 上限 5 min
    'isolation': (90, 180),   # 小肌群/孤立动作 ≥1.5 min
}

# RPE 上限: 多关节动作常规不做到力竭; 孤立动作仅末组可接近力竭
MAX_RPE = {
    'compound': 9.0,
    'isolation': 9.5,
}


def classify_movement(movement: str) -> str:
    """把动作名粗分为 compound / isolation, 用于选择休息与 RPE 上限。"""
    name = movement or ''
    for kw in ISOLATION_KEYWORDS:
        if kw in name:
            return 'isolation'
    for kw in COMPOUND_KEYWORDS:
        if kw in name:
            return 'compound'
    return 'compound'


def rpe_to_rir(rpe: float) -> int:
    """RPE → RIR (剩余可完成次数)。

    RPE 为半档 (.5) 时取相邻两档中更保守 (RIR 更多) 的一侧, 避免高估训练者的余力。
    """
    value = float(rpe)
    if value in RPE_TO_RIR:
        return RPE_TO_RIR[value]
    ceil_key = min((k for k in RPE_TO_RIR if k >= value), default=max(RPE_TO_RIR))
    floor_key = max((k for k in RPE_TO_RIR if k <= value), default=min(RPE_TO_RIR))
    return min(RPE_TO_RIR[floor_key], RPE_TO_RIR[ceil_key])


def rpe_to_rir_text(rpe: float) -> str:
    """RPE → 可读的 RPE/RIR 双标注, 例如 'RPE 8 (≈2 RIR)'。"""
    rir = rpe_to_rir(rpe)
    return f'RPE {_fmt_rpe(rpe)} (≈{rir} RIR)'


def _fmt_rpe(rpe: float) -> str:
    return str(int(rpe)) if float(rpe).is_integer() else f'{rpe:g}'


def reps_to_intensity(reps: int, target_rpe: float = 8.0) -> float:
    """按目标次数与目标 RPE 估算相对 1RM 的强度百分比。

    依据: 次数-负荷表给出“到力竭”的百分比; 目标 RPE 保留 RIR, 保留越多负荷越低。
    估算值只用于无 1RM 记录时的起点建议, 不是精确处方 (Nuckols: 用表现而非公式定负荷)。

    与 `e1rm_from_set` 使用同一 RIR 锚点 (见 RIR_EFFORT_REPS), 因此二者互为逆运算:
    用任一 RPE 反推的 e1RM 再按同一次数/RPE 折算回来, 会回到原始重量。
    """
    reps = max(1, int(reps))
    key = max(REPS_TO_PCT_1RM)
    pct = REPS_TO_PCT_1RM.get(reps, REPS_TO_PCT_1RM[key] - 0.01 * (reps - key))
    pct = pct / (1.0 + rir_adjust_factor(target_rpe))
    return round(pct, 3)


def rir_adjust_factor(target_rpe: float) -> float:
    """由 RIR 折算的负荷折减因子 (保留 3 RIR 约降 6%, 保留 1 RIR 约降 2%)。"""
    return rpe_to_rir(target_rpe) * RIR_LOAD_STEP


def e1rm_from_set(weight: float, reps: int, rpe: float = 8.0) -> float:
    """由一组记录估算 e1RM。

    口径: `e1RM = 实际重量 × (1 + 实际次数 / 30) / (1 + RIR × 步长)`
    —— RIR 保留越多, 该重量相对 1RM 的比例越低, 折算出的 e1RM 越高。
    与 `reps_to_intensity` / `load_for_target_reps` 互为逆运算, 保证同一口径自洽,
    避免旧实现把“保留次数”直接当成真实力竭次数而系统高估。
    仅用于趋势观察与起点建议, 不替代实测 (Nuckols: 用表现而不是公式定负荷)。
    """
    if reps <= 0 or weight <= 0:
        return 0.0
    if reps == 1:
        return round(float(weight), 2)
    rir = rpe_to_rir(rpe)
    # 折算到“当天力竭会用的重量”: 保留 RIR 越多, 说明当天还能加负荷
    effort_weight = float(weight) / (1.0 + rir_adjust_factor(rpe))
    # 再按“实际次数 + RIR”作为到力竭的等效次数套 Epley
    return round(effort_weight * (1.0 + (float(reps) + rir) / 30.0), 2)


def load_for_target_reps(e1rm: float, reps: int, target_rpe: float = 8.0) -> float:
    """给定 e1RM 与目标次数/RPE, 给出建议负荷 (0.5kg 精度)。"""
    if e1rm <= 0:
        return 0.0
    raw = e1rm * reps_to_intensity(reps, target_rpe)
    return round(raw * 2) / 2


# ═══════════════════════════════════════════════════════════
# 二、训练量区间 (Helms 每肌群/动作模式 10–20 组起始区间)
# ═══════════════════════════════════════════════════════════

WEEKLY_SET_BANDS = {
    'P0': (6, 10),     # 回归/动作学习期: 先建立可重复动作与基准
    'L1': (10, 14),    # 线性或双重渐进
    'L2': (12, 18),    # 按周管理变量
    'L3': (14, 20),    # 阶段化 + 疲劳管理
}

# 超过 20 组/周只在技术、睡眠、营养、压力、频率、努力度均可靠且确实需要突破平台时才试验
WEEKLY_SET_CEILING = 20
# 真平台且恢复良好时的单次加量步长 (Helms: 每次 1–2 组)
VOLUME_STEP = (1, 2)
# 反复低恢复时的减量比例 (Helms: 先把组数约减 20%)
VOLUME_DELOAD_RATIO = 0.2


def weekly_set_band(level: str) -> Tuple[int, int]:
    """按训练等级返回每周每肌群的起始组数区间。"""
    return WEEKLY_SET_BANDS.get((level or 'P0').upper(), WEEKLY_SET_BANDS['P0'])


def analyze_weekly_volume(level: str, planned_sets: int) -> Dict[str, Any]:
    """评估周组数是否处于该等级的起始区间内, 并给出调整方向。"""
    low, high = weekly_set_band(level)
    planned = max(0, int(planned_sets))
    if planned < low:
        verdict = '偏少'
        action = f'仍有空间逐步加到每周 {low}–{high} 组, 一次加 {VOLUME_STEP[0]}–{VOLUME_STEP[1]} 组'
    elif planned <= high:
        verdict = '合适'
        action = '维持当前周组数, 优先看表现与恢复趋势而不是继续加量'
    elif planned <= WEEKLY_SET_CEILING:
        verdict = '偏高'
        action = '仅在技术、睡眠、营养、压力与恢复均可靠时才保留, 并写明何时回退'
    else:
        verdict = '超出验证区间'
        action = f'超过 {WEEKLY_SET_CEILING} 组/周需要专门试验与可归因的观察窗口, 否则先回到起始区间'
    return {
        'level': (level or 'P0').upper(),
        'planned_sets': planned,
        'band': (low, high),
        'ceiling': WEEKLY_SET_CEILING,
        'verdict': verdict,
        'action': action,
    }


# ═══════════════════════════════════════════════════════════
# 三、自动调节: 由实际表现反推当日负荷
# ═══════════════════════════════════════════════════════════

def autoregulated_set(
    weight: float,
    reps: int,
    rpe: float,
    target_reps: int,
    target_rpe: float = 8.0,
    level: str = 'L2',
) -> Dict[str, Any]:
    """按当日实际表现校正负荷 (APRE + RPE 自动调节, 目标导向而非“次数越多越重”)。

    规则 (Nuckols 自动调节 / Schoenfeld 一次只改一个变量):
    - 达到或超过目标次数且 RPE 在目标内 → 该重量不再“太重”, 只加一个最小重量档;
    - 达到目标但余力不足 (RPE 高于目标) → 维持, 先巩固适应;
    - 未达目标次数或 RPE 偏高 → 按 e1RM 折算到目标次数后下调;
    - 明显超出目标难度 (RPE ≥9.5 或比目标少 2 次以上) → 直接降约 5% 保住动作质量。
    """
    weight = max(0.0, float(weight))
    reps = max(0, int(reps))
    rpe = float(rpe)
    target_reps = max(1, int(target_reps))
    delta = target_reps - reps
    e1rm = e1rm_from_set(weight, reps, rpe) if reps > 0 else 0.0
    step = min_weight_step(weight)

    if rpe >= 9.5 or delta >= 2:
        new_weight = max(0.0, round(weight * 0.95 * 2) / 2)
        action = '降级'
        reason = f'RPE {_fmt_rpe(rpe)} 或比目标少 {delta} 次, 先降约 5% 保住动作质量'
    elif delta <= 0 and rpe > target_rpe:
        new_weight = round(weight * 2) / 2
        action = '维持'
        reason = f'完成了目标次数但 RPE {_fmt_rpe(rpe)} 高于目标 {_fmt_rpe(target_rpe)}, 先维持'
    elif delta <= 0 and rpe <= target_rpe - 0.5:
        new_weight = round((weight + step) * 2) / 2
        action = '上调'
        reason = f'达到目标次数且 RPE 低于目标半档以上, 只加一个最小重量档 {step}kg'
    elif delta <= 0:
        new_weight = round(weight * 2) / 2
        action = '维持'
        reason = f'完成目标次数且 RPE 正好落在目标 {_fmt_rpe(target_rpe)}, 巩固一次再加'
    else:
        ideal = load_for_target_reps(e1rm, target_reps, target_rpe)
        new_weight = round(ideal * 2) / 2
        action = '降级'
        reason = f'比目标少 {delta} 次, 按当前表现折算到 {target_reps} 次 @RPE {_fmt_rpe(target_rpe)}'

    if new_weight <= 0:
        new_weight = round(weight * 2) / 2

    if delta <= 0 and rpe <= target_rpe - 0.5:
        stability = 1.0
    elif abs(delta) <= 1 and rpe <= target_rpe + 0.5:
        stability = 0.5
    else:
        stability = 0.0

    return {
        'suggested_weight': new_weight,
        'action': action,
        'reason': reason,
        'e1rm': e1rm,
        'stability': round(stability, 2),
        'step': step,
        'rir': rpe_to_rir(rpe),
        'level': (level or 'L2').upper(),
    }


def min_weight_step(weight: float) -> float:
    """按当前负重给出最小加重单位 (kg)。"""
    if weight <= 20:
        return 1.0
    if weight <= 60:
        return 2.5
    return 5.0


def apply_double_progression(
    weight: float,
    reps: int,
    sets: int,
    rpe: float,
    rep_window: Tuple[int, int] = (8, 12),
    is_isolation: bool = True,
) -> Dict[str, Any]:
    """双重渐进: 先把所有组做到次数区间上限, 再加最小重量档。

    Schoenfeld/Helms: 孤立与小肌群动作优先用双重渐进; 复合动作更常用线性/波浪周期。
    """
    weight = max(0.0, float(weight))
    reps = int(reps)
    sets = max(1, int(sets))
    rpe = float(rpe)
    lo, hi = rep_window
    step = min_weight_step(weight)
    rx: Dict[str, Any] = {'sets': sets, 'movement_sets': sets, 'weight': weight, 'reps': reps, 'rpe': rpe}

    if not is_isolation:
        rx['progression_type'] = '线性/波浪'
        rx['note'] = '复合主项优先在周期内按组次下降、负荷上升推进, 双重渐进只作辅助'
        return rx

    if reps < hi:
        rx.update({'reps': min(reps + 1, hi), 'rpe': min(round(rpe + 0.5, 1), MAX_RPE['isolation'])})
        rx['progression_type'] = '加次'
        rx['note'] = f'先把 {sets} 组都做到 {hi} 次上限 (当前 {reps} 次), 一次只加 1 次'
    else:
        rx.update({'weight': round((weight + step) * 2) / 2, 'reps': lo, 'rpe': max(6.0, round(rpe - 1.0, 1))})
        rx['progression_type'] = '加重'
        rx['note'] = f'次数已达上限, 加最小重量档 {step}kg 并让次数回落到 {lo} 次'
    return rx


# ═══════════════════════════════════════════════════════════
# 四、反应式减载清单 (Helms Level 3, pp.121-125)
# ═══════════════════════════════════════════════════════════

DELOAD_SIGNALS = (
    ('reluctance', '不想去训练'),
    ('sleep_worse', '睡眠比平常差'),
    ('performance_drop', '负荷或次数下降'),
    ('life_stress', '生活压力变大'),
    ('pain', '疼痛或不适加重'),
)
DELOAD_THRESHOLD = 2          # 2 项及以上 → 减载一周
PROACTIVE_DELOAD_CYCLES = 3   # 连续三个中周期未减载 → 预防性减载


def evaluate_deload_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    """按反应式减载清单给出“前进 / 减载一周 / 预防性减载”的结论。"""
    signals = signals or {}
    hit = [label for key, label in DELOAD_SIGNALS if signals.get(key)]
    count = len(hit)
    cycles_since = int(signals.get('cycles_since_deload', 0) or 0)

    if count >= DELOAD_THRESHOLD:
        verdict = '减载一周'
        action = '本周组数约减 20%, 保留主线动作与动作质量, 不测试极限; 下周按下一中周期继续'
    elif cycles_since >= PROACTIVE_DELOAD_CYCLES:
        verdict = '预防性减载'
        action = f'已连续 {cycles_since} 个中周期未减载, 安排一周低疲劳训练后再推进'
    else:
        verdict = '继续前进'
        action = '维持当前结构, 只让一个主要变量缓慢推进'

    return {
        'hit': hit,
        'count': count,
        'threshold': DELOAD_THRESHOLD,
        'cycles_since_deload': cycles_since,
        'volume_reduction': VOLUME_DELOAD_RATIO if verdict != '继续前进' else 0.0,
        'verdict': verdict,
        'action': action,
        'note': '一次状态差不等于平台期, 先核对睡眠/压力/休息/动作标准再改结构',
    }


# ═══════════════════════════════════════════════════════════
# 五、组内结构: 热身流程 / 多组 RPE 路径 / 组间休息 / 力竭使用
# ═══════════════════════════════════════════════════════════

WARMUP_SPEC = (
    ('空杆/最轻负荷', 10, 5.0),
    ('40% e1RM', 5, 5.0),
    ('60% e1RM', 3, 6.0),
    ('80% e1RM', 1, 7.0),
)


def build_warmup_sets(e1rm: float) -> List[Dict[str, Any]]:
    """生成热身流程: 逐级递增且不产生明显疲劳。"""
    if e1rm <= 0:
        return [{'label': '空杆/最轻负荷', 'weight': 0.0, 'reps': 10, 'rpe': 5.0}]
    plan = []
    for label, reps, rpe in WARMUP_SPEC:
        if label.startswith('空杆') or label.startswith('最轻'):
            plan.append({'label': label, 'weight': 0.0, 'reps': reps, 'rpe': rpe})
            continue
        pct = {'40% e1RM': 0.4, '60% e1RM': 0.6, '80% e1RM': 0.8}[label]
        w = round(e1rm * pct * 2) / 2
        if plan and w <= plan[-1]['weight']:
            continue
        plan.append({'label': label, 'weight': w, 'reps': reps, 'rpe': rpe})
    return plan


def build_rpe_path(working_sets: int, start_rpe: float, end_rpe: float) -> List[float]:
    """生成逐组 RPE 路径 (首组→末组), 避免把整组疲劳压成一个静态数字。

    Helms/Lzheng: 多组处方写 `首组 RPE→末组 RPE`; 中间组线性递增。
    """
    working_sets = max(1, int(working_sets))
    start = float(start_rpe)
    end = max(float(end_rpe), start)
    if working_sets == 1:
        return [round(end, 1)]
    step = (end - start) / (working_sets - 1)
    return [round(start + step * i, 1) for i in range(working_sets)]


def rest_seconds(movement: str, is_last_set: bool = False) -> Tuple[int, int]:
    """返回该动作的组间休息区间 (秒)。复合主项不因省时而压缩。"""
    kind = classify_movement(movement)
    lo, hi = REST_SECONDS[kind]
    if is_last_set:
        hi = max(lo, hi - 30)
    return lo, hi


def planned_rest_plan(movement: str, working_sets: int) -> List[Dict[str, Any]]:
    """为每组给出休息建议, 并标注拮抗肌配对组的省时用法。"""
    kind = classify_movement(movement)
    lo, hi = REST_SECONDS[kind]
    plan = []
    for i in range(max(1, int(working_sets))):
        is_last = i == max(1, int(working_sets)) - 1
        plan.append({
            'set_index': i + 1,
            'rest_low': lo,
            'rest_high': hi if not is_last else max(lo, hi - 30),
            'super_set': '可与拮抗肌动作配对省时' if kind == 'isolation' else '不要插入其他训练',
        })
    return plan


def failure_allowance(movement: str, set_index: int, working_sets: int) -> Dict[str, Any]:
    """说明该组是否允许接近力竭。

    Schoenfeld: 大多数组保留 1–2 RIR, 力竭只选择性放在最后一组;
    多关节动作更谨慎, 孤立动作末组可接近力竭。
    """
    kind = classify_movement(movement)
    is_last = set_index >= max(1, int(working_sets))
    cap = MAX_RPE[kind]
    if kind == 'compound':
        allow = False
        note = f'复合主项常规不做力竭, 末组也建议停在 {rpe_to_rir_text(cap)}'
    elif is_last:
        allow = True
        note = f'孤立动作末组可接近力竭 ({rpe_to_rir_text(cap)}), 前序组保留 1–2 RIR'
    else:
        allow = False
        note = '孤立动作前序组保留 1–2 RIR, 把力竭留给末组'
    return {'movement_kind': kind, 'set_index': set_index, 'max_rpe': cap,
            'allow_failure': allow, 'note': note}


def tempo_prescription(is_compound: bool = True, goal: str = '增肌') -> Dict[str, Any]:
    """节奏建议: 可控离心 + 全活动范围, 不刻意追求超慢节奏。"""
    if goal == '力量':
        return {'eccentric': '2 秒', 'pause': '按项目要求', 'concentric': '有力', 'note': '力量目标以技术稳定和专项性优先, 不做额外慢速离心'}
    if is_compound:
        return {'eccentric': '2 秒', 'pause': '底部 0–1 秒', 'concentric': '有力可控', 'note': '全活动范围, 注意拉长位控制, 不做刻意的 4 秒超慢离心'}
    return {'eccentric': '2–3 秒', 'pause': '收缩位 0–1 秒', 'concentric': '有力可控', 'note': '孤立动作可用 2–3 秒离心, 但不要用慢速替代负荷渐进'}


# ═══════════════════════════════════════════════════════════
# 六、指标趋势与安全分流
# ═══════════════════════════════════════════════════════════

class FatigueSignal:
    """疲劳信号常量 (供 GUI / 复盘文案复用)。"""
    RELUCTANCE = 'reluctance'
    SLEEP_WORSE = 'sleep_worse'
    PERFORMANCE_DROP = 'performance_drop'
    LIFE_STRESS = 'life_stress'
    PAIN = 'pain'


RED_FLAG_KEYWORDS = (
    '胸部不适', '胸痛', '晕厥', '异常气短', '麻木', '放射痛', '锐痛',
    '功能受限', '持续加重', '夜间痛', '关节肿胀', '腰痛伴腿麻',
)


def screen_action(text: str) -> Optional[str]:
    """安全筛查: 命中危险信号时返回分流建议, 否则返回 None。"""
    text = text or ''
    for kw in RED_FLAG_KEYWORDS:
        if kw in text:
            return (f'出现「{kw}」类描述时暂停常规高强度训练, '
                    '本项目不作医疗诊断, 请先寻求专业评估后再接回正常处方')
    return None


def detect_stall(history: List[Dict[str, Any]], threshold: int = 2) -> Dict[str, Any]:
    """检测真实停滞: 同重量次数下降, 或同组次 RPE 上升约一级, 连续达到阈值次。

    Lzheng: 连续两次同类异常才优先怀疑周期结构; 单次异常先核对睡眠/压力/休息/动作标准。
    不同重量或不同器械的记录不能机械比较, 只比较同一重量段的相邻记录。
    """
    usable = [h for h in (history or []) if h and h.get('weight') and h.get('reps')]
    usable = usable[-max(threshold + 1, 3):]
    flags = 0
    details: List[str] = []
    for prev, cur in zip(usable, usable[1:]):
        if cur['weight'] != prev['weight']:
            continue
        reps_drop = cur['reps'] < prev['reps']
        rpe_up = float(cur.get('rpe', 0) or 0) >= float(prev.get('rpe', 0) or 0) + 1.0
        if reps_drop or rpe_up:
            flags += 1
            details.append(
                f'第 {cur.get("index", "?")} 次记录出现'
                + ('同重量掉次数' if reps_drop else '同组次 RPE 上升约一级')
            )
    return {
        'is_stall': flags >= threshold,
        'flags': flags,
        'threshold': threshold,
        'details': details,
        'hint': '真实停滞且恢复良好时才优先考虑结构变化 (先加 1–2 组或调整分布), 单次异常只维持观察',
    }


def detect_plateau(
    e1rm_trend: List[float],
    sessions: int = 6,
    min_change_pct: float = 0.0,
) -> Dict[str, Any]:
    """用 e1RM 趋势判断是否进入平台期 (至少 4 次记录, 缺记录时不下结论)。"""
    trend = [float(v) for v in (e1rm_trend or []) if v]
    need = max(4, int(sessions))
    if len(trend) < need:
        return {'is_plateau': False, 'reason': f'可比记录不足 ({len(trend)}/{need}), 不做趋势结论', 'change_pct': 0.0}
    window = trend[-need:]
    first, last = window[0], window[-1]
    best = max(window)
    change_pct = ((last - first) / first * 100.0) if first else 0.0
    # 平台 = 窗口内净变化不明显 (<1%) 且最后一次没有突破之前的最高点
    is_plateau = change_pct < 1.0 and min_change_pct == 0.0 or change_pct <= min_change_pct
    is_plateau = is_plateau and (best - last) < 0.5
    return {
        'is_plateau': is_plateau,
        'change_pct': round(change_pct, 2),
        'sessions': need,
        'reason': (f'近 {need} 次 e1RM 变化 {change_pct:+.1f}% 且高点未被突破' if is_plateau
                   else f'近 {need} 次 e1RM 变化 {change_pct:+.1f}%, 仍在推进'),
        'hint': '平台期优先检查睡眠/能量/蛋白/RPE 估计/技术/周频率, 再考虑加量',
    }


# ═══════════════════════════════════════════════════════════
# 七、动作缺口审计 (Dan John Intervention, PDF 90-178)
# ═══════════════════════════════════════════════════════════

MOVEMENT_PATTERNS = (
    ('推', ('卧推', '推举', '俯卧撑', '肩推', '双杠', '臂屈伸', 'press', 'push')),
    ('拉', ('引体', '划船', '下拉', 'high pull', 'pull', 'row')),
    ('髋铰链', ('硬拉', '罗马尼亚', 'RDL', '壶铃摆', '早安', '铰链', 'deadlift', 'hinge')),
    ('深蹲', ('深蹲', '分腿蹲', '弓步', '蹲起', 'squat', 'lunge')),
    ('负重行走', ('农夫走', '负重行走', '提重', 'carry', 'farmer')),
    ('单腿/旋转', ('单腿', '保加利亚', '跨步', '鸟狗', '土耳其起立', '单臂', 'single-leg')),
)


def audit_movement_gaps(exercise_names: List[str]) -> Dict[str, Any]:
    """对当前动作清单做缺口审计, 只报缺口, 不自动加动作 (审计表而非配额表)。"""
    names = [str(n or '') for n in (exercise_names or [])]
    covered: Dict[str, List[str]] = {}
    for pattern, keywords in MOVEMENT_PATTERNS:
        hits = [n for n in names if any(k in n.lower() or k in n for k in keywords)]
        if hits:
            covered[pattern] = hits
    gaps = [p for p, _ in MOVEMENT_PATTERNS if p not in covered]
    return {
        'covered': covered,
        'gaps': gaps,
        'action': ('缺口明确且与目标相关时, 用最小、可教学、可恢复的方式补一个动作, '
                   '并保留原计划主线; 明显偏科不是自动加动作的理由') if gaps
                  else '六大动作模式均已有覆盖, 优先复核动作质量与恢复而不是继续加动作',
    }


# ═══════════════════════════════════════════════════════════
# 八、复盘决策 (综合自动调节 + 停滞 + 减载 + 疼痛, 单位: 次训练)
# ═══════════════════════════════════════════════════════════

@dataclass
class ReviewContext:
    """复盘输入上下文 (由 GUI / CLI 组装)。"""
    movement: str = '主项'
    weight: float = 0.0
    reps: int = 0
    sets: int = 0
    rpe: float = 8.0
    target_reps: int = 10
    target_rpe: float = 8.0
    level: str = 'L1'
    is_isolation: Optional[bool] = None
    rep_window: Tuple[int, int] = (8, 12)
    completed: bool = True
    pain_note: str = ''
    signals: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    e1rm_trend: List[float] = field(default_factory=list)
    weekly_sets: int = 0


@dataclass
class ReviewDecision:
    """复盘输出: 判断 + 下一次处方 + 渐进类型 + 备注。"""
    judgment: str
    progression_type: str
    next_prescription: Dict[str, Any]
    findings: List[str] = field(default_factory=list)
    deload: Optional[Dict[str, Any]] = None
    volume: Optional[Dict[str, Any]] = None
    stall: Optional[Dict[str, Any]] = None
    plateau: Optional[Dict[str, Any]] = None
    safety: Optional[str] = None


def review_session(ctx: ReviewContext) -> ReviewDecision:
    """综合复盘: 先安全分流 → 减载判定 → 停滞校验 → 自动调节 → 渐进方式。"""
    findings: List[str] = []

    safety = screen_action(ctx.pain_note)
    if safety:
        return ReviewDecision(
            judgment='暂停常规处方',
            progression_type='暂停',
            next_prescription={'movement': ctx.movement, 'action': '先评估再恢复训练'},
            findings=['疼痛/危险信号优先于任何渐进安排'],
            safety=safety,
        )

    if not ctx.completed:
        is_iso = _resolve_isolation(ctx)
        return ReviewDecision(
            judgment='部分完成',
            progression_type='维持',
            next_prescription={'movement': ctx.movement, 'weight': ctx.weight,
                               'reps': ctx.reps, 'sets': ctx.sets, 'rpe': ctx.rpe},
            findings=['未完成全部组次, 按原顺序继续, 不补课、不加倍训练',
                      '漏 2 次改用 30 分钟或状态差版接回'],
            volume=analyze_weekly_volume(ctx.level, ctx.weekly_sets) if ctx.weekly_sets else None,
        )

    deload = evaluate_deload_signals(ctx.signals)
    stall = detect_stall(ctx.history)
    plateau = detect_plateau(ctx.e1rm_trend) if ctx.e1rm_trend else None

    adjusted = autoregulated_set(
        ctx.weight, ctx.reps, ctx.rpe, ctx.target_reps, ctx.target_rpe, ctx.level,
    )

    if deload['verdict'] != '继续前进':
        findings.append(deload['action'])
        judgment = deload['verdict']
        progression = '减量'
        rx = {'movement': ctx.movement, 'weight': round(ctx.weight * 0.9 * 2) / 2,
              'sets': max(1, int(round(ctx.sets * (1 - VOLUME_DELOAD_RATIO)))), 'reps': ctx.reps,
              'rpe': max(5.0, ctx.rpe - 1.5)}
    elif stall['is_stall']:
        findings.append('连续同类异常, 优先怀疑结构而非当日状态')
        findings.extend(stall['details'])
        findings.append(stall['hint'])
        judgment = '停滞'
        progression = '结构调整'
        rx = {'movement': ctx.movement, 'weight': ctx.weight, 'sets': ctx.sets,
              'reps': ctx.reps, 'rpe': ctx.rpe}
        if ctx.weekly_sets:
            rx['suggested_weekly_sets'] = min(ctx.weekly_sets + VOLUME_STEP[0], WEEKLY_SET_CEILING)
    else:
        if plateau and plateau['is_plateau']:
            findings.append(plateau['reason'])
            findings.append(plateau['hint'])
        rx = apply_double_progression(
            adjusted['suggested_weight'], ctx.reps, ctx.sets, ctx.rpe,
            ctx.rep_window, _resolve_isolation(ctx),
        )
        rx = dict(rx)
        rx.setdefault('movement', ctx.movement)
        rx['weight'] = adjusted['suggested_weight']
        progression = rx.pop('progression_type', adjusted['action'])
        judgment = {'上调': '偏轻', '下调': '偏重'}.get(adjusted['action'], '合适')
        findings.append(adjusted['reason'])
        if 'note' in rx:
            findings.append(rx.pop('note'))

    rpe_path = build_rpe_path(int(ctx.sets or 3), max(6.0, ctx.rpe - 1.0), ctx.rpe)
    rx['rpe_path'] = rpe_path
    rx['rpe_text'] = [rpe_to_rir_text(r) for r in rpe_path]
    rx['rest'] = rest_seconds(ctx.movement)
    rx['failure'] = failure_allowance(ctx.movement, int(ctx.sets or 3), int(ctx.sets or 3))
    rx['tempo'] = tempo_prescription(not _resolve_isolation(ctx), ctx.signals.get('goal', '增肌'))

    return ReviewDecision(
        judgment=judgment,
        progression_type=progression,
        next_prescription=rx,
        findings=findings,
        deload=deload,
        volume=analyze_weekly_volume(ctx.level, ctx.weekly_sets) if ctx.weekly_sets else None,
        stall=stall,
        plateau=plateau,
    )


def _resolve_isolation(ctx: ReviewContext) -> bool:
    if ctx.is_isolation is not None:
        return bool(ctx.is_isolation)
    return classify_movement(ctx.movement) == 'isolation'


if __name__ == '__main__':  # 手动冒烟: python -m fitness_pkg.science
    demo = review_session(ReviewContext(
        movement='哑铃弯举', weight=12.5, reps=12, sets=3, rpe=8.0,
        target_reps=12, target_rpe=8.0, level='L1', weekly_sets=12,
        history=[{'index': 1, 'weight': 12.5, 'reps': 12, 'rpe': 8.0},
                 {'index': 2, 'weight': 12.5, 'reps': 11, 'rpe': 8.5}],
    ))
    print(demo.judgment, demo.progression_type)
    print(demo.next_prescription)
