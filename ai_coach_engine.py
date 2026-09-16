# -*- coding: utf-8 -*-
"""
AI 教练核心引擎 v1.0 — 基于 Lzheng-fitness 知识库的本地增肌规划系统

提取 Lzheng-fitness 的 P0-L3 分层、力量周期化、训练复盘、停训接回与最低执行版本规则，
用纯 Python 实现，无需 AI 对话或网络依赖。

知识来源: Lzheng-fitness/knowledge/ (Schoenfeld/Helms/Aragon/Nuckols 蒸馏模块)
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

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
    warmup: List[str] = field(default_factory=list)
    rest_seconds: int = 150
    purpose: str = ''
    checkpoint: str = ''


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
    """Epley 公式 + RPE 调整估算 1RM

    规则: RPE 描述的是「还能再做几次」(RIR), 因此先换算出力竭时可完成的次数
    再代入 Epley。原实现把当前次数直接当作力竭次数, 会系统性高估 1RM
    (如 100kg x 5 @8 原算法给 121.7kg, 实际应为 115.5kg)。
    """
    if reps <= 1 and rpe >= 10.0:
        return weight
    rir = max(0.0, 10.0 - rpe)          # RPE 10 ≈ 0 RIR, 每降 1 档留 1 次余力
    reps_to_failure = reps + rir
    if reps_to_failure <= 1:
        return round(weight, 1)
    return weight * (1 + reps_to_failure / 30.0)


def calc_target_weight(estimated_1rm: float, intensity_pct: float, reps: int) -> float:
    """根据目标强度百分比计算训练重量"""
    raw = estimated_1rm * intensity_pct
    return round(raw * 2) / 2  # 取 0.5kg 精度


PHASE_INTENSITY = {
    '积累': {'pct': 0.70, 'reps': 8, 'sets': 4, 'rpe': (6, 7)},
    '强度': {'pct': 0.80, 'reps': 5, 'sets': 4, 'rpe': (7, 8)},
    '实现': {'pct': 0.88, 'reps': 3, 'sets': 3, 'rpe': (8, 9)},
    '减量': {'pct': 0.60, 'reps': 5, 'sets': 3, 'rpe': (5, 6)},
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
) -> StrengthCycle:
    """生成完整力量周期

    - 周期长度由实际每周暴露次数决定, 不由「想提升力量」自动触发
    - 周组数按每周训练日数给出起始区间, 区间上限不是必须达到的目标
    - 减载: 约每 4 周一次节律减载; 连续 3 个中周期无减载则预防性减载
    """
    exposures = max(1.0, float(weekly_exposures))
    weeks = determine_cycle_length(int(round(exposures)))
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
                # 减载周: 用「减量阶段」强度口径, 显著降低负荷与组数
                pct = PHASE_INTENSITY['减量']['pct']
                cfg_sets = max(2, PHASE_INTENSITY['减量']['sets'] - 1)
                cfg_reps = cfg['reps']
                cycle.deload_weeks.append(week)
            else:
                cfg_sets = cfg['sets']
                cfg_reps = cfg['reps']

            rpe_start, rpe_end = _phase_rpe_path(phase, i_in_phase + 1, n_weeks)
            if deload:
                rpe_start, rpe_end = 4.0, 5.0

            w = calc_target_weight(cur_1rm, pct, cfg_reps)

            topology = '逐组 RPE' if cfg_sets > 1 else '单组校准'
            top_set = WorkoutSet(
                weight=w, reps=cfg_reps, sets=1,
                rpe_start=rpe_start, rpe_end=min(rpe_end, rpe_start + 1.0),
                set_type='顶组'
            )
            backoff_w = round(w * 0.90 * 2) / 2
            backoff = WorkoutSet(
                weight=backoff_w, reps=cfg_reps + 2, sets=max(1, cfg_sets - 1),
                rpe_start=rpe_start, rpe_end=rpe_end,
                set_type='回退组'
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
                rest_seconds=rest,
                purpose=('建立可重复动作与训练量' if phase == '积累' else
                         '提高较高负荷暴露' if phase == '强度' else
                         '提高专项性, 不让额外疲劳掩盖表现' if phase == '实现' else
                         '显著降低疲劳并建立下一周期基准'),
                checkpoint=('动作全程可控, 顶组不超过 RPE 9' if phase != '减量' else
                            '训练意愿与恢复回到正常水平'),
                warmup=_warmup_steps(movement, w) + (
                    ['本周为节律减载周: 顶组重量与组数已下调'] if deload else []),
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
                   prev_log: Optional['TrainingLog'] = None) -> List[str]:
    """减载信号: 命中 2 项即减载一周

    信号: 不想练(部分完成)、睡眠/恢复差(异常疲劳)、表现下降(掉次数或 RPE 升约一级)、
          压力大(异常疲劳)、疼痛。
    """
    signals = []
    if not log.completed:
        signals.append('不想练/未完成计划组次')
    if log.abnormal_fatigue:
        signals.append('睡眠或恢复明显变差(压力大)')
    if log.pain:
        signals.append('出现疼痛')
    if log.form_broken:
        signals.append('动作标准持续恶化')
    if prev_log and prev_log.movement == log.movement:
        if log.weight == prev_log.weight and log.reps < prev_log.reps:
            signals.append('同重量掉次数(表现下降)')
        elif log.weight == prev_log.weight and log.rpe - prev_log.rpe >= 1.0:
            signals.append('同组次 RPE 上升约一级')
    return signals


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


def review_training(log: TrainingLog, prev_log: Optional[TrainingLog] = None) -> ReviewResult:
    """单次训练复盘 + 渐进超负荷决策

    规则:
    - 一次只优先改变重量、次数或组数中的一个主要变量
    - 双重渐进: 先把次数提高到范围上限，再增加一个最小重量单位
    - 复合主项不做力竭, 主要正式组通常不超过 RPE 9
    - 单次状态差不改结构: 同重量掉次数或同组次 RPE 升约一级, 需**连续两次**才怀疑周期结构
    - 命中 2 项减载信号 → 减载一周
    - 危险信号(胸痛/晕厥/麻木/放射痛等) → 暂停普通处方
    """
    findings: List[str] = []
    next_rx: Dict[str, Any] = {'movement': log.movement, 'rest_seconds': rest_seconds(log.movement)}

    # ── 安全优先: 危险信号直接暂停常规处方 ──
    if log.pain and screen_danger(log.pain_desc or log.notes):
        return ReviewResult(
            judgment='暂停训练',
            key_findings=[
                f'疼痛描述含危险信号: {log.pain_desc or log.notes}',
                '暂停常规高强度处方, 先获得合适的专业评估',
                '本工具不作诊断, 不替代医生或康复专业人员',
            ],
            next_prescription={'movement': log.movement, 'action': '暂停', 'note': '以专业评估结论为下一步依据'},
            progression_type='暂停',
            safety_hold=True,
            deload_recommended=True,
            deload_reasons=['危险信号'],
        )

    signals = deload_signals(log, prev_log)
    deload = len(signals) >= 2

    if not log.completed:
        findings.append('未完成全部计划组次 → 不补课, 下次按原安排继续')
        if deload:
            findings.append('减载信号 ≥2 项, 建议本周直接减载: 重量与组数同步下调')
        return ReviewResult(
            judgment='部分完成',
            key_findings=findings,
            next_prescription=(dict(next_rx, weight=round(log.weight * 0.85 * 2) / 2,
                                    reps=log.reps, sets=max(1, log.sets - 1), rpe=6.0)
                               if deload else
                               dict(next_rx, weight=log.weight, reps=log.reps,
                                    sets=log.sets, rpe=log.rpe)),
            progression_type='减量' if deload else '维持',
            deload_recommended=deload,
            deload_reasons=signals,
        )

    compound = is_compound(log.movement)
    rir = rpe_to_rir(log.rpe)

    if log.pain or log.form_broken:
        judgment = '需要观察'
        if log.pain:
            findings.append(f'训练中出现疼痛({log.pain_desc or "位置未填"}) → 本次不加重, 先排查动作与器械设置')
        if log.form_broken:
            findings.append('动作标准失控 → 降一个最小重量档, 把动作质量放在负重数字之前')
        next_rx.update({'weight': round(log.weight * 0.9 * 2) / 2, 'reps': log.reps,
                        'sets': log.sets, 'rpe': min(8.0, log.rpe)})
        prog = '维持'
    elif log.rpe >= 9.5:
        judgment = '偏重'
        findings.append(f'RPE {log.rpe} 过高 (RIR ≈ {rir})，超过 9.5')
        findings.append('下次维持重量并降半档 RPE, 关注动作质量而不是负重数字')
        next_rx.update({'weight': log.weight, 'reps': log.reps, 'sets': log.sets, 'rpe': log.rpe - 0.5})
        prog = '维持'
    elif log.rpe <= 6.0:
        judgment = '偏轻'
        findings.append(f'RPE {log.rpe} 偏低 (RIR ≈ {rir})，还有较多余力')
        if log.reps < 12:
            findings.append('双重渐进: 先加次数到范围上限')
            next_rx.update({'weight': log.weight, 'reps': log.reps + 1, 'sets': log.sets, 'rpe': log.rpe + 0.5})
            prog = '加次'
        else:
            findings.append('次数已达上限，加重 2.5kg')
            next_rx.update({'weight': log.weight + 2.5, 'reps': log.reps - 2, 'sets': log.sets, 'rpe': 7.0})
            prog = '加重'
    else:
        judgment = '合适'
        findings.append(f'RPE {log.rpe} 在合理区间 (7-9), 剩余次数 ≈ {rir}')

        # ── 停滞判定: 连续两次可比记录异常才怀疑结构 ──
        stall_count = 0
        if prev_log and prev_log.movement == log.movement:
            if log.weight == prev_log.weight and (
                    log.reps < prev_log.reps or log.rpe - prev_log.rpe >= 1.0):
                stall_count += 1
        if stall_count >= 1:
            findings.append('本次同重量表现下降(掉次数或 RPE 升约一级) → 单次异常先看睡眠/压力/休息, 不改结构')
            next_rx.update({'weight': log.weight, 'reps': log.reps, 'sets': log.sets, 'rpe': log.rpe})
            prog = '维持'
        elif prev_log and prev_log.weight == log.weight and prev_log.reps == log.reps:
            if log.rpe <= prev_log.rpe - 0.5:
                findings.append('同重量同次数 RPE 下降，可加重 2.5kg')
                next_rx.update({'weight': log.weight + 2.5, 'reps': log.reps, 'sets': log.sets, 'rpe': 7.5})
                prog = '加重'
            else:
                findings.append('维持当前处方，巩固适应')
                next_rx.update({'weight': log.weight, 'reps': log.reps, 'sets': log.sets, 'rpe': log.rpe})
                prog = '维持'
        else:
            if log.reps < 10:
                findings.append('双重渐进: 加 1 次')
                next_rx.update({'weight': log.weight, 'reps': log.reps + 1, 'sets': log.sets, 'rpe': log.rpe + 0.5})
                prog = '加次'
            else:
                findings.append('次数达上限，加重 2.5kg')
                next_rx.update({'weight': log.weight + 2.5, 'reps': log.reps - 2, 'sets': log.sets, 'rpe': 7.5})
                prog = '加重'

    if deload:
        findings.append(f'命中 {len(signals)} 项减载信号: {"、".join(signals)} → 建议减载一周')
        next_rx.update({'weight': round(log.weight * 0.85 * 2) / 2, 'reps': log.reps,
                        'sets': max(1, log.sets - 1), 'rpe': 6.0})
        prog = '减量'

    if compound:
        findings.append('复合主项不做力竭, 组间休息 ≥2.5 分钟')
    else:
        findings.append('孤立动作仅最后一组可接近力竭, 组间休息 ≥1.5 分钟')

    findings.append('调整方案需你确认后再改周期参数(周次/频率/动作/组数/次数/重量/RPE 路径)')

    return ReviewResult(
        judgment=judgment, key_findings=findings, next_prescription=next_rx,
        progression_type=prog, deload_recommended=deload, deload_reasons=signals,
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
    next_7_days: List[str]
    first_step_48h: str = ''            # 48 小时内可完成的第一个具体动作
    upgrade_condition: str = ''         # 升级条件
    hold_condition: str = ''            # 维持条件
    pause_condition: str = ''           # 继续降级或暂停条件
    success_criteria: str = '恢复自主判断和稳定执行, 而不是一周回到停训前全部重量'
    first_week_focus: List[str] = field(default_factory=list)


def generate_return_plan(days_off: int, last_weight: float = 0.0,
                          movement: str = '主项', missed_sessions: int = 0,
                          condition_changed: bool = False) -> ReturnPlan:
    """生成停训接回三档方案

    路由阈值: 停训 ≥7 天、连续漏练 3 次、条件或能力明显变化时进入接回流程。
    规则:
    - 0-6 天: 按原计划继续 (漏 1 次不补课, 漏 2 次用 30 分钟短版接回)
    - 7-21 天: 正常接回 (原重量 90%)
    - 22-56 天: 降级接回 (原重量 80%)
    - 57-84 天: 最低任务 (原重量 70%)
    - >84 天: 暂停, 重新建档
    第一周只验证出勤、动作感觉、疼痛反应、主观用力和次日恢复, 不补错过的训练量。
    """
    first_week_focus = ['出勤是否稳定', '动作感觉与疼痛反应', '主观用力(RPE)是否可控', '次日恢复情况']

    if days_off <= 0 and missed_sessions <= 0:
        return ReturnPlan(
            days_off=days_off, permission='正常接回',
            normal_version='按原计划继续',
            degraded_version='—', minimal_version='—',
            next_7_days=['按当前周期继续训练'],
            first_step_48h='按原周期下一次安排直接训练, 不做额外补课',
            upgrade_condition='按周期处方正常推进即可',
            hold_condition='出现单次异常时先维持, 结合睡眠与压力判断',
            pause_condition='出现胸痛/晕厥/麻木/放射痛等危险信号 → 暂停并做专业评估',
            first_week_focus=['正常执行即可'],
        )

    if missed_sessions in (1, 2) and days_off < 7:
        if missed_sessions == 1:
            return ReturnPlan(
                days_off=days_off, permission='正常接回',
                normal_version='按原顺序继续, 不补课',
                degraded_version='—', minimal_version='—',
                next_7_days=['漏 1 次不补课, 下一次按原顺序继续'],
                first_step_48h=f'{movement} 按原处方重量完成下次训练',
                upgrade_condition='完成后按原周期继续推进',
                hold_condition='RPE 明显高于往常时维持原重量一周',
                pause_condition='出现危险信号 → 暂停并做专业评估',
                first_week_focus=first_week_focus,
            )
        return ReturnPlan(
            days_off=days_off, permission='降级接回',
            normal_version='按原顺序继续',
            degraded_version='使用 30 分钟短版接回',
            minimal_version='—',
            next_7_days=['漏 2 次用原计划的 30 分钟版本接回, 仍不补课'],
            first_step_48h=f'{movement} 主项 3 组 @RPE 7 (30 分钟短版), 只做当天主线',
            upgrade_condition='完成 30 分钟版且次日恢复正常 → 回原处方',
            hold_condition='RPE 超 8 或次日仍疲劳 → 再走一次 30 分钟版',
            pause_condition='出现危险信号或疼痛加重 → 暂停并做专业评估',
            first_week_focus=first_week_focus,
        )

    if days_off <= 7:
        perm = '正常接回'
        normal_w, degraded_w, minimal_w = last_weight * 0.90, last_weight * 0.85, last_weight * 0.80
    elif days_off <= 21:
        perm = '降级接回'
        normal_w, degraded_w, minimal_w = last_weight * 0.85, last_weight * 0.75, last_weight * 0.70
    elif days_off <= 56:
        perm = '最低任务'
        normal_w, degraded_w, minimal_w = last_weight * 0.75, last_weight * 0.65, last_weight * 0.60
    elif days_off <= 84:
        perm = '最低任务'
        normal_w, degraded_w, minimal_w = last_weight * 0.70, last_weight * 0.60, last_weight * 0.55
    else:
        return ReturnPlan(
            days_off=days_off, permission='暂停',
            normal_version='建议重新建档',
            degraded_version='从 P0 阶段重新开始',
            minimal_version='先完成动作学习与重量校准',
            next_7_days=['重新建档', '动作重量校准(RPE 选重)', '生成新计划'],
            first_step_48h='完成一次 P0 校准训练: 每个动作 2×8 @RPE 6, 记录第二天感觉',
            upgrade_condition='校准训练后无痛且次日恢复正常 → 生成新计划',
            hold_condition='任一动作动作明显失控 → 降重量继续校准',
            pause_condition='出现危险信号 → 暂停并做专业评估',
            first_week_focus=first_week_focus,
        )

    def fmt(w):
        return f'{round(w*2)/2}kg' if w > 0 else '自重'

    plan = ReturnPlan(
        days_off=days_off, permission=perm,
        normal_version=f'{movement} {fmt(normal_w)} 3×8 @7 (正常版)',
        degraded_version=f'{movement} {fmt(degraded_w)} 3×10 @6 (降级版)',
        minimal_version=f'{movement} {fmt(minimal_w)} 2×12 @5 (最低版)',
        next_7_days=[
            f'第1天: {fmt(degraded_w)} 3×10 @6 (找回感觉, 不测极限)',
            f'第3天: {fmt(normal_w)} 4×8 @7 (感觉正常才加组)',
            f'第5天: {fmt(normal_w)} 4×6 @7.5 (接近原强度, 仍留 1-2 RIR)',
            '第7天: 评估恢复与意愿, 再决定是否回原周期',
        ],
        first_step_48h=(f'48 小时内先做 1 次: {movement} {fmt(degraded_w)} 3×10 @RPE 6 '
                        f'(组间休息 ≥2 分钟), 做完记录次日感觉'),
        upgrade_condition='48 小时版本完成且次日无异常疲劳、无疼痛 → 第 3 天可加组或回到正常版',
        hold_condition='RPE 高于预期或次日仍疲劳 → 维持当前档位再练 1-2 次, 不加量',
        pause_condition=('疼痛加重/胸痛/晕厥/麻木/放射痛或明显功能受限 → 暂停普通处方并做专业评估; '
                         '再次中断 ≥7 天 → 重新走接回流程'),
    )
    if condition_changed:
        plan.next_7_days.insert(0, '训练条件或能力已变化: 先按最低版完成 1 次, 再决定是否升级')
    return plan


def generate_short_version(workout: WorkoutDay, minutes: int) -> str:
    """生成最低执行版本

    规则: 短版优先保留当天主线，不补课、不加倍训练、不用惩罚性有氧
    """
    if minutes >= 30:
        return workout.short_version_30 or f'{workout.movement} 主项 3组 (保留顶组+1组回退)'
    elif minutes >= 20:
        return workout.short_version_20 or f'{workout.movement} 主项 2组 (仅顶组+1组)'
    elif minutes >= 10:
        return workout.short_version_10 or f'{workout.movement} 主项 1组 (仅顶组)'
    elif minutes >= 5:
        return workout.short_version_5 or f'{workout.movement} 1×5 @RPE 6 (最小维持剂量)'
    else:
        return workout.short_version_2 or f'{workout.movement} 热身激活 1×8 (只用 2 分钟保持连续性)'


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
        lines.append(f'组间休息: ≥{d.rest_seconds // 60} 分钟')
        if d.checkpoint:
            lines.append(f'技术检查点: {d.checkpoint}')
        lines.append('')
        if d.warmup:
            lines.append('热身: ' + ' → '.join(d.warmup))
            lines.append('')
        lines.append('| 组类型 | 重量 | 组×次 | RPE |')
        lines.append('|:------|:-----|:------|:----|')
        for st in d.sets:
            lines.append(f'| {st.set_type} | {st.weight}kg | {st.sets}×{st.reps} | {st.rpe_start}→{st.rpe_end} |')
        lines.extend([
            '',
            '短版:',
            f'- 30分钟: {d.short_version_30}',
            f'- 20分钟: {d.short_version_20}',
            f'- 10分钟: {d.short_version_10}',
            f'- 5分钟: {d.short_version_5}',
            f'- 2分钟: {d.short_version_2}',
            '',
        ])
    path = os.path.join(COACH_DIR, f'周期_{cycle.movement}_{cycle.start_date}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path