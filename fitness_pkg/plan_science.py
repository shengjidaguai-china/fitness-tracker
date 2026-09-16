"""
22 周训练计划的科学化视图 (v9.1 新增, ROADMAP F9)

职责: 把 `fitness_pkg/science.py` 的规则层接到「22 周居家平替计划」的展示口径上,
让训练计划页看到的是规则层的判断, 而不是另一份硬编码文案。

设计约定:
- 只做「规则 → 可读文本/参数」的换算, 不读个人数据、不引入随机性、不依赖 PySide6;
- 训练量统一按 Helms 的「组/周/肌群」计量 (每肌群每周 10–20 组起始区间)。
  周计划正文里写的是「单次训练该动作做几组」, 与周组数不是同一个量纲;
  这里只在能确定频率时才算周组数, 否则明确返回「不判定」, 不硬凑数字;
- 减载周不是「多练一点」: 减载周强度必须低于相邻实现周;
- 找不到规则层或解析不出组次时全部 fail-open, 页面照常渲染。
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .science import (
    WEEKLY_SET_CEILING,
    rpe_to_rir_text,
    weekly_set_band,
)

# 22 周减载周 (与 PHASE_INFO 口径一致: 体成分重组 W8/W13, 线条雕刻 W17/W21)
RHYTHMIC_DELOAD_WEEKS: Tuple[int, ...] = (8, 13, 17, 21)
# 减载周组数保留比例 (Helms: 反复低恢复时先把组数约减 20%)
DELOAD_VOLUME_RATIO = 0.8
# 每周最多统计几次训练日 (计划为 6 练 1 休, 上限取 6)
MAX_SESSIONS_PER_WEEK = 6

# 展示用肌群桶 → 训练计划里的动作关键词
MUSCLE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "背(宽)": ("引体", "下拉", "pullover", "直臂下压", "反向飞鸟", "面拉"),
    "背(厚)": ("划船", "俯身", "硬拉", "早安", "耸肩"),
    "胸": ("卧推", "飞鸟", "俯卧撑", "夹胸", "双杠", "臂屈伸"),
    "肩": ("肩推", "推举", "侧平举", "前平举", "肩上推"),
    "腿": ("深蹲", "分腿蹲", "弓步", "硬拉", "腿", "臀桥", "提踵", "罗马尼亚"),
    "手臂": ("弯举", "窄距", "锤式", "下压"),
    "核心/窄腰": ("真空腹", "卷腹", "平板", "鸟狗", "死虫", "腹"),
}

# 阶段 → 周期负荷权重 (Helms: 频率优先于目标; 阶段不是生理日历)
CYCLE_WEIGHT_BY_PHASE: Dict[int, float] = {1: 0.7, 2: 1.0, 3: 1.2}
# 长露出口径下的每周每肌群组数起点 (按训练等级分层的起始区间)
WEEKLY_SETS_BY_LEVEL: Dict[str, int] = {"P0": 8, "L1": 12, "L2": 14, "L3": 16}

# 复合主项休息下限 (秒), 用于把计划正文的动作备注翻成可执行的休息建议
_COMPOUND_REST_SECONDS = 150


def phase_of_week(week: int) -> int:
    """22 周三阶段: W1-6 基础建设, W7-14 体成分重组, W15-22 线条雕刻。"""
    w = max(1, int(week))
    return 1 if w <= 6 else (2 if w <= 14 else 3)


def is_deload_week(week: int) -> bool:
    """节律减载周判定 (W8/W13/W17/W21)。"""
    return max(1, int(week)) in RHYTHMIC_DELOAD_WEEKS


def parse_group_spec(sets_text: Any) -> Dict[str, Any]:
    """把正文里的「4组×8-10次」解析成 {'sets': 4, 'reps_low': 8, 'reps_high': 10}。

    解析不出时 `sets=0`, 调用方必须做 fail-open 处理, 不要当成 0 组去下结论。
    """
    out: Dict[str, Any] = {"sets": 0, "reps_low": None, "reps_high": None, "raw": str(sets_text or "").strip()}
    if not sets_text:
        return out
    text = str(sets_text)
    pair = re.search(r"(\d+)\s*(?:组|轮)?\s*[x×*]\s*(\d+)\s*(?:[-~—]\s*(\d+))?", text)
    if pair:
        out["sets"] = int(pair.group(1))
        out["reps_low"] = int(pair.group(2))
        out["reps_high"] = int(pair.group(3)) if pair.group(3) else int(pair.group(2))
        return out
    groups = re.search(r"(\d+)\s*(?:组|轮|循环)", text)
    if groups:
        out["sets"] = int(groups.group(1))
    return out


def muscle_bucket_of(name: str) -> Optional[str]:
    """按动作名归类到展示用肌群桶 (取最长关键词匹配); 无法归类时返回 None。"""
    text = str(name or "").lower()
    if not text:
        return None
    best: Optional[str] = None
    best_len = 0
    for bucket, keywords in MUSCLE_KEYWORDS.items():
        for kw in keywords:
            if kw in text and len(kw) > best_len:
                best, best_len = bucket, len(kw)
    return best


def count_workout_days(week_exercises: Dict[str, List[Dict[str, Any]]]) -> int:
    """统计一周里有真实动作的天数 (跳过热身/收尾/有氧等流程块与休息日)。"""
    days = 0
    for _day, items in (week_exercises or {}).items():
        if any(not ex.get("is_workout_block") and parse_group_spec(ex.get("sets"))["sets"] > 0 for ex in items or []):
            days += 1
    return min(days, MAX_SESSIONS_PER_WEEK)


def estimate_muscle_sets(day_exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
    """估算「单次训练日」各肌群的组数 (粗口径, 用于单次训练量自检)。

    口径: 只统计真实动作行; 正文「组×次」是该动作在本次训练做的组数;
    一个动作只计入它的主目标肌群 (协同肌不重复计数)。
    """
    buckets: Dict[str, int] = {}
    unclassified: List[str] = []
    for ex in day_exercises or []:
        if ex.get("is_workout_block"):
            continue
        name = str(ex.get("name") or "")
        parsed = parse_group_spec(ex.get("sets"))
        if parsed["sets"] <= 0:
            if name and not ex.get("target") == "收尾":
                unclassified.append(name)
            continue
        bucket = muscle_bucket_of(name)
        if bucket is None:
            unclassified.append(name)
            continue
        buckets[bucket] = buckets.get(bucket, 0) + parsed["sets"]
    return {
        "sets_by_muscle": dict(sorted(buckets.items())),
        "total_sets": sum(buckets.values()),
        "unclassified": unclassified,
        "note": "单次训练量, 按动作主目标肌群计入, 与「每周每肌群组数」不是同一口径",
    }


def estimate_weekly_sets(week_exercises: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """按一周 7 天各自的动作表汇总出「每周每肌群组数」(Helms 计量单位)。

    这是唯一可以把结果和 10–20 组起始区间直接比的函数。训练日数会一并返回,
    便于调用方判断结论是否可信 (训练日为 0 时直接不判定)。
    """
    totals: Dict[str, int] = {}
    day_sets: Dict[str, Dict[str, int]] = {}
    for day, items in (week_exercises or {}).items():
        estimate = estimate_muscle_sets(items)
        if not estimate["sets_by_muscle"]:
            continue
        day_sets[day] = estimate["sets_by_muscle"]
        for muscle, sets in estimate["sets_by_muscle"].items():
            totals[muscle] = totals.get(muscle, 0) + sets
    return {
        "sets_by_muscle": dict(sorted(totals.items())),
        "total_sets": sum(totals.values()),
        "training_days": len(day_sets),
        "day_breakdown": day_sets,
    }


def weekly_volume_status(
    week_exercises: Dict[str, List[Dict[str, Any]]],
    level: str = "L1",
) -> Dict[str, Any]:
    """把一周的组数汇总与 Helms 起始区间比对, 给出结论与调整方向。

    训练日数为 0 时返回「不判定」, 避免把「没解析到计划」误报成「练得太少」。
    """
    estimate = estimate_weekly_sets(week_exercises)
    low, high = weekly_set_band(level)
    if estimate["training_days"] == 0:
        return {
            "level": (level or "L1").upper(),
            "band": (low, high),
            "verdict": "不判定",
            "action": "计划正文未解析到有效组次 (或该周为休息周), 不做组数结论",
            "estimate": estimate,
            "items": [],
        }
    items = []
    for muscle, sets in estimate["sets_by_muscle"].items():
        if sets < low:
            verdict = "偏少"
            action = f"离起始区间下限还差 {low - sets} 组, 每次只加 1–2 组, 再看恢复"
        elif sets <= high:
            verdict = "合适"
            action = "落在起始区间内, 优先看表现与恢复趋势而不是继续加量"
        elif sets <= WEEKLY_SET_CEILING:
            verdict = "偏高"
            action = "仅在技术/睡眠/营养/恢复都可靠时才保留, 并写明何时回退"
        else:
            verdict = "超出验证区间"
            action = f"超过 {WEEKLY_SET_CEILING} 组/周需要专门试验与可归因的观察窗口"
        items.append({"muscle": muscle, "sets": sets, "band": (low, high), "verdict": verdict, "action": action})
    return {
        "level": (level or "L1").upper(),
        "band": (low, high),
        "verdict": "已判定",
        "action": f"{estimate['training_days']} 个训练日汇总",
        "estimate": estimate,
        "items": items,
    }


def day_execution_note(movement: str = "深蹲") -> Dict[str, Any]:
    """当日执行口径 (只用规则层里不依赖负重记录的部分, 可安全用于展示)。"""
    from .science import (
        MAX_RPE,
        build_rpe_path,
        classify_movement,
        failure_allowance,
        planned_rest_plan,
        rest_seconds,
        tempo_prescription,
    )

    kind = classify_movement(movement)
    lo, _hi = rest_seconds(movement)
    cap = MAX_RPE[kind]
    return {
        "movement_kind": kind,
        "rest_seconds": lo,
        "rest_plan": planned_rest_plan(movement, 3),
        "failure": failure_allowance(movement, 3, 3),
        "tempo": tempo_prescription(kind == "compound", "增肌"),
        "rpe_path_example": build_rpe_path(3, max(6.0, cap - 1.0), cap),
        "rpe_note": rpe_to_rir_text(cap),
        "rest_text": (
            f"复合主项组间休息 ≥{lo // 60} 分钟"
            if kind == "compound"
            else f"孤立动作组间休息 ≥{lo // 60} 分钟, 可与拮抗肌动作配对省时"
        ),
    }


def deload_guidance(signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """减载指引: 反应式信号 (命中 2 项即减载一周) + 节律减载周口径。"""
    from .science import evaluate_deload_signals

    verdict = evaluate_deload_signals(signals or {})
    return {
        "rhythmic_weeks": list(RHYTHMIC_DELOAD_WEEKS),
        "volume_ratio": DELOAD_VOLUME_RATIO,
        "rule": (
            f"节律减载周 (第 {', '.join(str(w) for w in RHYTHMIC_DELOAD_WEEKS)} 周) 组数约保留 "
            f"{int(DELOAD_VOLUME_RATIO * 100)}%, 强度必须低于相邻实现周, 不测试极限"
        ),
        **verdict,
    }


def week_display_meta(week: int, level: str = "L1", signals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """周视图展示元数据: 阶段口径 / 是否减载 / 周组数起点 / 减载指引。

    供 GUI 与报告共用, 保证页面文案与规则层同源。
    """
    w = max(1, int(week))
    phase = phase_of_week(w)
    low, high = weekly_set_band(level)
    deload = is_deload_week(w)
    return {
        "week": w,
        "phase": phase,
        "is_deload": deload,
        "cycle_weight": CYCLE_WEIGHT_BY_PHASE.get(phase, 1.0),
        "weekly_sets_hint": WEEKLY_SETS_BY_LEVEL.get((level or "L1").upper(), WEEKLY_SETS_BY_LEVEL["L1"]),
        "volume_note": (
            f"周组数按等级起始区间 {low}–{high} 组/肌群; 减载周组数约保留 {int(DELOAD_VOLUME_RATIO * 100)}%"
            if deload
            else f"周组数按等级起始区间 {low}–{high} 组/肌群, 先用下限再看恢复"
        ),
        "failure_policy": "复合主项不做力竭 (留 1–2 RIR), 孤立动作仅末组可接近",
        "short_version_rule": "漏 1 次不补课; 漏 2 次用 30 分钟或状态差版接回",
        "deload_guidance": deload_guidance(signals),
    }


def plan_science_summary(
    week_exercises: Dict[str, List[Dict[str, Any]]],
    day_exercises: Optional[List[Dict[str, Any]]] = None,
    week: int = 1,
    level: str = "L1",
    movement: str = "深蹲",
    signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """一次训练日的完整科学化视图 (周元数据 + 周组数判定 + 单次量 + 执行口径)。"""
    summary = week_display_meta(week, level, signals)
    summary["weekly_volume"] = weekly_volume_status(week_exercises, level)
    summary["day_volume"] = estimate_muscle_sets(day_exercises or [])
    summary["execution"] = day_execution_note(movement)
    summary["training_days"] = count_workout_days(week_exercises)
    return summary
