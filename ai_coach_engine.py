# -*- coding: utf-8 -*-
"""
AI 教练核心引擎 v1.0 — 基于 Lzheng-fitness 知识库的本地增肌规划系统

提取 Lzheng-fitness 的 P0-L3 分层、力量周期化、训练复盘、停训接回与最低执行版本规则，
用纯 Python 实现，无需 AI 对话或网络依赖。

知识来源: Lzheng-fitness/knowledge/ (Schoenfeld/Helms/Aragon/Nuckols 蒸馏模块)
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

# 训练科学规则层 (v9.1): 可直接运行脚本 与 包内导入 两种场景都能找到
for _p in (os.path.dirname(os.path.abspath(__file__)),
           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fitness_pkg')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from science import (  # type: ignore
        ReviewContext, ReviewDecision, review_session, analyze_weekly_volume,
        evaluate_deload_signals, autoregulated_set, apply_double_progression,
        build_rpe_path, build_warmup_sets, failure_allowance, rest_seconds,
        planned_rest_plan, tempo_prescription, load_for_target_reps,
        reps_to_intensity, rpe_to_rir_text, e1rm_from_set, audit_movement_gaps,
        classify_movement, min_weight_step, weekly_set_band, detect_stall,
        detect_plateau, screen_action, VOLUME_STEP, WEEKLY_SET_CEILING,
    )
    SCIENCE_AVAILABLE = True
except Exception:
    try:
        from fitness_pkg.science import (  # type: ignore
            ReviewContext, ReviewDecision, review_session, analyze_weekly_volume,
            evaluate_deload_signals, autoregulated_set, apply_double_progression,
            build_rpe_path, build_warmup_sets, failure_allowance, rest_seconds,
            planned_rest_plan, tempo_prescription, load_for_target_reps,
            reps_to_intensity, rpe_to_rir_text, e1rm_from_set, audit_movement_gaps,
            classify_movement, min_weight_step, weekly_set_band, detect_stall,
            detect_plateau, screen_action, VOLUME_STEP, WEEKLY_SET_CEILING,
        )
        SCIENCE_AVAILABLE = True
    except Exception:
        SCIENCE_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COACH_DIR = os.path.join(BASE_DIR, '体重体脂监控', 'ai_coach')
os.makedirs(COACH_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 一、P0-L3 分层评估
# ═══════════════════════════════════════════════════════════

LEVEL_DESC = {
    'P0': '启动/回归期 — 首要目标: 安全、可重复、建立基准',
    'L1': '动作稳定期 — 可逐次或隔次推进，线性渐进',
    'L2': '周管理期 — 按周管理训练量、强度和恢复',
    'L3': '阶段进步期 — 按月或阶段出现进步，需高专项性和疲劳管理',
}


@dataclass
class AthleteProfile:
    """运动员建档"""
    name: str = ''
    age: int = 0
    height_cm: float = 0.0
    weight_kg: float = 0.0
    body_fat_pct: float = 0.0
    training_years: float = 0.0
    weekly_sessions: int = 4
    session_minutes: int = 60
    equipment: List[str] = field(default_factory=lambda: ['杠铃', '哑铃', '器械'])
    goal: str = '增肌'  # 增肌/减脂/力量/综合
    limitations: List[str] = field(default_factory=list)
    # 动作熟练度: {动作名: {'level': 'P0/L1/L2/L3', 'recent_1rm': float, 'quality': 1-5}}
    movement_proficiency: Dict[str, Dict] = field(default_factory=dict)


def assess_level(profile: AthleteProfile, movement: str) -> str:
    """评估单个动作的 P0-L3 等级

    依据: 近期可比记录、动作稳定性、恢复与推进速度
    """
    prof = profile.movement_proficiency.get(movement, {})
    quality = prof.get('quality', 0)
    has_record = bool(prof.get('recent_1rm'))
    years = profile.training_years

    if not has_record or quality < 2:
        return 'P0'
    if quality < 4 or years < 1:
        return 'L1'
    if years < 3 or quality < 5:
        return 'L2'
    return 'L3'


def assess_overall_level(profile: AthleteProfile) -> str:
    """评估整体训练等级"""
    if not profile.movement_proficiency:
        return 'P0' if profile.training_years < 0.5 else 'L1'
    levels = [assess_level(profile, m) for m in profile.movement_proficiency]
    order = ['P0', 'L1', 'L2', 'L3']
    idxs = [order.index(l) for l in levels]
    avg = sum(idxs) / len(idxs)
    return order[min(int(avg), 3)]


# ═══════════════════════════════════════════════════════════
# 二、力量周期生成 (8-12 周)
# ═══════════════════════════════════════════════════════════

PHASES = ['积累', '强度', '实现', '减量']


@dataclass
class WorkoutSet:
    """训练组"""
    weight: float
    reps: int
    sets: int
    rpe_start: float = 6.0
    rpe_end: float = 7.0
    set_type: str = '正式组'  # 热身组/顶组/回退组/正式组
    rpe_path: List[float] = field(default_factory=list)   # 逐组 RPE (首组→末组)
    rest_seconds: Optional[int] = None                    # 建议组间休息(秒)
    note: str = ''

    @property
    def rpe_text(self) -> str:
        """逐组 RPE 的可读描述, 保留首组→末组结构并标注 RIR。"""
        if self.rpe_path:
            return ' → '.join(rpe_to_rir_text(r) for r in self.rpe_path)
        return f'{self.rpe_start}→{self.rpe_end}'


@dataclass
class WorkoutDay:
    """训练日"""
    week: int
    phase: str
    day_name: str
    movement: str
    sets: List[WorkoutSet] = field(default_factory=list)
    notes: str = ''
    short_version_30: str = ''
    short_version_20: str = ''
    short_version_10: str = ''
    short_version_5: str = ''
    short_version_2: str = ''
    purpose: str = ''                                                # 本周目的
    checkpoint: str = ''                                             # 技术检查点
    warmup: List[str] = field(default_factory=list)                   # 热身步骤 (文字)
    rest_seconds: int = 150                                          # 组间休息下限
    warmup_sets: List[Dict[str, Any]] = field(default_factory=list)   # 热身流程
    rest_plan: List[Dict[str, Any]] = field(default_factory=list)     # 组间休息安排
    failure_note: str = ''                                           # 力竭使用说明
    tempo: Dict[str, Any] = field(default_factory=dict)               # 节奏/活动范围

    def short_version_seconds(self, seconds: int) -> str:
        """按秒返回短版处方, 支持 5 分钟以下的最低执行版本。"""
        base = self.short_version_10 or f'{self.movement} 1组 (仅顶组)'
        if seconds >= 1800:
            return self.short_version_30 or base
        if seconds >= 1200:
            return self.short_version_20 or base
        if seconds >= 600:
            return base
        if seconds >= 300:
            return self.short_version_5 or f'{self.movement} 1组 5次 (只保主线, 不补课)'
        if seconds >= 120:
            return self.short_version_2 or f'{self.movement} 1组 3次 (启动版, 只要连续性)'
        return '离训练结束还有 2 分钟时: 只做 1 组主线动作, 记录结果即可'


@dataclass
class StrengthCycle:
    """力量周期 (8-12 周)"""
    movement: str
    target_1rm: float
    current_1rm: float
    weeks: int
    start_date: str
    days: List[WorkoutDay] = field(default_factory=list)
    phase_distribution: Dict[str, int] = field(default_factory=dict)
    weekly_exposures: float = 2.0
    weekly_sets: int = 0
    volume_note: str = ''
    deload_weeks: List[int] = field(default_factory=list)


def determine_cycle_length(weekly_exposures: int, goal: str = '力量') -> int:
    """确定周期长度: 8/10/12 周

    - 8 周: 目标单一、动作频率较高、只需一次积累与转化
    - 10 周: 一般力量发展，兼顾积累、强度与验证
    - 12 周: 训练频率低、需要更慢推进，或需要完整阶段
    """
    if weekly_exposures >= 3:
        return 8
    elif weekly_exposures == 2:
        return 10 if goal == '力量' else 8
    else:
        return 12


def distribute_phases(weeks: int) -> Dict[str, int]:
    """分配各阶段周数: 积累→强度→实现→减量"""
    if weeks == 8:
        return {'积累': 3, '强度': 3, '实现': 1, '减量': 1}
    elif weeks == 10:
        return {'积累': 4, '强度': 3, '实现': 2, '减量': 1}
    else:  # 12
        return {'积累': 4, '强度': 4, '实现': 2, '减量': 2}


RIR_BY_RPE = {10.0: 0, 9.5: 0, 9.0: 1, 8.5: 1, 8.0: 2, 7.5: 2, 7.0: 3, 6.5: 3, 6.0: 4, 5.5: 4, 5.0: 5}


def rpe_to_rir(rpe: float) -> int:
    """RPE → RIR (还能做几次)

    规则: 10 ≈ 0 RIR、9 ≈ 1、8 ≈ 2、7 ≈ 3; 半档取更保守一侧(留更多余力)。
    """
    if rpe >= 10:
        return 0
    half = round(rpe * 2) / 2
    if half in RIR_BY_RPE:
        return RIR_BY_RPE[half]
    return RIR_BY_RPE[max(RIR_BY_RPE)] if half < 5 else RIR_BY_RPE[min(RIR_BY_RPE)]


# 每周训练组数起始区间(不是上限): 每个训练日 10-20 组, 超过 20 组/日需专门试验
WEEKLY_SETS_PER_SESSION_LOW = 10
WEEKLY_SETS_PER_SESSION_HIGH = 20


def weekly_set_range(sessions_per_week: int) -> Tuple[int, int]:
    """按每周训练日数推算周组数起始区间"""
    sessions = max(1, int(sessions_per_week))
    return (WEEKLY_SETS_PER_SESSION_LOW * sessions,
            WEEKLY_SETS_PER_SESSION_HIGH * sessions)


def check_weekly_sets(sessions_per_week: int, weekly_sets: int) -> Dict[str, Any]:
    """校验周组数是否落在起始区间内，超上限要求专门试验"""
    low, high = weekly_set_range(sessions_per_week)
    if weekly_sets < low:
        return {'status': '偏少', 'range': (low, high),
                'note': f'{weekly_sets} 组低于起始区间 {low}-{high}, 刺激可能不足; 优先提高动作质量再加组'}
    if weekly_sets <= high:
        return {'status': '区间内', 'range': (low, high),
                'note': f'{weekly_sets} 组落在起始区间 {low}-{high}, 按恢复与完成率推进'}
    return {'status': '超上限', 'range': (low, high),
            'note': f'{weekly_sets} 组超过 {high} 组上限, 需要专门试验并监控恢复; 不机械追求最大组数'}


# 休息与力竭: 复合主项与孤立动作不同口径
COMPOUND_REST_SECONDS = 150     # 复合主项 ≥2.5 分钟
ISOLATION_REST_SECONDS = 90     # 孤立动作 ≥1.5 分钟
COMPOUND_KEYWORDS = ('卧推', '深蹲', '硬拉', '推举', '划船', '引体', '实力举', '臀推', '高翻')


def is_compound(movement: str) -> bool:
    """按动作名粗判复合/孤立"""
    return any(k in movement for k in COMPOUND_KEYWORDS)


def rest_seconds(movement: str) -> int:
    return COMPOUND_REST_SECONDS if is_compound(movement) else ISOLATION_REST_SECONDS


def allows_failure(movement: str, last_set: bool = False) -> bool:
    """力竭规则: 复合主项不做力竭; 孤立动作只有最后一组可接近力竭"""
    if is_compound(movement):
        return False
    return last_set


def estimate_1rm(weight: float, reps: int, rpe: float = 7.0) -> float:
    """由一组记录估算 e1RM (RPE/RIR 口径, 与负荷换算互逆)

    规则: RPE 描述的是「还能再做几次」(RIR), 先换算到力竭的等效次数再套 Epley;
    把当前次数直接当力竭次数会系统性高估 (如 100kg×5@8 会算成 121.7kg)。
    仅作趋势观察, 不替代真实测试。
    """
    return e1rm_from_set(weight, reps, rpe)


def calc_target_weight(estimated_1rm: float, intensity_pct: float, reps: int) -> float:
    """根据目标强度百分比计算训练重量"""
    raw = estimated_1rm * intensity_pct
    return round(raw * 2) / 2  # 取 0.5kg 精度


# 各阶段强度/次数/组数/RPE 路径/回退组比例
# 依据: Helms 训练金字塔 Level 2-4 (次序 强度→组数→频率→休息, 组数不要同时动)
#       Helms Level 3 (减载周: 显著降低疲劳, 不测试极限)
#       Lzheng 03-渐进与力量周期 (阶段不是固定生理日历; 8 周适合目标单一且暴露频繁)
PHASE_INTENSITY = {
    '积累': {'pct': 0.70, 'reps': 8, 'sets': 4, 'rpe': (6.0, 7.5), 'backoff_pct': 0.90},
    '强度': {'pct': 0.80, 'reps': 5, 'sets': 4, 'rpe': (7.0, 8.5), 'backoff_pct': 0.90},
    '实现': {'pct': 0.88, 'reps': 3, 'sets': 3, 'rpe': (8.0, 9.0), 'backoff_pct': 0.92},
    '减量': {'pct': 0.60, 'reps': 5, 'sets': 2, 'rpe': (5.0, 6.0), 'backoff_pct': 0.90},
}


def _phase_rpe_path(phase: str, week_in_phase: int, phase_len: int) -> Tuple[float, float]:
    """逐组 RPE 路径: 同阶段内每周末组 RPE 递增 0.5, 表达组内疲劳累积方向"""
    base_start = PHASE_INTENSITY[phase]['rpe'][0]
    base_end = PHASE_INTENSITY[phase]['rpe'][1]
    step = 0.5 if phase_len > 1 else 0.0
    end = min(10.0, base_end + step * (week_in_phase - 1))
    return base_start, end


def _deload_week_numbers(weeks: int, dist: Dict[str, int], exposures: float) -> List[int]:
    """节律减载周(1-based)

    规则: 约每 4 周一次节律减载; 连续 3 个中周期(≥10 周)未见减载则预防性减载。
    实现阶段承担专项性, 不与节律减载叠加, 避免减载周反而重于相邻实现周。
    """
    deloads = [w for w in range(4, weeks + 1, 4) if w <= weeks - 1]
    if weeks >= 10 and not deloads:
        deloads = [weeks - 2]
    # 实现阶段的周不做节律减载
    realiz_weeks = []
    wk = 1
    for phase, n in dist.items():
        for _ in range(n):
            if phase == '实现':
                realiz_weeks.append(wk)
            wk += 1
    return [w for w in deloads if w not in realiz_weeks and w < weeks]


def generate_strength_cycle(
    movement: str,
    current_1rm: float,
    target_1rm: float,
    weekly_exposures: float = 2,
    start_date: Optional[str] = None,
    sessions_per_week: int = 4,
    level: str = 'L1',
    goal: str = '力量',
) -> StrengthCycle:
    """生成完整力量周期

    - 周期长度由每周暴露次数与目标共同决定 (determine_cycle_length), 不由「想提升力量」自动触发
    - 周组数按每周训练日数给出起始区间, 上限不是必须达到的目标
    - 减载: 约每 4 周一次节律减载; 连续 3 个中周期无减载则预防性减载
    """
    exposures = max(1.0, float(weekly_exposures))
    weeks = determine_cycle_length(int(round(exposures)), goal)
    dist = distribute_phases(weeks)
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')

    rest = rest_seconds(movement)
    compound = is_compound(movement)
    volume_low, volume_high = weekly_set_range(sessions_per_week)
    deload_weeks = _deload_week_numbers(weeks, dist, exposures)

    cycle = StrengthCycle(
        movement=movement,
        target_1rm=target_1rm,
        current_1rm=current_1rm,
        weeks=weeks,
        start_date=start_date,
        phase_distribution=dist,
        weekly_exposures=exposures,
        weekly_sets=cfg_sets_default(),
        volume_note=(f'周组数起始区间 {volume_low}-{volume_high} 组 '
                     f'(每周 {sessions_per_week} 练 × 10-20 组/日); '
                     '先用下限, 按恢复与完成率再加; 单次主项 5-8 组为常见起点'),
    )

    week = 1
    for phase, n_weeks in dist.items():
        cfg = PHASE_INTENSITY[phase]
        for i_in_phase in range(n_weeks):
            progress = (week - 1) / max(weeks - 1, 1)
            cur_1rm = current_1rm + (target_1rm - current_1rm) * progress * 0.7
            pct = cfg['pct'] + progress * 0.05
            deload = week in deload_weeks
            if deload:
                # 减载周: 用「减量」强度与组数口径, 保证轻于任何实现周
                pct = min(pct, PHASE_INTENSITY['减量']['pct'])
                cfg_sets = max(2, cfg['sets'] - 2)
                cfg_reps = PHASE_INTENSITY['减量']['reps']
                cycle.deload_weeks.append(week)
            else:
                cfg_sets = cfg['sets']
                cfg_reps = cfg['reps']

            if phase == '减量':
                # 减量阶段不以强度为先, 避免把减载写成「更重的验证周」
                pct = min(pct, 0.65)

            rpe_start, rpe_end = _phase_rpe_path(phase, i_in_phase + 1, n_weeks)
            if deload:
                rpe_start, rpe_end = max(4.0, rpe_start - 2.5), max(5.0, rpe_end - 2.5)

            w = calc_target_weight(cur_1rm, pct, cfg_reps)
            rpe_path = build_rpe_path(cfg_sets, rpe_start, rpe_end)
            topology = '逐组 RPE' if cfg_sets > 1 else '单组校准'
            top_set = WorkoutSet(
                weight=w, reps=cfg_reps, sets=1,
                rpe_start=rpe_path[0], rpe_end=rpe_path[-1],
                set_type='顶组', rpe_path=rpe_path,
                rest_seconds=rest_seconds(movement),
                note=f'{topology}: 顶组用于校准当天状态, 不作为惩罚性追加组',
            )
            backoff_w = round(w * cfg['backoff_pct'] * 2) / 2
            backoff_path = build_rpe_path(
                max(1, cfg_sets - 1), rpe_start, max(rpe_start, rpe_end - 0.5))
            backoff = WorkoutSet(
                weight=backoff_w, reps=cfg_reps + 2, sets=max(1, cfg_sets - 1),
                rpe_start=backoff_path[0], rpe_end=backoff_path[-1],
                set_type='回退组', rpe_path=backoff_path,
                rest_seconds=rest_seconds(movement),
                note='回退组是计划内的正式训练量, 顶上不去时用它替代, 不另外追加',
            )

            if compound:
                note = (f'{phase}阶段 — {PHASE_DESC[phase]}; 复合主项留 1-2 RIR, 不做力竭; '
                        f'组间休息 ≥{rest // 60} 分钟; 首组 RPE→末组 RPE 逐组记录')
            else:
                note = (f'{phase}阶段 — {PHASE_DESC[phase]}; 孤立动作优先双重渐进, '
                        f'仅最后一组可接近力竭; 组间休息 ≥{rest // 60} 分钟')

            day = WorkoutDay(
                week=week, phase=phase, day_name=f'第{week}周',
                movement=movement, sets=[top_set, backoff],
                notes=note,
                purpose=('建立可重复动作与训练量' if phase == '积累' else
                         '提高较高负荷暴露' if phase == '强度' else
                         '提高专项性, 不让额外疲劳掩盖表现' if phase == '实现' else
                         '显著降低疲劳并建立下一周期基准'),
                checkpoint=('动作全程可控, 顶组不超过 RPE 9' if phase != '减量' else
                            '训练意愿与恢复回到正常水平'),
                rest_seconds=rest,
                warmup=_warmup_steps(movement, w) + (
                    ['本周为节律减载周: 顶组重量与组数已下调'] if deload else []),
                warmup_sets=build_warmup_sets(cur_1rm),
                rest_plan=planned_rest_plan(movement, cfg_sets),
                failure_note=failure_allowance(movement, cfg_sets, cfg_sets)['note'],
                tempo=tempo_prescription(compound, goal),
            )
            day.short_version_30 = (f'热身 {movement} 空杆/50% 2×5 → {movement} {w}kg '
                                    f'{cfg_sets}×{cfg_reps} @RPE {rpe_start:.0f} (保留顶组+回退组)')
            day.short_version_20 = f'{movement} {w}kg 2×{cfg_reps} @RPE {rpe_start:.0f} (仅顶组+1组回退)'
            day.short_version_10 = f'{movement} {w}kg 1×{cfg_reps} @RPE {rpe_start:.0f} (仅顶组, 动作质量优先)'
            day.short_version_5 = f'{movement} {w * 0.9:.1f}kg 1×5 @RPE 6 (最小维持剂量, 只求不断档)'
            day.short_version_2 = f'{movement} 空杆/50% 1×8 热身激活 (2 分钟保持连续性, 不计入训练量)'
            cycle.days.append(day)
            week += 1

    return cycle


def _warmup_steps(movement: str, work_weight: float) -> List[str]:
    """热身流程: 从空杆/50% 起步, 逐步逼近工作重量"""
    light = round(work_weight * 0.5 * 2) / 2
    mid = round(work_weight * 0.75 * 2) / 2
    return [
        f'空杆/最轻档 {movement} 2×5 (激活)',
        f'{light}kg 1×5',
        f'{mid}kg 1×3',
        f'{work_weight}kg 1×1 (只做 1 次找感觉)',
    ]


def cfg_sets_default() -> int:
    """默认单次主项组数起点 (积累阶段)"""
    return PHASE_INTENSITY['积累']['sets']


PHASE_DESC = {
    '积累': '建立可恢复训练量和动作质量',
    '强度': '提高较高负荷暴露，通常减少次数或部分训练量',
    '实现': '提高专项性，避免额外疲劳掩盖表现',
    '减量': '显著降低疲劳，再测试目标或建立下一周期基准',
}


# ═══════════════════════════════════════════════════════════
# 三、训练复盘 + 渐进超负荷
# ═══════════════════════════════════════════════════════════

@dataclass
class TrainingLog:
    """训练记录"""
    date: str
    movement: str
    weight: float
    reps: int
    sets: int
    rpe: float
    completed: bool = True
    notes: str = ''
    pain: bool = False                # 是否出现疼痛
    abnormal_fatigue: bool = False    # 异常疲劳(睡眠/压力/恢复明显变差)
    form_broken: bool = False         # 动作标准明显失控
    pain_desc: str = ''               # 疼痛位置与表现


# 危险信号: 直接暂停普通训练处方, 先做专业评估
DANGER_SIGNALS = (
    '胸痛', '胸部不适', '胸闷', '晕厥', '昏厥', '麻木', '放射痛',
    '锐痛', '刺痛', '持续加重', '明显功能受限', '急性发热',
)


def screen_danger(text: str) -> bool:
    """疼痛描述中是否含危险信号"""
    return any(k in (text or '') for k in DANGER_SIGNALS)


def deload_signals(log: 'TrainingLog',
                   prev_log: Optional['TrainingLog'] = None,
                   signals: Optional[Dict[str, Any]] = None) -> List[str]:
    """减载信号: 命中 2 项即减载一周

    信号: 不想练(部分完成)、睡眠/恢复差(异常疲劳)、表现下降(掉次数或 RPE 升约一级)、
          压力大(异常疲劳)、疼痛。GUI/API 也可直接传入 signals 字典覆盖勾选结果。
    """
    if signals:
        try:
            hit = evaluate_deload_signals(signals).get('hit') or []
            if hit:
                return list(hit)
        except Exception:
            pass
    signals_hit = []
    if not log.completed:
        signals_hit.append('不想练/未完成计划组次')
    if log.abnormal_fatigue:
        signals_hit.append('睡眠或恢复明显变差(压力大)')
    if log.pain:
        signals_hit.append('出现疼痛')
    if log.form_broken:
        signals_hit.append('动作标准持续恶化')
    if prev_log and prev_log.movement == log.movement:
        if log.weight == prev_log.weight and log.reps < prev_log.reps:
            signals_hit.append('同重量掉次数(表现下降)')
        elif log.weight == prev_log.weight and log.rpe - prev_log.rpe >= 1.0:
            signals_hit.append('同组次 RPE 上升约一级')
    return signals_hit


@dataclass
class ReviewResult:
    """复盘结果"""
    judgment: str  # 完成/部分完成/偏轻/合适/偏重/需要观察
    key_findings: List[str]
    next_prescription: Dict[str, Any]
    progression_type: str  # 加重/加次/加组/维持/减量
    deload_recommended: bool = False
    deload_reasons: List[str] = field(default_factory=list)
    safety_hold: bool = False
    needs_more_data: bool = False
    rule_source: str = '训练科学规则层 (Helms/Schoenfeld/Nuckols/Dan John)'


def review_training(
    log: TrainingLog,
    prev_log: Optional[TrainingLog] = None,
    level: str = 'L1',
    target_reps: int = 10,
    target_rpe: float = 8.0,
    rep_window: Tuple[int, int] = (8, 12),
    pain_note: str = '',
    signals: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    e1rm_trend: Optional[List[float]] = None,
    weekly_sets: int = 0,
    is_isolation: Optional[bool] = None,
) -> ReviewResult:
    """单次训练复盘 + 下一次处方 (v9.1: 由训练科学规则层统一下判)

    规则来源 (由规则层统一下判, 不再手写 delta):
    - 安全分流: 疼痛描述命中危险信号 (胸痛/晕厥/麻木/放射痛等) → 暂停常规处方并建议专业评估
    - Schoenfeld: 多数组保留 1-2 RIR, 力竭只在末组; 一次只改一个主要变量
    - Helms: 反应式减载清单 (0-1 项前进 / 2+ 项减载); 孤立动作双重渐进
    - Nuckols: 无足够记录时不编造精确公斤数, 先用 RPE 6-7 选重建立第二个可比样本
    - Lzheng: 连续两次同类异常才怀疑结构; 单次异常只维持观察
    """
    hist = list(history or [])
    if prev_log is not None:
        hist.insert(0, {'weight': prev_log.weight, 'reps': prev_log.reps, 'rpe': prev_log.rpe})
    hist.append({'weight': log.weight, 'reps': log.reps, 'rpe': log.rpe})

    ctx = ReviewContext(
        movement=log.movement,
        weight=log.weight,
        reps=log.reps,
        sets=log.sets,
        rpe=log.rpe,
        target_reps=target_reps if target_reps > 0 else 10,
        target_rpe=target_rpe if target_rpe > 0 else 8.0,
        level=level,
        is_isolation=is_isolation,
        rep_window=rep_window,
        completed=log.completed,
        pain_note=pain_note or log.notes or '',
        signals=dict(signals or {}),
        history=hist[:-1],
        e1rm_trend=list(e1rm_trend or []),
        weekly_sets=weekly_sets,
    )
    decision = review_session(ctx)

    findings = list(decision.findings)
    if decision.stall and not decision.stall['is_stall'] and hist and len(hist) < 3:
        findings.append(f'可比记录只有 {len(hist)} 次, RPE 选重先行, 不编造精确公斤数')
    if decision.safety:
        findings.append(decision.safety)
    deload_reasons = list(decision.deload['hit']) if decision.deload else []

    rx = dict(decision.next_prescription)
    if 'weight' not in rx:
        rx['weight'] = log.weight
    rx['movement'] = rx.get('movement') or log.movement

    return ReviewResult(
        judgment=decision.judgment,
        key_findings=findings,
        next_prescription=rx,
        progression_type=decision.progression_type,
        deload_recommended=bool(decision.deload and decision.deload['verdict'] != '继续前进'),
        deload_reasons=deload_reasons,
        safety_hold=bool(decision.safety),
    )


# ═══════════════════════════════════════════════════════════
# 四、停训接回 (三档方案)
# ═══════════════════════════════════════════════════════════

@dataclass
class ReturnPlan:
    """停训接回方案"""
    days_off: int
    permission: str  # 正常接回/降级接回/最低任务/暂停
    normal_version: str
    degraded_version: str
    minimal_version: str
    next_7_days: List[str] = field(default_factory=list)
    return_48h: str = ''                                   # 48 小时内可完成的具体动作
    exit_conditions: Dict[str, str] = field(default_factory=dict)  # 升级/维持/暂停条件
    no_makeup_note: str = ''                               # 不补课声明
    first_week_focus: List[str] = field(default_factory=list)      # 第一周只验证这些
    success_criteria: str = '恢复自主判断和稳定执行, 而不是一周回到停训前全部重量'


# 停训天数 → (恢复权限, 正常版系数, 降级版系数, 最低版系数)
# 依据: Lzheng 04-训练中断接回 (正常/降级/最低/暂停 四档权限)
#       Helms Level 3 (减载不是「补作业」: 保留主线、降低相对压力、不测试极限)
RETURN_TIERS = (
    (7, '正常接回', 0.90, 0.85, 0.80),
    (21, '降级接回', 0.85, 0.75, 0.70),
    (56, '最低任务', 0.75, 0.65, 0.60),
)


def generate_return_plan(
    days_off: int,
    last_weight: float = 0.0,
    movement: str = '主项',
    support_movements: Optional[List[str]] = None,
    weekly_exposures: int = 2,
    missed_sessions: int = 0,
    condition_changed: bool = False,
) -> ReturnPlan:
    """生成停训接回三档方案 (覆盖多动作 + 48 小时接回 + 升级/维持/暂停条件)

    路由阈值: 停训 ≥7 天、连续漏练 3 次、条件或能力明显变化时进入接回流程。
    规则:
    - 0 天且未漏练: 按原计划继续
    - 漏 1 次不补课, 下一次按原顺序继续; 漏 2 次用 30 分钟短版接回
    - 1-7 天: 正常接回 (原负荷 90%)
    - 8-21 天: 降级接回 (原负荷 75%-85%)
    - 22-56 天: 最低任务 (原负荷 60%-75%)
    - >56 天: 暂停, 先用 RPE 选重重新建立可比样本 (不编造公斤数)
    - 第一周只验证出勤/动作感觉/疼痛反应/主观用力/次日恢复, 不补错过的训练量
    - 交付必须包含一个 48 小时内可完成的动作
    """
    movements = [movement or '主项'] + [m for m in (support_movements or []) if m and m != movement]
    exposures = max(1, min(int(weekly_exposures or 1), 7))

    def fmt(w: float) -> str:
        return f'{round(w * 2) / 2}kg' if w > 0 else '自重'

    first_week_focus = ['出勤是否稳定', '动作感觉与疼痛反应', '主观用力(RPE)是否可控', '次日恢复情况']

    if days_off <= 0 and missed_sessions <= 0:
        return ReturnPlan(
            days_off=days_off, permission='正常接回',
            normal_version='按原计划继续',
            degraded_version='—', minimal_version='—',
            next_7_days=['按当前周期继续训练'],
            return_48h='按原周期下一次安排直接训练, 不做额外补课',
            exit_conditions={
                'upgrade': '按周期处方正常推进即可',
                'hold': '出现单次异常时先维持, 结合睡眠与压力判断',
                'stop': '出现胸痛/晕厥/麻木/放射痛等危险信号 → 暂停并做专业评估',
            },
            first_week_focus=['正常执行即可'],
        )

    if days_off < 7 and missed_sessions in (1, 2):
        if missed_sessions == 1:
            return ReturnPlan(
                days_off=days_off, permission='正常接回',
                normal_version='按原顺序继续, 不补课',
                degraded_version='—', minimal_version='—',
                next_7_days=['漏 1 次不补课, 下一次按原顺序继续'],
                return_48h=f'{movement} 按原处方重量完成下次训练',
                exit_conditions={
                    'upgrade': '完成后按原周期继续推进',
                    'hold': 'RPE 明显高于往常时维持原重量一周',
                    'stop': '出现危险信号 → 暂停并做专业评估',
                },
                first_week_focus=first_week_focus,
            )
        return ReturnPlan(
            days_off=days_off, permission='降级接回',
            normal_version='按原顺序继续',
            degraded_version='使用 30 分钟短版接回',
            minimal_version='—',
            next_7_days=['漏 2 次用原计划的 30 分钟版本接回, 仍不补课'],
            return_48h=f'{movement} 主项 3 组 @RPE 7 (30 分钟短版), 只做当天主线',
            exit_conditions={
                'upgrade': '完成 30 分钟版且次日恢复正常 → 回原处方',
                'hold': 'RPE 超 8 或次日仍疲劳 → 再走一次 30 分钟版',
                'stop': '出现危险信号或疼痛加重 → 暂停并做专业评估',
            },
            first_week_focus=first_week_focus,
        )

    if days_off > 56:
        return ReturnPlan(
            days_off=days_off, permission='暂停',
            normal_version='建议重新建档, 先用 RPE 选重建立可比样本',
            degraded_version='从 P0 阶段重新开始动作学习与基准记录',
            minimal_version='先完成动作学习, 暂不做接近力竭的组',
            return_48h=f'{movements[0]} 空杆/最轻负荷 3×5 @RPE 5 (只找动作感觉)',
            exit_conditions={
                'upgrade': '动作无痛、技术稳定且次日恢复正常 → 下一周按最低版负荷推进',
                'hold': '疼痛或技术不稳 → 维持轻负荷技术练习',
                'stop': '出现危险信号 → 暂停并寻求专业评估',
            },
            next_7_days=['重新建档', '动作重量校准 (RPE 6-7 选重)', '生成新计划'],
            first_week_focus=first_week_focus,
        )

    perm, normal_r, degraded_r, minimal_r = '正常接回', 0.90, 0.85, 0.80
    for threshold, name, nr, dr, mr in RETURN_TIERS:
        if days_off <= threshold:
            perm, normal_r, degraded_r, minimal_r = name, nr, dr, mr
            break

    lines = {}
    for label, ratio, rpe in (('normal', normal_r, 7.0), ('degraded', degraded_r, 6.5),
                              ('minimal', minimal_r, 6.0)):
        lines[label] = ' / '.join(
            f'{m} {fmt(last_weight * ratio)} 3×8 @{rpe_to_rir_text(rpe)}'
            if m == movements[0] and last_weight > 0
            else f'{m} 保留主线 2×10 @{rpe_to_rir_text(rpe)}'
            for m in movements
        )

    day_plan = []
    for i in range(exposures):
        day_no = 1 + i * max(1, 7 // exposures)
        if i == 0:
            day_plan.append(f'第{day_no}天: 降级版 — {lines["degraded"]} (找回感觉, 不追求负荷)')
        elif i == 1:
            day_plan.append(f'第{day_no}天: 正常版 — {lines["normal"]} (恢复正常节奏)')
        else:
            day_plan.append(f'第{day_no}天: 正常版 — {lines["normal"]} (进入原周期, 保留 1–2 RIR)')

    if missed_sessions == 2:
        day_plan.insert(0, '漏 2 次: 这一次走 30 分钟短版, 不补课、不加倍')
    if condition_changed:
        day_plan.insert(0, '训练条件或能力已变化: 先按最低版完成 1 次, 再决定是否升级')

    return ReturnPlan(
        days_off=days_off,
        permission=perm,
        normal_version=lines['normal'],
        degraded_version=lines['degraded'],
        minimal_version=lines['minimal'],
        return_48h=(f'{movements[0]} {fmt(last_weight * degraded_r)} 3×8 @{rpe_to_rir_text(6.5)}'
                    ' (48 小时内先完成这一次)'),
        exit_conditions={
            'upgrade': '动作质量稳定、RPE ≤ 目标且次日恢复正常 → 下一周回到正常版负荷',
            'hold': 'RPE 超标或次日明显疲劳 → 维持降级版一周',
            'stop': '疼痛/异常气短/麻木等信号 → 暂停常规处方并寻求专业评估',
        },
        next_7_days=day_plan + ['第7天: 评估出勤/动作感觉/疼痛反应/主观用力/次日恢复, 再决定是否回到原周期'],
        no_makeup_note='第一周不补错过的训练量, 不测试极限, 不随机更换全部动作',
        first_week_focus=first_week_focus,
    )


def generate_short_version(workout: WorkoutDay, minutes: int) -> str:
    """生成最低执行版本 (v9.1: 支持 2/5/10/20/30 分钟档)

    规则:
    - 短版优先保留当天主线, 不补课、不加倍训练、不用惩罚性有氧
    - 时间不足时按 Helms Level 5 先减少低优先级附件, 不压缩复合主项的组间休息
    - 孤立/低风险附件可用拮抗肌配对组省时, 复合主项不要在组间插入其他训练
    """
    seconds = max(0, int(minutes)) * 60
    return workout.short_version_seconds(seconds)


def generate_short_plan(workout: WorkoutDay, minutes: int) -> Dict[str, Any]:
    """短版的完整可序列化明细 (含保留/舍弃规则与休息建议)。"""
    kind = classify_movement(workout.movement)
    lo, hi = rest_seconds(workout.movement)
    return {
        'minutes': int(minutes),
        'prescription': generate_short_version(workout, minutes),
        'keep': '当天主线动作与顶组',
        'drop': '低优先级附件与泵感类补充 (先减附件, 不压缩复合主项的组间休息)',
        'rest': f'{lo//60}–{hi//60} 分钟' if hi >= 120 else f'{lo} 秒',
        'super_set': '可与拮抗肌动作配对省时' if kind == 'isolation' else '不要在组间插入其他训练',
        'rules': [
            '漏 1 次按原顺序继续, 不补课',
            '漏 2 次用 30 分钟或状态差版接回',
            '达到 7 天或连续漏 3 次 → 走停训接回流程',
            '不用惩罚性有氧弥补',
        ],
    }


def _export_cycle_week_rows(d) -> List[str]:
    """导出周期 Markdown 的每周训练表行 (供 export_cycle_to_markdown 复用)。"""
    lines = []
    if d.purpose:
        lines.append(f'目的: {d.purpose}')
    lines.append('| 组类型 | 重量 | 组×次 | RPE 路径 | 组间休息 |')
    lines.append('|:------|:-----|:------|:---------|:---------|')
    for st in d.sets:
        rest_txt = f'{st.rest_seconds // 60} 分钟' if st.rest_seconds else '按需'
        lines.append(f'| {st.set_type} | {st.weight}kg | {st.sets}×{st.reps} | {st.rpe_text} | {rest_txt} |')
    if d.warmup_sets:
        lines.append('')
        lines.append('热身: ' + ' / '.join(
            f'{(w["label"] if w["weight"] <= 0 else str(w["weight"]) + "kg")} {w["reps"]}次'
            for w in d.warmup_sets))
    if d.checkpoint:
        lines.append(f'技术检查点: {d.checkpoint}')
    if d.failure_note:
        lines.append(f'力竭使用: {d.failure_note}')
    if d.tempo:
        lines.append(f'节奏/幅度: 离心 {d.tempo.get("eccentric", "")}, 向心 {d.tempo.get("concentric", "")}, '
                     f'{d.tempo.get("note", "")}')
    return lines


# ═══════════════════════════════════════════════════════════
# 六、数据持久化
# ═══════════════════════════════════════════════════════════

def _atomic_write_json(path: str, data: Any) -> str:
    """原子写 JSON: 先写临时文件再替换, 避免中途异常留下半个文件"""
    tmp = f'{path}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def _read_json(path: str, default: Any) -> Any:
    """读取 JSON: 兼容多种编码; 文件损坏时备份为 .bad 并返回默认值, 不静默丢数据"""
    if not os.path.exists(path):
        return default
    for enc in ('utf-8', 'utf-8-sig', 'gbk', 'gb18030'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return json.load(f)
        except json.JSONDecodeError:
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
        except OSError:
            break
    backup = f'{path}.bad'
    try:
        if not os.path.exists(backup):
            os.replace(path, backup)
    except OSError:
        pass
    return default


def save_profile(profile: AthleteProfile) -> str:
    path = os.path.join(COACH_DIR, 'profile.json')
    return _atomic_write_json(path, asdict(profile))


def load_profile() -> Optional[AthleteProfile]:
    """加载建档; 缺字段/多余字段均不致崩溃"""
    path = os.path.join(COACH_DIR, 'profile.json')
    data = _read_json(path, None)
    if not isinstance(data, dict):
        return None
    known = set(AthleteProfile.__dataclass_fields__)
    return AthleteProfile(**{k: v for k, v in data.items() if k in known})


def save_cycle(cycle: StrengthCycle) -> str:
    path = os.path.join(COACH_DIR, f'cycle_{cycle.movement}_{cycle.start_date}.json')
    data = {
        'movement': cycle.movement, 'target_1rm': cycle.target_1rm,
        'current_1rm': cycle.current_1rm, 'weeks': cycle.weeks,
        'start_date': cycle.start_date, 'phase_distribution': cycle.phase_distribution,
        'days': [
            {
                'week': d.week, 'phase': d.phase, 'day_name': d.day_name,
                'movement': d.movement, 'notes': d.notes,
                'sets': [asdict(s) for s in d.sets],
                'short_30': d.short_version_30, 'short_20': d.short_version_20,
                'short_10': d.short_version_10, 'short_5': d.short_version_5,
                'short_2': d.short_version_2,
                'warmup': d.warmup, 'rest_seconds': d.rest_seconds,
                'purpose': d.purpose, 'checkpoint': d.checkpoint,
            } for d in cycle.days
        ],
        'weekly_exposures': cycle.weekly_exposures,
        'weekly_sets': cycle.weekly_sets,
        'volume_note': cycle.volume_note,
        'deload_weeks': cycle.deload_weeks,
    }
    return _atomic_write_json(path, data)


def save_review(log: TrainingLog, result: ReviewResult) -> str:
    path = os.path.join(COACH_DIR, 'reviews.json')
    reviews = _read_json(path, [])
    if not isinstance(reviews, list):
        reviews = []
    reviews.append({
        'log': asdict(log),
        'judgment': result.judgment,
        'key_findings': result.key_findings,
        'next_prescription': result.next_prescription,
        'progression_type': result.progression_type,
        'deload_recommended': result.deload_recommended,
        'deload_reasons': result.deload_reasons,
        'safety_hold': result.safety_hold,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
    })
    return _atomic_write_json(path, reviews)


def load_reviews() -> List[Dict]:
    path = os.path.join(COACH_DIR, 'reviews.json')
    data = _read_json(path, [])
    return data if isinstance(data, list) else []


# ═══════════════════════════════════════════════════════════
# 七、周期导出为 Markdown (供 fitness-tracker 训练计划页读取)
# ═══════════════════════════════════════════════════════════

def export_cycle_to_markdown(cycle: StrengthCycle) -> str:
    """导出周期为 Markdown 格式"""
    lines = [
        f'# {cycle.movement} 力量周期 — {cycle.weeks}周',
        f'> 起始日期: {cycle.start_date}',
        f'> 当前 1RM: {cycle.current_1rm}kg → 目标 1RM: {cycle.target_1rm}kg',
        f'> 阶段分布: {", ".join(f"{k}{v}周" for k, v in cycle.phase_distribution.items())}',
        f'> 每周暴露: {cycle.weekly_exposures:.1f} 次',
        f'> 周组数: {cycle.volume_note}',
    ]
    if cycle.deload_weeks:
        lines.append(f'> 节律减载周: 第 {", ".join(str(w) for w in cycle.deload_weeks)} 周')
    lines += [
        '> 力竭规则: 复合主项不做力竭(留 1-2 RIR), 孤立动作仅最后一组可接近',
        '> 单次状态差不改结构: 连续两次可比记录异常才怀疑周期',
        '',
        '## 周期结构',
        '',
    ]
    for phase, n in cycle.phase_distribution.items():
        lines.append(f'- **{phase}** ({n}周): {PHASE_DESC.get(phase, "")}')
    lines.extend(['', '## 每周训练安排', ''])
    for d in cycle.days:
        lines.append(f'### 第{d.week}周 — {d.phase}阶段')
        lines.append(f'{d.notes}')
        lines.append('')
        if d.purpose:
            lines.append(f'目的: {d.purpose}')
        lines.append('| 组类型 | 重量 | 组×次 | RPE 路径 | 组间休息 |')
        lines.append('|:------|:-----|:------|:---------|:---------|')
        for st in d.sets:
            rest_txt = f'{st.rest_seconds // 60} 分钟' if st.rest_seconds else '按需'
            lines.append(f'| {st.set_type} | {st.weight}kg | {st.sets}×{st.reps} | {st.rpe_text} | {rest_txt} |')
        if d.warmup_sets:
            lines.append('')
            lines.append('热身: ' + ' / '.join(
                f'{(w["label"] if w["weight"] <= 0 else str(w["weight"]) + "kg")} {w["reps"]}次'
                for w in d.warmup_sets))
        if d.checkpoint:
            lines.append(f'技术检查点: {d.checkpoint}')
        if d.failure_note:
            lines.append(f'力竭使用: {d.failure_note}')
        if d.tempo:
            lines.append(f'节奏/幅度: 离心 {d.tempo.get("eccentric", "")}, 向心 {d.tempo.get("concentric", "")}, '
                         f'{d.tempo.get("note", "")}')
        lines.extend([
            '',
            '短版 (不补课):',
            f'- 30分钟: {d.short_version_30}',
            f'- 20分钟: {d.short_version_20}',
            f'- 10分钟: {d.short_version_10}',
            f'- 5分钟: {d.short_version_seconds(300)}',
            f'- 2分钟: {d.short_version_seconds(120)}',
            '',
        ])
    lines.extend([
        '## 科学依据',
        '',
        '- Helms《训练金字塔 v2.0》: 每肌群/动作模式每周 10–20 组起始区间; 组间休息小肌群 ≥1.5 min、复合主项 ≥2.5 min; 反应式减载清单 0–1 项前进 / 2+ 项减载',
        '- Schoenfeld: 多数组保留 1–2 RIR, 力竭只在末组; 一次只改一个主要变量并观察 2–4 周',
        '- Nuckols: 训练量是可检验剂量而非固定靶值; AMRAP/e1RM 趋势评估优于频繁硬测 1RM',
        '- Lzheng: 连续两次同类异常才怀疑结构; 阶段不是固定生理日历',
        '',
        '## 验证方式',
        '',
        '- 成功不等于最终 1RM: 检查目标负荷下的动作质量、RPE、完成率、恢复与有效暴露',
        '- 无可靠记录时先用 RPE 6–7 选重建立第二个可比样本, 不编造精确公斤数',
        '- 出现疼痛或危险信号 (胸痛/晕厥/麻木/放射痛等) 时暂停常规高强度处方并寻求专业评估',
        '',
    ])
    path = os.path.join(COACH_DIR, f'周期_{cycle.movement}_{cycle.start_date}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path

# ═══════════════════════════════════════════════════════════
# 八、编排与自检 (v9.1)
# ═══════════════════════════════════════════════════════════

def build_weekly_volume_report(level: str, muscle_sets: Dict[str, int]) -> Dict[str, Any]:
    """按训练等级检查每个肌群的周组数是否落在起始区间 (Helms 10–20 组)。"""
    items = []
    for muscle, sets in (muscle_sets or {}).items():
        items.append({'muscle': muscle, **analyze_weekly_volume(level, sets)})
    return {'level': (level or 'P0').upper(), 'items': items}


def coach_diagnostics() -> Dict[str, Any]:
    """引擎自检: 科学规则层是否可用 + 关键规则的当前取值 (供 GUI / CI 展示)。"""
    if SCIENCE_AVAILABLE:
        return {
            'science_layer': True,
            'rpe_scheme': 'RPE 10 = 0 RIR, 9 ≈ 1 RIR, 8 ≈ 2 RIR, 7 ≈ 3 RIR',
            'weekly_set_bands': {k: weekly_set_band(k) for k in ('P0', 'L1', 'L2', 'L3')},
            'weekly_set_ceiling': WEEKLY_SET_CEILING,
            'volume_step': VOLUME_STEP,
            'deload_threshold': f'2 项及以上反应式减载信号 → 减载一周; 连续 3 个中周期未减载 → 预防性减载',
            'rest_seconds': {'compound': rest_seconds('深蹲'), 'isolation': rest_seconds('弯举')},
            'failure_policy': '复合主项常规不做力竭; 孤立动作仅末组可接近力竭',
        }
    return {
        'science_layer': False,
        'hint': 'fitness_pkg/science.py 未加载, 已降级为 v9.0 的旧规则',
    }
