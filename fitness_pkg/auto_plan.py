"""
输入驱动方案生成 (v9.2 新增, Issue #5)

两条链路:
1. 体测输入 (当前体重/体脂 + 目标体重/体脂) → 训练计划 + 训练动作
2. 月度伙食费预算 → 每日饮食计划 + 不伤身体的补剂建议

设计约定:
- 纯逻辑, 不依赖 PySide6 / numpy / pandas, 因此可在 CI 与 CLI 直接跑;
- 只复用仓库既有口径 (`science` 的组数区间/负荷换算, `NutritionParser` 的补剂与餐次,
  `plan_science` 的周期视图), 不另起一套规则; 同一结论在两处出现时以规则层为准;
- 不吐医疗建议: 补剂只给"常识档 + 剂量上限 + 禁忌", 并明确列出就医/化验触发条件;
- 所有结论都带一句口径说明, 让用户知道这个数字是怎么来的、什么时候不该信它。
"""

from typing import Any, Dict, List, Optional

from .parsers import NutritionParser, TrainingPlanParser
from .plan_science import is_deload_week, phase_of_week, week_display_meta, weekly_volume_status
from .science import (
    WEEKLY_SET_CEILING,
    e1rm_from_set,
    load_for_target_reps,
    weekly_set_band,
)

# ── 安全与校验阈值 ──────────────────────────────────────────
MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 250.0
MIN_BODYFAT_PCT = 3.0
MAX_BODYFAT_PCT = 60.0
MIN_BUDGET = 300.0
MAX_BUDGET = 20000.0
MIN_HEIGHT_CM = 140.0
MAX_HEIGHT_CM = 220.0
MIN_AGE = 16
MAX_AGE = 80

# 每周减重/增重速度上限 (占体重比例)。高于上限的部分靠延长周期解决, 不靠加大缺口。
MAX_WEEKLY_LOSS_RATIO = 0.01
MAX_WEEKLY_GAIN_RATIO = 0.0025
# 低于此体脂率时不再安排减脂方向, 直接提示就医评估
ESSENTIAL_FAT_ALERT = {"male": 5.0, "female": 12.0}

# 蛋白质与脂肪的相对摄入区间 (g/kg 体重)
PROTEIN_G_PER_KG = (1.6, 2.2)
FAT_G_PER_KG = (0.6, 1.0)
KCAL_PER_KG_FAT = 7700.0

# 每公斤去脂体重的默认能量估算系数 (kcal/kg), 仅用于没填身高时的兜底
KCAL_PER_KG_BODYWEIGHT = 33.0

# 训练水平 → 平台动作 + 每日组数档位 (动作名与动作库/计划正文同名, 便于点开看示范)
LEVEL_CATALOG: Dict[str, Dict[str, Any]] = {
    "P0": {
        "label": "启动/回归期",
        "sessions": 3,
        "sets_per_movement": (2, 3),
        "reps": (8, 12),
        "rpe": (6.0, 7.0),
        "note": "先把动作做熟、留下可比较的基准, 动作质量优先于重量",
    },
    "L1": {
        "label": "动作稳定期",
        "sessions": 4,
        "sets_per_movement": (3, 4),
        "reps": (6, 10),
        "rpe": (7.0, 8.0),
        "note": "线性或双重渐进: 先把次数做满, 再加最小一档重量",
    },
    "L2": {
        "label": "周管理期",
        "sessions": 5,
        "sets_per_movement": (3, 5),
        "reps": (5, 10),
        "rpe": (7.5, 8.5),
        "note": "按周管理训练量与强度, 一次只推进一个主要变量",
    },
    "L3": {
        "label": "阶段进步期",
        "sessions": 6,
        "sets_per_movement": (4, 6),
        "reps": (3, 8),
        "rpe": (8.0, 9.0),
        "note": "阶段化 + 疲劳管理, 高负荷暴露与减载必须成对出现",
    },
}

# 每周分化模板 (每个元素 = 一天的训练主题 + 该天的主/辅动作)
_SPLITS: Dict[int, List[Dict[str, Any]]] = {
    3: [
        {
            "day": "周一",
            "title": "全身 A",
            "focus": "下肢推 + 水平拉",
            "main": ["Goblet深蹲", "单臂哑铃划船", "上斜哑铃卧推"],
            "assist": ["死虫式", "平板支撑"],
        },
        {
            "day": "周三",
            "title": "全身 B",
            "focus": "下肢拉 + 垂直推/拉",
            "main": ["罗马尼亚硬拉", "宽握引体", "坐姿肩推"],
            "assist": ["侧平举", "真空腹"],
        },
        {
            "day": "周五",
            "title": "全身 C",
            "focus": "单腿 + 上背容量",
            "main": ["保加利亚分腿蹲", "对握引体", "俯身划船"],
            "assist": ["锤式弯举", "鸟狗式"],
        },
    ],
    4: [
        {
            "day": "周一",
            "title": "上肢推",
            "focus": "胸/肩/三头",
            "main": ["上斜哑铃卧推", "坐姿肩推", "哑铃飞鸟"],
            "assist": ["椅子臂屈伸", "侧平举"],
        },
        {
            "day": "周二",
            "title": "上肢拉",
            "focus": "背宽 + 背厚",
            "main": ["宽握引体", "单臂哑铃划船", "对握引体"],
            "assist": ["俯身划船", "锤式弯举"],
        },
        {
            "day": "周四",
            "title": "下肢",
            "focus": "股四 + 后链",
            "main": ["Goblet深蹲", "罗马尼亚硬拉", "保加利亚分腿蹲"],
            "assist": ["臀桥", "提踵"],
        },
        {
            "day": "周六",
            "title": "核心与肩袖",
            "focus": "窄腰 + 肩健康",
            "main": ["平板支撑", "侧平举", "弹力带面拉"],
            "assist": ["真空腹", "死虫式"],
        },
    ],
    5: [
        {
            "day": "周一",
            "title": "背(宽)",
            "focus": "背阔宽度",
            "main": ["宽握引体", "反握引体", "单臂哑铃划船"],
            "assist": ["哑铃Pullover", "直臂下压"],
        },
        {
            "day": "周二",
            "title": "胸+三头",
            "focus": "上胸优先",
            "main": ["上斜哑铃卧推", "哑铃飞鸟", "椅子臂屈伸"],
            "assist": ["俯卧撑", "窄距俯卧撑"],
        },
        {
            "day": "周三",
            "title": "腿",
            "focus": "哑铃复合",
            "main": ["Goblet深蹲", "罗马尼亚硬拉", "保加利亚分腿蹲"],
            "assist": ["臀桥", "提踵"],
        },
        {
            "day": "周四",
            "title": "背(厚)+二头",
            "focus": "上背厚度",
            "main": ["对握引体", "胸支撑哑铃划船", "俯身划船"],
            "assist": ["锤式弯举", "哑铃弯举"],
        },
        {
            "day": "周五",
            "title": "肩+核心",
            "focus": "中束 + 肩袖 + 窄腰",
            "main": ["坐姿肩推", "侧平举", "弹力带面拉"],
            "assist": ["俯身飞鸟", "真空腹"],
        },
    ],
    6: [
        {
            "day": "周一",
            "title": "背(宽)",
            "focus": "背阔宽度",
            "main": ["宽握引体", "反握引体", "单臂哑铃划船"],
            "assist": ["哑铃Pullover", "直臂下压"],
        },
        {
            "day": "周二",
            "title": "胸+三头",
            "focus": "上胸优先",
            "main": ["上斜哑铃卧推", "哑铃飞鸟", "椅子臂屈伸"],
            "assist": ["俯卧撑", "窄距俯卧撑"],
        },
        {
            "day": "周三",
            "title": "腿",
            "focus": "哑铃复合",
            "main": ["Goblet深蹲", "罗马尼亚硬拉", "保加利亚分腿蹲"],
            "assist": ["臀桥", "提踵"],
        },
        {
            "day": "周四",
            "title": "背(厚)+二头",
            "focus": "上背厚度",
            "main": ["对握引体", "胸支撑哑铃划船", "俯身划船"],
            "assist": ["锤式弯举", "哑铃弯举"],
        },
        {
            "day": "周五",
            "title": "肩+核心",
            "focus": "中束 + 肩袖 + 窄腰",
            "main": ["坐姿肩推", "侧平举", "弹力带面拉"],
            "assist": ["俯身飞鸟", "真空腹"],
        },
        {
            "day": "周六",
            "title": "推+腿泵感",
            "focus": "低疲劳循环",
            "main": ["上斜哑铃卧推", "Goblet深蹲", "椅子臂屈伸"],
            "assist": ["俯卧撑循环", "侧平举"],
        },
    ],
}

# 补剂: 只保留有共识基础、可长期吃且剂量明确的品类。
# tier: core = 先补这个; optional = 有余钱再补; food_first = 优先从食物拿, 预算紧就取消。
SUPPLEMENT_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "乳清蛋白粉",
        "tier": "core",
        "unit_cost": 0.24,  # 元/克
        "dose_g": 30,
        "timing": "训练后 30 分钟内, 或任意一餐蛋白不足时",
        "purpose": "把每日蛋白补齐到目标量",
        "upper_note": "肾功能异常者需先咨询医生; 乳糖不耐受选分离乳清",
    },
    {
        "name": "肌酸单水合物",
        "tier": "core",
        "unit_cost": 0.30,
        "dose_g": 5,
        "timing": "任意固定时间, 与餐同服即可",
        "purpose": "力量与训练容量支持 (证据最扎实的一档)",
        "upper_note": "每日 5g 足够, 不需要冲击期; 每天额外多喝水 500ml",
    },
    {
        "name": "维生素D3",
        "tier": "core",
        "unit_cost": 0.50,  # 元/天 (IU 计价太碎, 按日成本给)
        "dose_g": 0,
        "dose_text": "1000–2000 IU",
        "timing": "随含脂餐",
        "purpose": "室内训练/冬季日照不足时的基础补充",
        "upper_note": "上限 4000 IU/天; 有条件先查血清 25(OH)D 再定剂量",
    },
    {
        "name": "鱼油 (EPA/DHA)",
        "tier": "optional",
        "unit_cost": 0.30,
        "dose_g": 1.5,
        "timing": "随餐",
        "purpose": "抗炎与恢复支持",
        "upper_note": "日常 1–2g EPA+DHA; 服用抗凝药者先问医生",
    },
    {
        "name": "柠檬酸镁 / 甘氨酸镁",
        "tier": "food_first",
        "unit_cost": 0.40,
        "dose_g": 0,
        "dose_text": "200–300 mg 元素镁",
        "timing": "睡前 1 小时",
        "purpose": "缓解抽筋、帮助睡眠",
        "upper_note": "优先靠坚果/深绿叶菜/豆类补齐; 上限 350mg/天, 过量会腹泻",
    },
    {
        "name": "锌",
        "tier": "food_first",
        "unit_cost": 0.25,
        "dose_g": 0,
        "dose_text": "10–15 mg",
        "timing": "随餐, 与钙铁错开",
        "purpose": "补足红肉/贝类摄入不足时的缺口",
        "upper_note": "上限 40mg/天, 长期大剂量会干扰铜吸收",
    },
]

# 补剂红线: 出现在清单里就直接劝退 (不伤身体是硬条件)
SUPPLEMENT_RED_LINES = (
    "不碰「燃脂丸 / 左旋肉碱+咖啡因堆叠 / DNP / 克伦特罗」这类以刺激或产热为主的减脂产品",
    "不碰来路不明的「增睾 / 促生长」产品与任何注射类制剂",
    "不使用利尿剂或脱水类手段压秤",
    "补剂是「补齐缺口」, 剂量按标签上限走, 不叠加同类成分",
)

# ── 预算 → 食材单价 (元/100g 或 元/个), 用于把预算折成可执行的采购清单 ──
BUDGET_UNIT_PRICES: Dict[str, float] = {
    "鸡蛋": 1.6,  # 元/个
    "鸡胸肉": 4.0,  # 元/100g
    "瘦牛肉": 9.0,
    "三文鱼/冷冻鱼柳": 8.0,
    "全脂牛奶": 0.9,  # 元/100ml
    "无糖豆浆": 0.5,
    "大米/糙米(生)": 0.7,
    "燕麦片(干)": 1.2,
    "红薯": 0.6,
    "全麦面包": 1.5,  # 元/片
    "香蕉": 1.5,  # 元/根
    "混合蔬菜/西兰花": 1.2,
    "豆制品(豆腐/豆干)": 1.2,
    "花生/坚果": 4.0,
    "橄榄油/食用油": 3.0,
}

# 每日五餐结构 (与 NutritionParser.DAILY_MEALS 同构, 但份量按个人热量目标缩放)
MEAL_TEMPLATE = (
    ("早餐 (07:00)", 0.22, ("鸡蛋", "燕麦片(干)", "全脂牛奶")),
    ("加餐 (10:00)", 0.22, ("鸡胸肉", "红薯", "花生/坚果")),
    ("午餐 (12:30)", 0.26, ("大米/糙米(生)", "鸡胸肉", "混合蔬菜/西兰花")),
    ("训练前加餐 (16:30)", 0.12, ("全麦面包", "香蕉", "无糖豆浆")),
    ("训练后 (19:00)", 0.10, ("乳清蛋白粉", "香蕉")),
    ("晚餐 (20:30)", 0.08, ("三文鱼/冷冻鱼柳", "混合蔬菜/西兰花", "橄榄油/食用油")),
)


# ═══════════════════════════════════════════════════════════
# 一、输入校验
# ═══════════════════════════════════════════════════════════


def validate_body_inputs(
    current_weight: Any,
    current_bodyfat: Any = None,
    target_weight: Any = None,
    target_bodyfat: Any = None,
    height_cm: Any = None,
    age: Any = None,
    sex: str = "male",
) -> Dict[str, Any]:
    """校验体测输入, 返回可直接喂给生成器的干净参数。

    非法输入一律在这里拦住并给出可读原因, 不让下游用「0 kg / 0% 体脂」跑出荒谬方案。
    """
    errors: List[str] = []
    warnings: List[str] = []

    def _num(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    cur_w = _num(current_weight)
    if cur_w is None:
        errors.append("请填写当前体重 (kg)")
    elif not (MIN_WEIGHT_KG <= cur_w <= MAX_WEIGHT_KG):
        errors.append(f"当前体重需在 {MIN_WEIGHT_KG:.0f}–{MAX_WEIGHT_KG:.0f} kg 之间, 请检查单位是否为 kg")

    cur_f = _num(current_bodyfat)
    if cur_f is not None and not (MIN_BODYFAT_PCT <= cur_f <= MAX_BODYFAT_PCT):
        errors.append(f"当前体脂率需在 {MIN_BODYFAT_PCT:.0f}–{MAX_BODYFAT_PCT:.0f}% 之间")
    if cur_f is None:
        warnings.append("未填当前体脂率: 方向判断改用 BMI 与体重趋势, 精度会下降")

    tgt_w = _num(target_weight)
    if tgt_w is not None and not (MIN_WEIGHT_KG <= tgt_w <= MAX_WEIGHT_KG):
        errors.append(f"目标体重需在 {MIN_WEIGHT_KG:.0f}–{MAX_WEIGHT_KG:.0f} kg 之间")

    tgt_f = _num(target_bodyfat)
    if tgt_f is not None and not (MIN_BODYFAT_PCT <= tgt_f <= MAX_BODYFAT_PCT):
        errors.append(f"目标体脂率需在 {MIN_BODYFAT_PCT:.0f}–{MAX_BODYFAT_PCT:.0f}% 之间")

    h = _num(height_cm)
    if h is not None and not (MIN_HEIGHT_CM <= h <= MAX_HEIGHT_CM):
        errors.append(f"身高需在 {MIN_HEIGHT_CM:.0f}–{MAX_HEIGHT_CM:.0f} cm 之间")

    a = int(_num(age) or 0)
    if a and not (MIN_AGE <= a <= MAX_AGE):
        errors.append(f"年龄需在 {MIN_AGE}–{MAX_AGE} 岁之间")

    if cur_w is not None and tgt_w is not None and tgt_w > cur_w and cur_f is not None and tgt_f is not None:
        if tgt_f < cur_f:
            warnings.append("目标体重上升但目标体脂下降: 属于「增肌减脂」双目标, 周期会明显拉长, 先用 8–12 周看趋势")

    essential = ESSENTIAL_FAT_ALERT.get((sex or "male").lower(), ESSENTIAL_FAT_ALERT["male"])
    if cur_f is not None and cur_f <= essential:
        warnings.append(f"当前体脂已接近必需脂肪区间 (≤{essential:.0f}%), 不建议继续减脂, 请先做医学评估")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "current_weight": cur_w,
        "current_bodyfat": cur_f,
        "target_weight": tgt_w,
        "target_bodyfat": tgt_f,
        "height_cm": h,
        "age": a or None,
        "sex": (sex or "male").lower(),
    }


def validate_budget(budget: Any) -> Dict[str, Any]:
    """校验月度伙食费预算。"""
    try:
        value = float(budget)
    except (TypeError, ValueError):
        return {"ok": False, "errors": ["请填写每月伙食费预算 (元)"], "monthly_budget": None}
    if not (MIN_BUDGET <= value <= MAX_BUDGET):
        return {
            "ok": False,
            "errors": [f"预算需在 {MIN_BUDGET:.0f}–{MAX_BUDGET:.0f} 元/月之间"],
            "monthly_budget": None,
        }
    return {"ok": True, "errors": [], "monthly_budget": value}


# ═══════════════════════════════════════════════════════════
# 二、体成分 → 目标与周期
# ═══════════════════════════════════════════════════════════


def body_composition_plan(
    current_weight: float,
    current_bodyfat: Optional[float] = None,
    target_weight: Optional[float] = None,
    target_bodyfat: Optional[float] = None,
    height_cm: Optional[float] = None,
) -> Dict[str, Any]:
    """把「当前体测 + 目标体测」折成方向、速度上限与周期长度。

    核心约束: 缺口再大也不允许周速度超过体重 1% (减) / 0.25% (增),
    因为超出部分的代价是肌肉流失与代谢适应, 而不是更快的进度。
    """
    cur_w = float(current_weight or 0)
    if cur_w <= 0:
        return {"ok": False, "errors": ["当前体重无效, 无法生成计划"]}

    cur_f = current_bodyfat
    tgt_f = target_bodyfat

    fat_now = cur_w * cur_f / 100.0 if cur_f is not None else None
    lean_now = cur_w - fat_now if fat_now is not None else None

    # 目标体重口径: 用户填了就以用户填的为准 (他只填体脂目标时才按去脂体重守恒推算)。
    # 反过来做会让「想增重到 72kg」被推成 65kg, 方向判断直接反了。
    weight_from_fat = None
    if lean_now is not None and tgt_f is not None and 0 < tgt_f < 100:
        weight_from_fat = lean_now / (1 - tgt_f / 100.0)
    if target_weight is not None:
        suggested_target_weight = float(target_weight)
        if weight_from_fat is not None and abs(suggested_target_weight - weight_from_fat) > 0.5:
            weight_note = (
                f"你填的目标体重 {suggested_target_weight:.1f} kg 与「保住去脂体重、只掉脂肪」的推算值 "
                f"{weight_from_fat:.1f} kg 差 {abs(suggested_target_weight - weight_from_fat):.1f} kg; "
                "按你填的来, 但周期与热量按更保守的那个走"
            )
        else:
            weight_note = f"目标体重采用你填写的 {suggested_target_weight:.1f} kg"
    elif weight_from_fat is not None:
        suggested_target_weight = weight_from_fat
        weight_note = f"未填目标体重, 按去脂体重守恒 + 目标体脂推算出 {suggested_target_weight:.1f} kg"
    else:
        suggested_target_weight = cur_w
        weight_note = "既未填目标体重也未填目标体脂: 按维持体重与体成分重组安排"

    delta = suggested_target_weight - cur_w
    # 阈值 0.5kg: 小于它的目标变化属于「换体成分」而不是「减重/增重」,
    # 否则 70kg→18% 这种小改动会被算成 1.7kg 的减脂周期。
    if abs(delta) < 0.5:
        direction, direction_label = "recomp", "体成分重组 (体重基本不变, 换体脂)"
    elif delta < 0:
        direction, direction_label = "cut", "减脂 (保留肌肉是硬约束)"
    else:
        direction, direction_label = "bulk", "增肌 (控制脂肪涨幅)"

    # 周期长度: 按允许的最大周速度反推, 不按「想几周完成」
    planned_weekly = 0.0
    if direction == "cut":
        planned_weekly = min(abs(delta) / 12.0, cur_w * MAX_WEEKLY_LOSS_RATIO) if delta else 0.0
        min_weeks = max(8, int(abs(delta) / max(planned_weekly, 0.01) + 0.999))
    elif direction == "bulk":
        planned_weekly = min(abs(delta) / 12.0, cur_w * MAX_WEEKLY_GAIN_RATIO) if delta else 0.0
        min_weeks = max(12, int(abs(delta) / max(planned_weekly, 0.01) + 0.999))
    else:
        min_weeks = 12

    weeks = min(24, max(8, (min_weeks + 3) // 4 * 4))  # 收敛到 4 的倍数, 便于按中周期排减载

    return {
        "ok": True,
        "direction": direction,
        "direction_label": direction_label,
        "current_weight": round(cur_w, 1),
        "current_bodyfat": cur_f,
        "current_fat_mass": round(fat_now, 1) if fat_now is not None else None,
        "current_lean_mass": round(lean_now, 1) if lean_now is not None else None,
        "target_weight": round(suggested_target_weight, 1),
        "target_bodyfat": tgt_f,
        "target_lean_mass": round(lean_now, 1) if lean_now is not None else None,
        "weight_delta": round(delta, 1),
        "weekly_rate_cap": round(cur_w * MAX_WEEKLY_LOSS_RATIO, 2)
        if direction != "bulk"
        else round(cur_w * MAX_WEEKLY_GAIN_RATIO, 2),
        "planned_weekly_rate": round(planned_weekly, 2),
        "weeks": weeks,
        "bmi": round(cur_w / ((height_cm / 100.0) ** 2), 1) if height_cm else None,
        "weight_note": weight_note,
        "rate_note": (
            f"减脂周速度上限 {cur_w * MAX_WEEKLY_LOSS_RATIO:.2f} kg/周 (体重 1%); "
            "更快通常意味着掉的是肌肉与水分, 也要用更长周期补回来"
            if direction == "cut"
            else f"增肌周速度上限 {cur_w * MAX_WEEKLY_GAIN_RATIO:.2f} kg/周 (体重 0.25%); 再快基本都是脂肪"
            if direction == "bulk"
            else "体重不动时看腰围与体脂率变化, 单看秤容易误判"
        ),
    }


# ═══════════════════════════════════════════════════════════
# 三、体测 → 训练水平与训练计划 (含动作)
# ═══════════════════════════════════════════════════════════


def infer_level(
    current_weight: float,
    current_bodyfat: Optional[float] = None,
    target_bodyfat: Optional[float] = None,
    height_cm: Optional[float] = None,
    training_age_months: int = 0,
) -> Dict[str, Any]:
    """按体成分与训练年限给出 P0–L3 训练等级。

    只用于「计划密度与组数档位」, 不评价体型好坏; 判定依据全部写回 `reasons`。
    """
    months = max(0, int(training_age_months or 0))
    bmi = current_weight / ((height_cm / 100.0) ** 2) if height_cm else None
    fat = current_bodyfat

    score = 0
    reasons: List[str] = []

    if months < 1:
        reasons.append("训练年限 <1 个月: 先建立可重复动作")
    elif months < 6:
        score += 1
        reasons.append("训练年限 1–6 个月: 可线性渐进")
    elif months < 24:
        score += 2
        reasons.append("训练年限 6–24 个月: 需要按周管理变量")
    else:
        score += 3
        reasons.append("训练年限 >24 个月: 需要阶段化与疲劳管理")

    if fat is not None:
        if fat >= 30:
            score -= 1
            reasons.append(f"体脂 {fat:.1f}% 偏高: 先保证关节负荷可控, 别急着上大重量")
        elif fat <= 10:
            score += 1
            reasons.append(f"体脂 {fat:.1f}% 偏低: 训练量承受力好, 但要盯住恢复")

    if bmi is not None and bmi >= 32:
        score -= 1
        reasons.append(f"BMI {bmi:.1f} 偏高: 跳跃类与高冲击动作先替代")

    if target_bodyfat is not None and fat is not None and target_bodyfat < fat:
        reasons.append(f"目标体脂 {target_bodyfat:.1f}% < 当前 {fat:.1f}%: 减脂期优先保住力量表现")

    level = "P0" if score <= 0 else "L1" if score == 1 else "L2" if score == 2 else "L3"
    cfg = LEVEL_CATALOG[level]
    return {
        "level": level,
        "label": cfg["label"],
        "sessions_per_week": cfg["sessions"],
        "weekly_sets_band": weekly_set_band(level),
        "score": score,
        "reasons": reasons,
        "note": "等级只决定计划密度与组数档位; 单次状态差不改等级",
    }


def _scale_sets(schedule: Dict[str, Any], cfg: Dict[str, Any], week: int) -> Dict[str, Any]:
    """把分化模板折算成「本周、本动作」的组数×次数×RPE, 减载周按规则层口径下调。"""
    sets_low, sets_high = cfg["sets_per_movement"]
    reps_low, reps_high = cfg["reps"]
    rpe_low, rpe_high = cfg["rpe"]
    deload = is_deload_week(week)

    main_sets = sets_high if schedule.get("is_main") else sets_low
    if deload:
        main_sets = max(1, main_sets - 1)
        reps_low, reps_high = max(5, reps_low - 2), max(reps_low, reps_high - 2)
        rpe_low, rpe_high = max(4.0, rpe_low - 1.5), max(5.0, rpe_high - 1.5)

    return {
        "sets": main_sets,
        "reps_low": reps_low,
        "reps_high": reps_high,
        "rpe": (round(rpe_low, 1), round(rpe_high, 1)),
        "sets_text": f"{main_sets}×{reps_low}-{reps_high}" if reps_low != reps_high else f"{main_sets}×{reps_low}",
        "is_deload": deload,
    }


def _estimate_start_load(current_weight: float, sex: str = "male") -> Dict[str, float]:
    """无 1RM 记录时的起点负荷: 按体重比例给一个保守系数, 再折算成建议重量。

    这是起点而非处方; 第一次训练按 RPE 6–7 选重, 用实际表现替换它。
    """
    ratio = {"male": 0.55, "female": 0.40}.get((sex or "male").lower(), 0.55)
    base_1rm = current_weight * ratio
    return {
        "assumed_1rm": round(base_1rm, 1),
        "note": (
            f"用体重 ×{ratio:.2f} 估的起点 e1RM {base_1rm:.1f} kg; "
            "第一次按 RPE 6–7 试重, 之后一律用实际做的重量×次数替换, 只作趋势观察"
        ),
    }


def generate_training_plan(
    current_weight: float,
    current_bodyfat: Optional[float] = None,
    target_weight: Optional[float] = None,
    target_bodyfat: Optional[float] = None,
    height_cm: Optional[float] = None,
    sex: str = "male",
    training_age_months: int = 0,
    weeks: Optional[int] = None,
    week: int = 1,
    plan_parser: Optional[TrainingPlanParser] = None,
) -> Dict[str, Any]:
    """由体测输入直接生成训练计划: 方向 → 等级 → 分化 → 每周每日动作与组次。

    找不到本地 22 周计划正文时, 全部按内置模板输出 (fail-open), 保证无个人数据也能用。
    """
    comp = body_composition_plan(current_weight, current_bodyfat, target_weight, target_bodyfat, height_cm)
    if not comp.get("ok"):
        return {"ok": False, "errors": comp.get("errors", [])}

    level_info = infer_level(current_weight, current_bodyfat, target_bodyfat, height_cm, training_age_months)
    total_weeks = int(weeks or comp["weeks"])
    level = level_info["level"]
    cfg = LEVEL_CATALOG[level]
    sessions = cfg["sessions"]
    split = _SPLITS[sessions]
    load = _estimate_start_load(current_weight, sex)

    days: List[Dict[str, Any]] = []
    for spec in split:
        day_sets: List[Dict[str, Any]] = []
        for idx, name in enumerate(list(spec["main"]) + list(spec["assist"])):
            prescription = _scale_sets({"is_main": idx < len(spec["main"])}, cfg, week)
            day_sets.append({"name": name, "is_main": idx < len(spec["main"]), **prescription})
        days.append(
            {
                "day": spec["day"],
                "title": spec["title"],
                "focus": spec["focus"],
                "exercises": day_sets,
                "estimated_sets": sum(d["sets"] for d in day_sets),
            }
        )

    week_names = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
    trained = {d["day"] for d in days}
    rest_days = [name for name in week_names if name not in trained]
    day_sets_total = {d["day"]: d["estimated_sets"] for d in days}
    # 交给规则层做周组数判定: 只统计有真实动作行的训练日, 不自己另算一套
    weekly_exercises = {
        d["day"]: [{"name": ex["name"], "sets": ex["sets_text"]} for ex in d["exercises"] if ex["is_main"]]
        or [{"name": ex["name"], "sets": ex["sets_text"]} for ex in d["exercises"]]
        for d in days
    }
    weekly = weekly_volume_status(weekly_exercises, level)

    meta = week_display_meta(week, level)
    return {
        "ok": True,
        "weeks": total_weeks,
        "week": week,
        "phase": phase_of_week(week),
        "level": level,
        "level_label": level_info["label"],
        "level_reasons": level_info["reasons"],
        "sessions_per_week": sessions,
        "volume_band": list(weekly_set_band(level)),
        "volume_ceiling": WEEKLY_SET_CEILING,
        "weekly_volume": weekly,
        "days": days,
        "rest_days": rest_days,
        "day_sets_total": day_sets_total,
        "start_load": load,
        "deload": meta["is_deload"],
        "deload_note": meta["volume_note"],
        "short_version_rule": meta["short_version_rule"],
        "composition": comp,
        "load_example": {
            "movement": "Goblet深蹲",
            "assumed_1rm": load["assumed_1rm"],
            "working_weight_at_rpe7": load_for_target_reps(load["assumed_1rm"], 8, 7.0),
            "e1rm_from_example_set": e1rm_from_set(20.0, 8, 8.0),
        },
        "cautions": _training_cautions(comp, level_info),
    }


def _training_cautions(comp: Dict[str, Any], level_info: Dict[str, Any]) -> List[str]:
    """训练侧安全提示: 来自「方向 + 等级」的可执行约束, 不是泛泛的建议。"""
    cautions = [
        "复合主项留 1–2 RIR, 不做力竭; 孤立动作只剩末组可接近力竭",
        "组间休息: 复合主项 ≥2.5 分钟, 孤立动作 ≥1.5 分钟; 不要为省时压缩复合主项",
        "单次状态差不改结构; 连续两次异常才怀疑周期",
    ]
    if comp.get("direction") == "cut":
        cautions.append("减脂期强度不掉、只掉体重: 力量明显下滑就先加 1–2 餐碳水而不是加练")
    if comp.get("direction") == "bulk":
        cautions.append("增肌期周增重超过 0.25% 体重就下调热量, 别把脂肪一起加上去")
    if level_info.get("level") == "P0":
        cautions.append("前 2 周不加到力竭、不做跳跃与爆发动作, 先把动作轨迹固定")
    cautions.append("出现胸痛/晕厥/麻木或放射痛: 立刻停止训练并就医")
    return cautions


def generate_training_markdown(plan: Dict[str, Any]) -> str:
    """把训练计划渲染成可直接贴进 Issue / 报告的 Markdown。"""
    if not plan.get("ok"):
        return "\n".join(f"- ⚠ {e}" for e in plan.get("errors", ["输入无效"]))
    comp = plan["composition"]
    lines = [
        f"### 训练计划 (第 {plan['week']}/{plan['weeks']} 周 · 阶段 {plan['phase']})",
        "",
        f"- 方向: **{comp['direction_label']}** · 目标 {comp['target_weight']} kg"
        + (f" / 体脂 {comp['target_bodyfat']:.1f}%" if comp.get("target_bodyfat") else ""),
        f"- 训练等级: **{plan['level']} ({plan['level_label']})** — {'; '.join(plan['level_reasons'])}",
        f"- 频率: 每周 {plan['sessions_per_week']} 练, 休息日 {'/'.join(plan['rest_days']) or '—'}",
        f"- 周组数起始区间: {plan['volume_band'][0]}–{plan['volume_band'][1]} 组/肌群"
        f" (≥{plan['volume_ceiling']} 组需专门试验)",
        f"- 起点负荷: {plan['start_load']['note']}",
    ]
    if plan["deload"]:
        lines.append(f"- ⚠ 本周为节律减载周: {plan['deload_note']}")
    lines.append("")
    for day in plan["days"]:
        lines.append(f"**{day['day']} · {day['title']}** — {day['focus']} (约 {day['estimated_sets']} 组)")
        lines.append("")
        lines.append("| 动作 | 组×次 | 组数 | RPE |")
        lines.append("|:--|:--|--:|:--|")
        for ex in day["exercises"]:
            tag = "" if ex["is_main"] else " (辅助)"
            lines.append(f"| {ex['name']}{tag} | {ex['sets_text']} | {ex['sets']} | {ex['rpe'][0]}–{ex['rpe'][1]} |")
        lines.append("")
    lines.append("**执行纪律**")
    lines.append("")
    lines.extend(f"- {c}" for c in plan["cautions"])
    lines.append(f"- {plan['short_version_rule']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 四、预算 → 热量与宏量
# ═══════════════════════════════════════════════════════════


def plan_energy(
    current_weight: float,
    current_bodyfat: Optional[float] = None,
    target_weight: Optional[float] = None,
    sex: str = "male",
) -> Dict[str, Any]:
    """按方向给出每日热量与三大宏量 (克 + 折算克/公斤体重)。

    热量只是起点: 2 周后按体重趋势校准, 而不是死守这个数字。
    """
    cur_w = float(current_weight or 0)
    if cur_w <= 0:
        return {"ok": False, "errors": ["当前体重无效, 无法估算热量"]}

    bmr = KCAL_PER_KG_BODYWEIGHT * cur_w
    direction = "recomp"
    tgt_w = target_weight if target_weight is not None else cur_w
    if tgt_w < cur_w - 0.3:
        direction = "cut"
    elif tgt_w > cur_w + 0.3:
        direction = "bulk"

    ratio = {"cut": 0.85, "recomp": 1.0, "bulk": 1.10}[direction]
    kcal = round(bmr * ratio / 10) * 10

    protein_low, protein_high = PROTEIN_G_PER_KG
    if direction == "cut":
        protein_g = round(cur_w * protein_high)  # 缺口期蛋白取上限, 保住肌肉
    elif direction == "bulk":
        protein_g = round(cur_w * protein_low)
    else:
        protein_g = round(cur_w * 1.8)

    fat_low, fat_high = FAT_G_PER_KG
    fat_g = round(cur_w * (fat_high if direction == "bulk" else fat_low))
    remaining = kcal - protein_g * 4 - fat_g * 9
    carbs_g = max(50, round(remaining / 4))

    return {
        "ok": True,
        "direction": direction,
        "kcal": kcal,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "per_kg": {
            "protein": round(protein_g / cur_w, 1),
            "carbs": round(carbs_g / cur_w, 1),
            "fat": round(fat_g / cur_w, 1),
        },
        "water_ml": int(round(cur_w * 35 / 100) * 100),
        "note": f"起点热量 {kcal} kcal/天, 缺口或盈余约 {abs(kcal - bmr):.0f} kcal; 2 周后按体重趋势校准",
    }


# ═══════════════════════════════════════════════════════════
# 五、预算 → 每日饮食计划
# ═══════════════════════════════════════════════════════════


# 餐次内每种食材承担的宏量角色与实际份量档位 (克 / 个 / 毫升)
FOOD_PORTIONS: Dict[str, Dict[str, Any]] = {
    "鸡蛋": {
        "role": "protein",
        "grams": 50,
        "unit": "个",
        "count": 2,
        "kcal": 72,
        "protein": 6,
        "carbs": 0.5,
        "fat": 5,
    },
    "鸡胸肉": {
        "role": "protein",
        "grams": 100,
        "unit": "g",
        "count": 1,
        "kcal": 133,
        "protein": 24,
        "carbs": 0,
        "fat": 3,
    },
    "瘦牛肉": {
        "role": "protein",
        "grams": 100,
        "unit": "g",
        "count": 1,
        "kcal": 180,
        "protein": 26,
        "carbs": 0,
        "fat": 8,
    },
    "三文鱼/冷冻鱼柳": {
        "role": "protein",
        "grams": 100,
        "unit": "g",
        "count": 1,
        "kcal": 200,
        "protein": 22,
        "carbs": 0,
        "fat": 12,
    },
    "全脂牛奶": {
        "role": "protein",
        "grams": 250,
        "unit": "ml",
        "count": 1,
        "kcal": 158,
        "protein": 8,
        "carbs": 12,
        "fat": 8,
    },
    "无糖豆浆": {
        "role": "protein",
        "grams": 300,
        "unit": "ml",
        "count": 1,
        "kcal": 90,
        "protein": 9,
        "carbs": 6,
        "fat": 3,
    },
    "豆制品(豆腐/豆干)": {
        "role": "protein",
        "grams": 150,
        "unit": "g",
        "count": 1,
        "kcal": 120,
        "protein": 12,
        "carbs": 5,
        "fat": 6,
    },
    "大米/糙米(生)": {
        "role": "carb",
        "grams": 80,
        "unit": "g",
        "count": 1,
        "kcal": 280,
        "protein": 6,
        "carbs": 62,
        "fat": 1,
    },
    "燕麦片(干)": {
        "role": "carb",
        "grams": 50,
        "unit": "g",
        "count": 1,
        "kcal": 190,
        "protein": 6,
        "carbs": 33,
        "fat": 3,
    },
    "红薯": {"role": "carb", "grams": 200, "unit": "g", "count": 1, "kcal": 180, "protein": 3, "carbs": 40, "fat": 0.5},
    "全麦面包": {
        "role": "carb",
        "grams": 70,
        "unit": "片",
        "count": 2,
        "kcal": 170,
        "protein": 6,
        "carbs": 30,
        "fat": 2,
    },
    "香蕉": {
        "role": "carb",
        "grams": 120,
        "unit": "根",
        "count": 1,
        "kcal": 105,
        "protein": 1,
        "carbs": 27,
        "fat": 0.4,
    },
    "混合蔬菜/西兰花": {
        "role": "veg",
        "grams": 200,
        "unit": "g",
        "count": 1,
        "kcal": 60,
        "protein": 5,
        "carbs": 8,
        "fat": 1,
    },
    "花生/坚果": {"role": "fat", "grams": 15, "unit": "g", "count": 1, "kcal": 90, "protein": 4, "carbs": 3, "fat": 8},
    "橄榄油/食用油": {
        "role": "fat",
        "grams": 10,
        "unit": "g",
        "count": 1,
        "kcal": 90,
        "protein": 0,
        "carbs": 0,
        "fat": 10,
    },
    "乳清蛋白粉": {
        "role": "protein",
        "grams": 30,
        "unit": "g",
        "count": 1,
        "kcal": 120,
        "protein": 24,
        "carbs": 3,
        "fat": 1,
    },
}


# 单价按「个/根/片」计的可数食材 (不按 100g 折算)
COUNTABLE_FOODS = ("鸡蛋", "香蕉", "全麦面包")


def _portion_cost(kind: str, grams: float, count: int = 1) -> float:
    """按食材单价折算该份量的成本 (元)。"""
    price = BUDGET_UNIT_PRICES.get(kind)
    if price is None:
        return 0.0
    if kind in COUNTABLE_FOODS:
        return round(price * max(1, count), 1)
    return round(grams / 100.0 * price, 1)


def scale_meals(energy: Dict[str, Any], monthly_budget: float) -> Dict[str, Any]:
    """把每日宏量按模板分配到餐次, 并给出每餐的食材份量与成本。

    份量按固定档位 (FOOD_PORTIONS) 给, 便于直接采购; 数字是起点, 按腰围与训练表现微调。
    不做「按价格反推克数」这类拍脑袋换算 —— 份量必须先能对上宏量目标再谈成本。
    """
    if not energy.get("ok"):
        return {"ok": False, "errors": energy.get("errors", ["热量估算失败"])}

    calories = energy["kcal"]
    daily_budget = round(monthly_budget / 30.0, 1)
    meals: List[Dict[str, Any]] = []
    total_cost = 0.0
    for name, share, kinds in MEAL_TEMPLATE:
        kcal = round(calories * share)
        items = []
        for kind in kinds:
            spec = FOOD_PORTIONS.get(kind)
            if spec is None:
                continue
            count = spec["count"]
            grams = spec["grams"]
            # 可数食材 (个/根/片) 按「数量」写, 其余按克/毫升写, 避免出现「香蕉 120 根」这类读不通的标签
            label = (
                f"{kind} {count} {spec['unit']}"
                if spec["unit"] in ("个", "根", "片")
                else f"{kind} {grams}{spec['unit']}"
            )
            cost = _portion_cost(kind, grams, count)
            items.append(
                {
                    "food": label,
                    "grams": grams,
                    "kcal": spec["kcal"] * count,
                    "protein": spec["protein"] * count,
                    "cost": cost,
                }
            )
            total_cost += cost
        meals.append({"name": name, "kcal": kcal, "share": share, "items": items})

    return {
        "ok": True,
        "meals": meals,
        "daily_budget": daily_budget,
        "estimated_cost": round(total_cost, 1),
        "note": (
            f"按 {energy['kcal']} kcal 分配到六餐 (比例 "
            + "/".join(f"{int(s * 100)}" for _, s, _ in MEAL_TEMPLATE)
            + "); 份量是起点, 按饱腹感与体重趋势上下调 10–15%"
        ),
    }


def budget_plan(monthly_budget: float, energy: Dict[str, Any]) -> Dict[str, Any]:
    """把预算折成每日预算、补剂额度与采购清单; 不够就先保蛋白。

    分配口径: 补剂占比不超过 15% 且每日不超过 25 元 —— 先把钱花在肉蛋奶豆上。
    """
    monthly = float(monthly_budget or 0)
    daily = monthly / 30.0
    supplement_cap = min(daily * 0.15, 25.0)
    food_daily = max(0.0, daily - supplement_cap)

    daily_grams = {
        "protein": energy.get("protein_g", 0),
        "carbs": energy.get("carbs_g", 0),
        "fat": energy.get("fat_g", 0),
    }
    # 蛋白缺口 = 目标蛋白 - 按每天 2 个鸡蛋 + 300g 主食 + 500g 菜 + 250ml 奶的粗略供给
    staple_protein = 2 * 6 + 300 * 0.03 + 250 * 0.03
    protein_gap = max(0, int(daily_grams["protein"] - staple_protein))

    priorities = [
        "先保证蛋白总量: 鸡蛋 + 鸡胸肉/豆腐 + 奶/豆浆, 这是最影响训练恢复的一笔钱",
        "主食选米/面/红薯这类单价低的, 碳水不用买贵",
        "蔬菜按 500g/天 以上买当季的, 冷冻混合蔬菜更便宜",
        "水果挑香蕉这类便宜的, 不必买贵的进口水果",
    ]
    if food_daily < 25:
        priorities.append("预算偏紧: 减少外食与半成品, 用整袋米面 + 冷冻肉替代已切配产品")
    if food_daily < 15:
        priorities.append("预算很紧: 蛋白优先靠鸡蛋 + 豆制品 + 乳清蛋白粉补齐, 先保住蛋白再做菜式变化")

    return {
        "ok": True,
        "monthly_budget": round(monthly, 1),
        "daily_budget": round(daily, 1),
        "food_daily_budget": round(food_daily, 1),
        "supplement_daily_cap": round(supplement_cap, 1),
        "protein_gap_g": protein_gap,
        "protein_fill": (
            f"目标蛋白 {daily_grams['protein']}g, 基础食材约能提供 {staple_protein:.0f}g, "
            f"余下约 {protein_gap}g 由鸡胸肉/豆腐/蛋白粉补齐"
        ),
        "priorities": priorities,
        "note": "补剂最多占预算 15% 且不超过 25 元/天; 钱先花在真食物上",
    }


def generate_diet_plan(
    monthly_budget: Any,
    current_weight: float,
    current_bodyfat: Optional[float] = None,
    target_weight: Optional[float] = None,
    sex: str = "male",
    nutrition_parser: Optional[Any] = None,
) -> Dict[str, Any]:
    """由月度预算 + 体测输入生成每日饮食计划与补剂方案 (含不伤身体的红线)。"""
    check = validate_budget(monthly_budget)
    if not check["ok"]:
        return {"ok": False, "errors": check["errors"]}

    energy = plan_energy(current_weight, current_bodyfat, target_weight, sex)
    if not energy.get("ok"):
        return {"ok": False, "errors": energy["errors"]}

    monthly = check["monthly_budget"]
    meals = scale_meals(energy, monthly)
    budget = budget_plan(monthly, energy)
    supplements = suggest_supplements(budget["supplement_daily_cap"], energy)

    return {
        "ok": True,
        "energy": energy,
        "meals": meals,
        "budget": budget,
        "supplements": supplements,
        "cautions": _diet_cautions(energy, monthly),
        "reference": _reference_meals(nutrition_parser),
    }


def suggest_supplements(daily_cap: float, energy: Dict[str, Any]) -> Dict[str, Any]:
    """在每日补剂额度内排一个「先核心、后可选」的清单, 只给常用安全品类。"""
    cap = max(0.0, float(daily_cap or 0))
    picked: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    spent = 0.0

    for item in SUPPLEMENT_CATALOG:
        cost = _supplement_daily_cost(item)
        entry = {
            "name": item["name"],
            "dose": item.get("dose_text") or f"{item['dose_g']:g} g",
            "timing": item["timing"],
            "purpose": item["purpose"],
            "daily_cost": round(cost, 2),
            "note": item["upper_note"],
            "tier": item["tier"],
        }
        is_core = item["tier"] == "core"
        # core 至少保一个 (头一个 core 不看额度): 蛋白不够时蛋白粉优先级最高
        if (is_core and spent + cost <= cap) or (is_core and not any(p["tier"] == "core" for p in picked)):
            picked.append(entry)
            spent += cost
        elif not is_core and spent + cost <= cap:
            picked.append(entry)
            spent += cost
        else:
            entry["reason"] = (
                "当前额度不够, 先用食物补齐这类营养" if item["tier"] == "food_first" else "预算有余量时再加"
            )
            skipped.append(entry)

    protein_target = energy.get("protein_g", 0)
    return {
        "daily_cap": round(cap, 1),
        "daily_cost": round(spent, 2),
        "picked": picked,
        "skipped": skipped,
        "red_lines": list(SUPPLEMENT_RED_LINES),
        "protein_fill": (
            f"目标蛋白 {protein_target}g: 先靠鸡蛋/肉/奶/豆拿到 {max(0, protein_target - 30)}g, "
            "剩下的一餐用 30g 乳清蛋白补齐即可, 不要靠蛋白粉顶掉正餐"
        ),
        "medical_note": (
            "补剂只用于补齐饮食缺口, 不替代正餐也不治病。有肝肾疾病、心血管疾病、"
            "正在服药、孕期或哺乳期, 加任何补剂前先问医生; 体检异常指标先就医再谈补剂。"
        ),
    }


def _supplement_daily_cost(item: Dict[str, Any]) -> float:
    """按剂量与单价折算每日成本 (元)。"""
    if item.get("dose_g"):
        return float(item["unit_cost"]) * float(item["dose_g"])
    return float(item["unit_cost"])


def _diet_cautions(energy: Dict[str, Any], monthly_budget: float) -> List[str]:
    cautions = [
        f"饮水 {energy['water_ml']} ml/天, 训练中每 15 分钟补 200ml",
        "盐摄入控制在 <5g/天, 控盐日 <3g; 加工肉制品与酱料少碰",
        "每周固定同一天、同一时间、同一状态称重, 只看 2–4 周趋势不看单日波动",
    ]
    if energy.get("direction") == "cut":
        cautions.append("减脂期热量不低于估算基础值的 85%, 出现持续乏力/怕冷/睡眠变差就先回到维持热量")
    if monthly_budget / 30.0 < 20:
        cautions.append("预算紧张时优先砍零食与外食, 不砍蛋白与蔬菜")
    cautions.append("有糖尿病、肾病、痛风、进食障碍史: 饮食方案必须由医生或注册营养师复核")
    return cautions


def _reference_meals(nutrition_parser: Optional[Any]) -> Dict[str, Any]:
    """本地已有营养方案时的对照参考 (不存在就返回空, 不阻断生成)。"""
    parser_cls = nutrition_parser or NutritionParser
    try:
        meals = parser_cls.get_meals()
        totals = parser_cls.get_daily_totals(meals)
    except Exception:
        return {"available": False, "meals": [], "totals": {}, "note": "未取到本地营养方案, 仅用本次生成的方案"}
    return {
        "available": True,
        "meals": meals,
        "totals": totals,
        "note": "本地 22 周计划自带的五餐基准, 可用来对照本次生成方案的餐次结构",
    }


def generate_diet_markdown(diet: Dict[str, Any]) -> str:
    """把饮食与补剂方案渲染成 Markdown。"""
    if not diet.get("ok"):
        return "\n".join(f"- ⚠ {e}" for e in diet.get("errors", ["输入无效"]))
    energy, budget, supp = diet["energy"], diet["budget"], diet["supplements"]
    lines = [
        "### 每日饮食计划",
        "",
        f"- 热量: **{energy['kcal']} kcal/天** ({energy['direction']}) · "
        f"蛋白 {energy['protein_g']}g / 碳水 {energy['carbs_g']}g / 脂肪 {energy['fat_g']}g",
        f"- 每公斤体重: 蛋白 {energy['per_kg']['protein']}g · 碳水 {energy['per_kg']['carbs']}g · 脂肪 {energy['per_kg']['fat']}g",
        f"- 饮水: {energy['water_ml']} ml/天",
        f"- 预算: {budget['monthly_budget']} 元/月 ≈ {budget['daily_budget']} 元/天 "
        f"(补剂上限 {budget['supplement_daily_cap']} 元/天)",
        f"- 蛋白补齐: {budget['protein_fill']}",
        "",
        f"**{energy['note']}**",
        "",
        "| 餐次 | 热量 | 采购参考 |",
        "|:--|--:|:--|",
    ]
    for meal in diet["meals"]["meals"]:
        food = " + ".join(i["food"] for i in meal["items"])
        lines.append(f"| {meal['name']} | {meal['kcal']} kcal | {food} |")
    lines.extend(["", "**采购优先级**", ""])
    lines.extend(f"- {p}" for p in budget["priorities"])
    lines.extend(["", "### 补剂方案 (不伤身体优先)", ""])
    if supp["picked"]:
        lines.append("| 补剂 | 剂量 | 时间 | 作用 | 元/天 |")
        lines.append("|:--|:--|:--|:--|--:|")
        for item in supp["picked"]:
            lines.append(
                f"| {item['name']} | {item['dose']} | {item['timing']} | {item['purpose']} | {item['daily_cost']} |"
            )
    else:
        lines.append("- 当前额度只够保基础: 先用食物补齐蛋白, 有余量再加补剂")
    lines.append("")
    for item in supp["picked"]:
        lines.append(f"- **{item['name']}**: {item['note']}")
    if supp["skipped"]:
        lines.append("")
        lines.append("暂不安排: " + "; ".join(f"{i['name']} ({i['reason']})" for i in supp["skipped"]))
    lines.extend(["", "**红线**", ""])
    lines.extend(f"- {r}" for r in supp["red_lines"])
    lines.extend(["", f"> {supp['medical_note']}", "", "**饮食纪律**", ""])
    lines.extend(f"- {c}" for c in diet["cautions"])
    return "\n".join(lines)
