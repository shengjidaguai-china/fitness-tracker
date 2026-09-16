"""
训练计划 / 营养方案解析器 (v7.0 模块化拆分)
TrainingPlanParser: 解析 居家平替计划_v3.0_*.md 的每日动作表 + 补位体系
NutritionParser: 解析三阶段营养方案常量
"""

import os
from typing import Dict, List, Optional, Tuple

from .constants import PLAN_MD, TRAINING_SCHEDULE


class TrainingPlanParser:
    """从居家平替计划 v3.0 解析训练动作, 支持22周三阶段周期化"""

    DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def __init__(self):
        self.raw_text = ""
        self._phase_exercises = {}  # {phase_num: {day: [exercises]}}
        self._phase_notes = {}  # {phase_num: ['note1', ...]}
        self._load()
        self._parse_all()

    def _load(self):
        if os.path.exists(PLAN_MD):
            with open(PLAN_MD, encoding="utf-8") as f:
                self.raw_text = f.read()

    @classmethod
    def get_phase(cls, week: int) -> int:
        return 1 if week <= 6 else (2 if week <= 14 else 3)

    def get_daily_exercises(self, week: int = 1) -> Dict[str, List[Dict]]:
        phase = self.get_phase(week)
        if self._phase_exercises.get(phase):
            return self._phase_exercises[phase]
        # Phase 2/3 复用 Phase 1 动作(仅有调整说明, 无独立表格)
        result = self._phase_exercises.get(1, {})
        if not result:
            return {d["day"]: [] for d in TRAINING_SCHEDULE}
        return result

    def get_phase_notes(self, week: int = 1) -> List[str]:
        phase = self.get_phase(week)
        return self._phase_notes.get(phase, [])

    # ──────────────── 解析引擎 ────────────────

    def _parse_all(self):
        """v2.1 格式: ## 五、Phase 1 训练明细 — ### 周X 日标题 + 3列表格(动作|组×次|要点)"""
        if not self.raw_text:
            return

        lines = self.raw_text.split("\n")
        in_section = 0  # 0=跳过, 5=Chapter5训练, 6=Chapter6概要
        current_day = None
        parsed = {}
        table_header = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # ── 章节边界 ──
            if stripped.startswith("## 五、"):
                in_section = 5
                continue
            if in_section == 5 and stripped.startswith("## 六、"):
                # 保存 Phase 1
                if parsed:
                    self._phase_exercises[1] = dict(parsed)
                in_section = 6
                continue
            if in_section == 6 and stripped.startswith("## 七、"):
                break
            if in_section == 0:
                continue

            # ── Chapter 6: Phase 2/3 概要收集 (v2.1: 粗体格式 **Phase N**) ──
            if in_section == 6:
                if stripped.startswith("**Phase 2") or stripped.startswith("### Phase 2"):
                    self._collect_phase_notes(2, lines, i)
                elif stripped.startswith("**Phase 3") or stripped.startswith("### Phase 3"):
                    self._collect_phase_notes(3, lines, i)
                continue

            # ── Chapter 5: 日期检测 (### 周一 · ... ) ──
            day_found = False
            for dn in self.DAY_NAMES:
                if stripped.startswith(f"### {dn}") and ("·" in stripped or "★" in stripped or "—" in stripped):
                    current_day = dn
                    table_header = []
                    day_found = True
                    break
            if day_found:
                continue
            # 非日期的 ### 行重置
            if stripped.startswith("###"):
                current_day = None
                table_header = []
                continue

            if current_day is None or current_day == "周日":
                continue

            # ── 表格行解析 (3列: 动作 | 组×次 | 要点) ──
            if not stripped.startswith("|") or "---" in stripped:
                if not stripped.startswith("|") and table_header:
                    table_header = []
                continue

            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not cells:
                continue

            first_cell = cells[0]

            # 表头行: v2.1 第一列是 "动作"
            if first_cell == "动作":
                table_header = cells
                continue
            if not table_header:
                continue

            # ── 分格式解析 ──
            parsed.setdefault(current_day, [])

            if first_cell == "收尾":
                ex_name = cells[1] if len(cells) > 1 else ""
                ex_tip = cells[2] if len(cells) > 2 else ""
                if "真空腹" in ex_name:
                    if "+" in ex_name:
                        # 拆分: 非真空腹动作 + 真空腹流程块
                        non_vac = [
                            p.strip().replace("**", "") for p in ex_name.split("+") if p.strip() and "真空腹" not in p
                        ]
                        if non_vac:
                            parsed[current_day].append(
                                {
                                    "name": non_vac[0],
                                    "sets": "",
                                    "target": "收尾",
                                    "tip": ex_tip,
                                    "media_id": "",
                                }
                            )
                        vac_sets = " ".join(p.strip() for p in ex_name.split("+") if "真空腹" in p)
                        parsed[current_day].append(
                            {
                                "name": vac_sets if vac_sets else "真空腹",
                                "sets": "",
                                "target": "窄腰",
                                "tip": "",
                                "media_id": "",
                                "is_workout_block": True,
                                "block_type": "flow",
                                "duration": "",
                                "sub_info": "腹横肌收缩训练, 缩小腰围最有效的非有氧手段",
                            }
                        )
                    else:
                        parsed[current_day].append(
                            {
                                "name": ex_name,
                                "sets": "",
                                "target": "窄腰",
                                "tip": ex_tip,
                                "media_id": "",
                                "is_workout_block": True,
                                "block_type": "flow",
                                "duration": "",
                                "sub_info": "腹横肌收缩训练, 缩小腰围最有效的非有氧手段",
                            }
                        )
                else:
                    parsed[current_day].append(
                        {
                            "name": ex_name,
                            "sets": cells[1] if len(cells) > 1 else "",
                            "target": "收尾",
                            "tip": ex_tip,
                            "media_id": "",
                        }
                    )
            elif first_cell == "热身":
                parsed[current_day].append(
                    {
                        "name": cells[1] if len(cells) > 1 else "动态热身",
                        "sets": "热身",
                        "target": "",
                        "tip": cells[2] if len(cells) > 2 else "",
                        "media_id": "",
                        "is_workout_block": True,
                        "block_type": "flow",
                        "duration": "5-8分钟",
                        "sub_info": "关节绕环+空杆激活",
                    }
                )
            elif first_cell.startswith("循环"):
                parsed[current_day].append(
                    {
                        "name": cells[1] if len(cells) > 1 else "HIIT循环",
                        "sets": "4循环",
                        "target": "HIIT",
                        "tip": cells[2] if len(cells) > 2 else "",
                        "media_id": "",
                        "is_workout_block": True,
                        "block_type": "hiit_loop",
                        "duration": cells[2] if len(cells) > 2 else "约15分钟",
                        "sub_info": "6动作 x 40秒训练 / 20秒休息",
                    }
                )
            elif first_cell == "拉伸":
                parsed[current_day].append(
                    {
                        "name": "全身拉伸",
                        "sets": cells[1] if len(cells) > 1 else "10分钟",
                        "target": "拉伸",
                        "tip": cells[2] if len(cells) > 2 else "",
                        "media_id": "",
                        "is_workout_block": True,
                        "block_type": "flow",
                        "duration": cells[1] if len(cells) > 1 else "10分钟",
                        "sub_info": "静态拉伸·肌筋膜放松",
                    }
                )
            elif first_cell == "快走/椭圆机":
                parsed[current_day].append(
                    {
                        "name": "快走/椭圆机 (LISS)",
                        "sets": cells[1] if len(cells) > 1 else "",
                        "target": "LISS有氧 心率120-135",
                        "tip": cells[2] if len(cells) > 2 else "",
                        "media_id": "",
                        "is_workout_block": True,
                        "block_type": "liss_cardio",
                        "duration": cells[1] if len(cells) > 1 else "35分钟",
                        "sub_info": "心率120-135 bpm · 燃脂神经恢复",
                    }
                )
            else:
                # 普通动作行: | 动作名 | 组×次 | 要点 |
                ex_name = first_cell
                if "真空腹" in ex_name:
                    parsed[current_day].append(
                        {
                            "name": ex_name,
                            "sets": cells[1] if len(cells) > 1 else "",
                            "target": "窄腰",
                            "tip": cells[2] if len(cells) > 2 else "",
                            "media_id": "",
                            "is_workout_block": True,
                            "block_type": "flow",
                            "duration": cells[1] if len(cells) > 1 else "",
                            "sub_info": "腹横肌收缩训练, 缩小腰围最有效的非有氧手段",
                        }
                    )
                else:
                    parsed[current_day].append(
                        {
                            "name": ex_name,
                            "sets": cells[1] if len(cells) > 1 else "",
                            "target": "",
                            "tip": cells[2] if len(cells) > 2 else "",
                            "media_id": "",
                        }
                    )

        # 如果没有通过 Chapter 5→6 边界保存, 兜底保存 Phase 1
        if parsed and 1 not in self._phase_exercises:
            self._phase_exercises[1] = dict(parsed)

    @staticmethod
    def _detect_phase(stripped: str) -> int:
        # v2.1: Phase 1 明细直接在 ## 五、 下, 无需 ### 子标题检测, 此方法保留兼容
        if stripped.startswith("### 3.1"):
            return 1
        if stripped.startswith("### 3.2"):
            return 2
        if stripped.startswith("### 3.3"):
            return 3
        return 0

    def _collect_phase_notes(self, phase: int, lines: List[str], start_idx: int):
        """从 Phase 2/3 概要(## 六、)标题后收集调整说明, 直到下一个 Phase 标题 或 ## 章节"""
        notes = []
        for j in range(start_idx + 1, len(lines)):
            s = lines[j].strip()
            if not s:
                continue
            # 停止条件: 下一个 Phase 粗体/标题 或 ## 章节
            if s.startswith("**Phase") or s.startswith("### Phase") or s.startswith("## "):
                break
            if s.startswith("- ") or s.startswith("**") or any(s.startswith(f"{n}. **") for n in range(1, 10)):
                notes.append(s)
        if notes:
            self._phase_notes[phase] = notes

    # ──────────────── 补位体系 (v3.0 第九章/第十章) ────────────────
    def get_supplement_systems(self) -> Dict[str, Dict]:
        """解析居家平替计划 v3.0 第九章(海豹徒手) + 第十章(囚徒健身) 两大补位体系。

        返回:
            {
              'seal':   {'title', 'position', 'moves':[{'name','target','tip'}], 'test_loop':'', 'embed':[...]},
              'cc':     {'title', 'position', 'arts':[{'art','s1','s5','s10','day'}], 'embed':[...]},
            }
        若文档不存在或缺少相关章节, 返回空结构(调用方需做 fail-open 降级)。
        """
        seal = {"title": "", "position": "", "moves": [], "test_loop": "", "embed": []}
        cc = {"title": "", "position": "", "arts": [], "embed": []}
        if not self.raw_text:
            return {"seal": seal, "cc": cc}

        lines = self.raw_text.split("\n")
        cur_section = 0  # 0=无 / 9=海豹 / 10=囚徒
        table_header = []

        for line in lines:
            s = line.strip()
            if s.startswith("## 九"):
                cur_section = 9
                continue
            if s.startswith("## 十"):
                cur_section = 10
                continue
            if s.startswith("## 十一"):
                cur_section = 0
                break
            if cur_section == 0:
                continue

            # 定位/哲学/嵌入段落
            if cur_section == 9:
                if s.startswith("> **定位**"):
                    seal["position"] = s.lstrip("> ").replace("**定位**", "").strip().lstrip(":：").strip()
                elif s.startswith("> **训练哲学**"):
                    pass
                elif s.startswith("### 9.2"):
                    # 标准 SEAL 500 循环说明
                    pass
                elif "累计" in s and "轮" in s:
                    seal["test_loop"] = s.strip("`").strip()
            elif cur_section == 10:
                if s.startswith("> **定位**"):
                    cc["position"] = s.lstrip("> ").replace("**定位**", "").strip().lstrip(":：").strip()

            # 表格解析
            if s.startswith("|") and "---" not in s:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if not cells:
                    continue
                # 表头识别
                if cur_section == 9 and cells[0] == "动作":
                    table_header = cells
                    continue
                if cur_section == 10 and cells[0] == "艺":
                    table_header = cells
                    continue
                if not table_header:
                    continue
                if cur_section == 9:
                    # 六支柱表: 动作 | 目标 | 标准要点
                    if len(cells) >= 3:
                        seal["moves"].append(
                            {
                                "name": cells[0],
                                "target": cells[1],
                                "tip": cells[2],
                            }
                        )
                elif cur_section == 10:
                    # 六艺十阶表: 艺 | 阶1 | 阶5 | 阶10 | 主计划对应日
                    if len(cells) >= 5:
                        cc["arts"].append(
                            {
                                "art": cells[0],
                                "s1": cells[1],
                                "s5": cells[2],
                                "s10": cells[3],
                                "day": cells[4],
                            }
                        )
            # 嵌入示例(项目符号列表)
            if s.startswith("- "):
                if cur_section == 9 and ("应急" in s or "晨间" in s or "收尾" in s or "替代" in s):
                    seal["embed"].append(s.lstrip("- ").strip())
                elif cur_section == 10 and ("重量到顶" in s or "背厚度" in s or "桥" in s or "倒立" in s):
                    cc["embed"].append(s.lstrip("- ").strip())

        return {"seal": seal, "cc": cc}


# ═══════════════════════════════════════════════════════════
# 营养方案 — 解析12月底塑形冲刺计划第二章
# ═══════════════════════════════════════════════════════════


class NutritionParser:
    """从居家平替计划 v3.0 提取三阶段营养方案 + 补剂 + 饮水"""

    # 三阶段热量与宏量数据(v3.0居家平替版, 蛋白165g/天恒定)
    PHASE_MACROS = {
        1: {  # 基础建设期 (v3.0: 2300/2100, 蛋白165g)
            "training": {"kcal": 2300, "protein": 165, "carbs": 240, "fat": 60, "protein_pct": 29},
            "rest": {"kcal": 2100, "protein": 160, "carbs": 190, "fat": 58, "protein_pct": 30},
        },
        2: {  # 体成分重组期 (v3.0: 2200/2000, 蛋白165g)
            "training": {"kcal": 2200, "protein": 165, "carbs": 240, "fat": 55, "protein_pct": 30},
            "rest": {"kcal": 2000, "protein": 160, "carbs": 190, "fat": 55, "protein_pct": 32},
        },
        3: {  # 线条雕刻期 (碳水循环: 高碳280g, 中碳200g, 低碳150g, 休息130g)
            "training": {"kcal": 2200, "protein": 165, "carbs": 200, "fat": 55, "protein_pct": 30},  # 中碳日 fallback
            "high_carb": {"kcal": 2500, "protein": 165, "carbs": 280, "fat": 60, "protein_pct": 26},
            "medium": {"kcal": 2200, "protein": 165, "carbs": 200, "fat": 55, "protein_pct": 30},
            "low_carb": {"kcal": 1900, "protein": 160, "carbs": 150, "fat": 50, "protein_pct": 34},
            "rest": {"kcal": 1900, "protein": 160, "carbs": 130, "fat": 50, "protein_pct": 34},
        },
    }

    # 每日五餐 (v2.0 Phase 1 训练日基准 2050kcal, 蛋白目标165g)
    DAILY_MEALS = [
        {
            "name": "早餐 (07:00)",
            "kcal": 450,
            "protein": 38,
            "carbs": 43,
            "fat": 22,
            "items": [
                ("全蛋", "3个", "18g蛋白, 15g脂肪"),
                ("蛋白", "3个", "10g蛋白"),
                ("燕麦片(干)", "40g", "24g碳水, 5g蛋白"),
                ("蓝莓", "80g", "10g碳水"),
                ("全脂牛奶", "150ml", "8g碳水, 5g蛋白"),
            ],
        },
        {
            "name": "加餐 (10:00)",
            "kcal": 280,
            "protein": 28,
            "carbs": 25,
            "fat": 7,
            "items": [
                ("鸡胸肉", "100g", "24g蛋白"),
                ("红薯", "120g", "24g碳水, 2g蛋白"),
                ("核桃", "10g", "6g脂肪, 2g蛋白"),
            ],
        },
        {
            "name": "午餐 (12:30)",
            "kcal": 520,
            "protein": 40,
            "carbs": 48,
            "fat": 14,
            "items": [
                ("糙米饭(熟)", "120g", "40g碳水, 4g蛋白"),
                ("牛肉(瘦)", "120g", "30g蛋白, 6g脂肪"),
                ("西兰花", "200g", "8g碳水, 6g蛋白"),
                ("橄榄油", "6g", "6g脂肪"),
            ],
        },
        {
            "name": "训练前加餐 (16:30)",
            "kcal": 250,
            "protein": 12,
            "carbs": 33,
            "fat": 4,
            "items": [
                ("全麦面包", "2片", "30g碳水, 6g蛋白"),
                ("无糖豆浆", "200ml", "3g碳水, 6g蛋白"),
            ],
        },
        {
            "name": "训练后 (19:00)",
            "kcal": 310,
            "protein": 27,
            "carbs": 29,
            "fat": 1,
            "items": [
                ("酵母蛋白粉", "35g", "25g蛋白, 4g碳水"),
                ("香蕉", "1根", "25g碳水, 1g蛋白"),
                ("亮氨酸粉", "2-3g", "补偿酵母蛋白亮氨酸"),
            ],
        },
        {
            "name": "晚餐 (20:30)",
            "kcal": 290,
            "protein": 25,
            "carbs": 8,
            "fat": 9,
            "items": [
                ("三文鱼/鸡胸", "100g", "22g蛋白, 6g脂肪"),
                ("混合蔬菜", "200g", "8g碳水, 3g蛋白"),
                ("橄榄油", "3g", "3g脂肪"),
            ],
        },
    ]

    # 补剂方案 (v2.0宽背窄腰版, 新增乳清/CLA/电解质, 维D3提升)
    SUPPLEMENTS = [
        {"name": "酵母蛋白粉", "dose": "35g", "timing": "训练后30分钟内", "purpose": "蛋白质补充", "note": "维持"},
        {
            "name": "乳清蛋白粉",
            "dose": "30g",
            "timing": "训练前30分钟",
            "purpose": "弥补酵母蛋白亮氨酸不足",
            "note": "★新增,训练前补充",
        },
        {
            "name": "肌酸单水合物",
            "dose": "5g/天",
            "timing": "训练后随蛋白粉",
            "purpose": "力量+肌肉饱满度",
            "note": "维持",
        },
        {
            "name": "亮氨酸粉",
            "dose": "3-4g",
            "timing": "训练后(混蛋白粉)",
            "purpose": "MPS最大化",
            "note": "★v2.0从2-3g提升",
        },
        {"name": "鱼油", "dose": "3g", "timing": "随餐", "purpose": "抗炎+减脂辅助", "note": "维持"},
        {
            "name": "CLA共轭亚油酸",
            "dose": "3g",
            "timing": "随餐",
            "purpose": "减少腹部顽固脂肪",
            "note": "★新增,窄腰针对性",
        },
        {
            "name": "维生素D3",
            "dose": "4000IU",
            "timing": "早餐",
            "purpose": "睾酮支持+免疫",
            "note": "★v2.0提升到4000IU(冬季阳光少)",
        },
        {"name": "锌镁", "dose": "30mg+450mg", "timing": "睡前1h", "purpose": "睡眠+恢复", "note": "维持"},
        {
            "name": "电解质",
            "dose": "含钾钠镁",
            "timing": "高碳日训练中",
            "purpose": "防抽筋+维持水合",
            "note": "★新增,高碳日专用",
        },
    ]

    # 饮水与控盐 (v2.0窄腰版: 饮水提升, 盐摄入降低)
    HYDRATION = [
        ("总饮水量", "4.0-4.5L/天", "v2.0提升0.5L帮助代谢"),
        ("晨起", "500ml温水+柠檬", "代谢唤醒"),
        ("训练中", "800-1000ml", "每15分钟200ml"),
        ("肌酸补水", "额外+500ml/天", "肌酸需充足水合"),
        ("盐摄入", "<4g/天", "★v2.0从4-5g降至<4g,控皮下水分"),
        ("周日控盐日", "<3g/天", "★窄腰日严格控盐"),
        ("睡前2h", "限水", "避免夜起"),
        ("加工食品", "完全避免", "★香肠腊肉酱料一律不碰"),
    ]

    # Phase 3 高碳日说明 (v3.0: 高碳日280g碳水专为大肌群背/腿日)
    HIGH_CARB_INFO = (
        "高碳日安排(碳水280g): 背日(周一/周四) + 腿日(周三)\n"
        "中碳日(碳水200g): 胸/肩日(周二/周五) · "
        "低碳日(碳水150g): 泵感日(周六) · 休息日(周日): 130g\n"
        "蛋白恒定165g/天, 碳水循环驱动减脂+保肌"
    )

    @classmethod
    def get_phase(cls, week: int) -> int:
        return 1 if week <= 6 else (2 if week <= 14 else 3)

    @classmethod
    def get_macros(cls, week: int, day_type: str = "training") -> Dict:
        """day_type: 'training' | 'rest' | 'high_carb'"""
        phase = cls.get_phase(week)
        data = cls.PHASE_MACROS.get(phase, {}).get(day_type)
        if data is None:
            data = cls.PHASE_MACROS[phase]["training"]
        return dict(data)

    @classmethod
    def get_meals(cls) -> List[Dict]:
        return list(cls.DAILY_MEALS)

    @classmethod
    def get_supplements(cls) -> List[Dict]:
        return list(cls.SUPPLEMENTS)

    @classmethod
    def get_hydration(cls) -> List[Tuple]:
        return list(cls.HYDRATION)

    @classmethod
    def get_daily_totals(cls, meals: Optional[List[Dict]] = None) -> Dict:
        """汇总五餐合计(Phase 1 训练日基准: 169p/186c/57f/2100kcal)"""
        if meals is None:
            meals = cls.DAILY_MEALS
        return {
            "protein": sum(m["protein"] for m in meals),
            "carbs": sum(m["carbs"] for m in meals),
            "fat": sum(m["fat"] for m in meals),
            "kcal": sum(m["kcal"] for m in meals),
        }
