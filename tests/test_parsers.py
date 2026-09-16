"""解析器单元测试 — TrainingPlanParser / NutritionParser

含回归: in_table 死代码移除后补充体系解析行为不变(防回归)。
"""

from fitness_pkg.parsers import NutritionParser, TrainingPlanParser


class TestTrainingPlanPhase:
    def test_phase_boundaries(self):
        # 22 周三阶段: W1-6 → 1, W7-14 → 2, W15+ → 3
        assert TrainingPlanParser.get_phase(1) == 1
        assert TrainingPlanParser.get_phase(6) == 1
        assert TrainingPlanParser.get_phase(7) == 2
        assert TrainingPlanParser.get_phase(14) == 2
        assert TrainingPlanParser.get_phase(15) == 3
        assert TrainingPlanParser.get_phase(22) == 3

    def test_empty_plan_returns_empty_day_slots(self, tmp_path, monkeypatch):
        """训练计划 md 缺失时 fail-open: 返回周一~周日空表"""
        monkeypatch.setattr("fitness_pkg.parsers.PLAN_MD", str(tmp_path / "不存在.md"))
        p = TrainingPlanParser()
        plan = p.get_daily_exercises(week=1)
        assert set(plan.keys()) == {"周一", "周二", "周三", "周四", "周五", "周六", "周日"}
        assert all(v == [] for v in plan.values())

    def test_supplement_systems_parse(self, plan_md, monkeypatch):
        """回归: 第九章(海豹)/第十章(囚徒)表格解析"""
        monkeypatch.setattr("fitness_pkg.parsers.PLAN_MD", plan_md)
        p = TrainingPlanParser()
        sup = p.get_supplement_systems()

        assert sup["seal"]["position"] == "哑铃/杠铃缺失时的徒手补位动作库"
        moves = sup["seal"]["moves"]
        assert len(moves) == 2
        assert moves[0]["name"] == "折刀引体"
        assert moves[0]["target"] == "背"
        assert moves[1]["name"] == "单腿蹲"

        arts = sup["cc"]["arts"]
        assert len(arts) == 1
        assert arts[0]["art"] == "俯卧撑"
        assert arts[0]["s1"] == "墙撑"
        assert arts[0]["s5"] == "标准"
        assert arts[0]["s10"] == "神级"
        assert arts[0]["day"] == "周一/周四"

    def test_supplement_systems_missing_plan_is_fail_open(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fitness_pkg.parsers.PLAN_MD", str(tmp_path / "不存在.md"))
        p = TrainingPlanParser()
        sup = p.get_supplement_systems()
        assert sup["seal"]["moves"] == []
        assert sup["cc"]["arts"] == []


class TestNutrition:
    def test_phase_boundaries_match_training(self):
        for week in (1, 6, 7, 14, 15, 22):
            assert NutritionParser.get_phase(week) == TrainingPlanParser.get_phase(week)

    def test_get_macros_training_has_required_keys(self):
        for week in (1, 8, 16):
            macros = NutritionParser.get_macros(week, day_type="training")
            for key in ("蛋白质", "碳水", "脂肪", "热量", "蛋白", "kcal"):
                if key in macros:
                    assert macros[key] > 0

    def test_get_meals_returns_full_day(self):
        meals = NutritionParser.get_meals()
        assert len(meals) >= 5  # 早/午/晚/加餐等全餐结构
        for m in meals:
            assert set(m) >= {"name", "protein", "carbs", "fat", "kcal"}

    def test_get_daily_totals_sum_custom_meals(self):
        meals = [
            {"名称": "A", "protein": 30.0, "carbs": 40.0, "fat": 10.0, "kcal": 400},
            {"名称": "B", "protein": 20.0, "carbs": 30.0, "fat": 5.0, "kcal": 300},
        ]
        totals = NutritionParser.get_daily_totals(meals)
        assert totals == {"protein": 50.0, "carbs": 70.0, "fat": 15.0, "kcal": 700}

    def test_get_supplements_and_hydration(self):
        assert isinstance(NutritionParser.get_supplements(), list)
        hydration = NutritionParser.get_hydration()
        assert hydration, "饮水计划不应为空"
        for item in hydration:
            assert len(item) >= 2
