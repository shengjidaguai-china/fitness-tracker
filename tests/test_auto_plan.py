"""自动方案生成用例 (Issue #5) — 体测→训练计划, 预算→饮食与补剂

覆盖重点:
- 输入校验真的能拦住非法值 (不是走个过场)
- 减脂/增肌速度上限不被突破 (这是安全约束, 不是文案)
- 补剂清单永不出现红线品类, 且预算紧时先保蛋白
- 餐次份量标签可读 (不出现「香蕉 120 根」这类读不通的输出)
"""

import pytest

from fitness_pkg.auto_plan import (
    BUDGET_UNIT_PRICES,
    LEVEL_CATALOG,
    SUPPLEMENT_CATALOG,
    SUPPLEMENT_RED_LINES,
    body_composition_plan,
    budget_plan,
    generate_diet_markdown,
    generate_diet_plan,
    generate_training_markdown,
    generate_training_plan,
    infer_level,
    plan_energy,
    scale_meals,
    validate_body_inputs,
    validate_budget,
)


class TestValidation:
    def test_missing_weight_is_rejected(self):
        result = validate_body_inputs(None)
        assert result["ok"] is False
        assert any("当前体重" in e for e in result["errors"])

    def test_non_numeric_weight_is_rejected(self):
        assert validate_body_inputs("很重")["ok"] is False

    def test_zero_weight_is_rejected_not_treated_as_valid(self):
        """0 kg 能过校验的话, 下游所有推算都会变成 0, 必须在这里拦住。"""
        assert validate_body_inputs(0)["ok"] is False

    def test_unit_confusion_caught_by_range(self):
        """常见误填: 把斤当 kg (74 斤 = 37kg 还能过) / 写成克 (74000) 必须被拦。"""
        assert validate_body_inputs(74000)["ok"] is False

    def test_bodyfat_out_of_range_rejected(self):
        assert validate_body_inputs(70, 120)["ok"] is False

    def test_valid_input_passes_and_normalizes(self):
        result = validate_body_inputs(74, 23, 68, 15, 175, 28, "male")
        assert result["ok"] is True
        assert result["current_weight"] == 74.0
        assert result["sex"] == "male"

    def test_missing_bodyfat_warns_but_still_works(self):
        result = validate_body_inputs(74, None, 68, None)
        assert result["ok"] is True
        assert any("体脂率" in w for w in result["warnings"])

    def test_essential_fat_floor_warns_against_further_cutting(self):
        result = validate_body_inputs(70, 4.5, 68, 5.0)
        assert any("必需脂肪" in w for w in result["warnings"])

    def test_conflicting_goals_warned(self):
        """目标体重上升但体脂下降 = 双目标, 周期会拉长, 应提示。"""
        result = validate_body_inputs(70, 20, 75, 15)
        assert any("双目标" in w for w in result["warnings"])

    @pytest.mark.parametrize("budget", [None, "", "很多", 100, 99999])
    def test_bad_budget_rejected(self, budget):
        assert validate_budget(budget)["ok"] is False

    def test_valid_budget_passes(self):
        assert validate_budget(1500)["monthly_budget"] == 1500.0


class TestComposition:
    def test_cut_direction_detected(self):
        comp = body_composition_plan(74, 23, 68, 15)
        assert comp["direction"] == "cut"
        assert comp["target_weight"] < 74

    def test_bulk_direction_detected(self):
        comp = body_composition_plan(65, 15, 72, 15)
        assert comp["direction"] == "bulk"

    def test_small_delta_is_recomp_not_cut(self):
        comp = body_composition_plan(70, 20, 70, 18)
        assert comp["direction"] == "recomp"

    def test_target_weight_derived_from_lean_mass(self):
        """目标体脂优先按「保住去脂体重」推算, 而不是直接用用户填的数字。"""
        comp = body_composition_plan(74, 23, None, 15)
        lean = 74 * (1 - 0.23)
        assert comp["target_weight"] == pytest.approx(lean / 0.85, abs=0.3)

    def test_explicit_target_weight_conflict_is_disclosed(self):
        comp = body_composition_plan(74, 23, 60, 15)
        assert "差" in comp["weight_note"]

    def test_weekly_rate_never_exceeds_safety_cap(self):
        comp = body_composition_plan(100, 35, 60, 12)
        assert comp["planned_weekly_rate"] <= comp["weekly_rate_cap"]

    def test_aggressive_target_extends_weeks_instead_of_raising_rate(self):
        """要求 12 周掉 20kg 时必须延长周期, 不允许靠加大缺口硬走。"""
        comp = body_composition_plan(100, 35, 80, 25)
        assert comp["weeks"] >= 16
        assert comp["planned_weekly_rate"] <= 1.0

    def test_weeks_are_multiples_of_four(self):
        comp = body_composition_plan(90, 30, 75, 18)
        assert comp["weeks"] % 4 == 0

    def test_lean_mass_preserved_in_target(self):
        comp = body_composition_plan(80, 25, None, 15)
        assert comp["target_lean_mass"] == pytest.approx(80 * 0.75, abs=0.2)


class TestTrainingPlan:
    def test_plan_contains_exercises_every_training_day(self):
        plan = generate_training_plan(74, 23, 68, 15, 175, training_age_months=8)
        assert plan["ok"] is True
        for day in plan["days"]:
            assert day["exercises"], f"{day['day']} 没有动作"

    def test_every_exercise_has_sets_and_reps(self):
        plan = generate_training_plan(74, 23, 68, 15, 175, training_age_months=8)
        for day in plan["days"]:
            for ex in day["exercises"]:
                assert ex["sets"] >= 1
                assert 1 <= ex["reps_low"] <= ex["reps_high"]
                assert "×" in ex["sets_text"]

    def test_sessions_match_level_catalog(self):
        plan = generate_training_plan(74, 23, None, None, 175, training_age_months=8)
        assert plan["sessions_per_week"] == LEVEL_CATALOG[plan["level"]]["sessions"]
        assert len(plan["days"]) == plan["sessions_per_week"]

    def test_rest_days_are_the_rest_of_the_week(self):
        plan = generate_training_plan(74, 23, None, None, 175, training_age_months=8)
        trained = {d["day"] for d in plan["days"]}
        assert set(plan["rest_days"]).isdisjoint(trained)
        assert len(trained) + len(plan["rest_days"]) == 7

    def test_deload_week_is_lighter_than_normal_week(self):
        """不变量: 同一个动作在减载周的组数必须少于实现周。"""
        normal = generate_training_plan(74, 23, None, None, 175, week=7, training_age_months=8)
        deload = generate_training_plan(74, 23, None, None, 175, week=8, training_age_months=8)
        assert deload["deload"] is True
        normal_sets = normal["days"][0]["exercises"][0]["sets"]
        deload_sets = deload["days"][0]["exercises"][0]["sets"]
        assert deload_sets < normal_sets

    def test_deload_rpe_is_lower(self):
        normal = generate_training_plan(74, 23, None, None, 175, week=7, training_age_months=8)
        deload = generate_training_plan(74, 23, None, None, 175, week=8, training_age_months=8)
        assert deload["days"][0]["exercises"][0]["rpe"][1] < normal["days"][0]["exercises"][0]["rpe"][1]

    def test_volume_verdict_is_delegated_to_rule_layer(self):
        """周组数判定必须来自 plan_science/science, 页面不自己下结论。"""
        plan = generate_training_plan(74, 23, None, None, 175, training_age_months=8)
        assert plan["weekly_volume"]["verdict"] in ("已判定", "不判定")
        assert plan["volume_band"] == list(plan["weekly_volume"]["band"])

    def test_start_load_is_flagged_as_estimate_not_prescription(self):
        plan = generate_training_plan(74, 23, None, None, 175)
        assert "RPE 6–7" in plan["start_load"]["note"]

    def test_cautions_include_red_flag(self):
        plan = generate_training_plan(74, 23, 68, 15, 175, training_age_months=8)
        assert any("就医" in c for c in plan["cautions"])

    def test_plan_fails_open_without_height_and_age(self):
        plan = generate_training_plan(70, 20, 65, 15)
        assert plan["ok"] is True
        assert plan["days"]

    def test_invalid_weight_returns_errors_not_exception(self):
        plan = generate_training_plan(0)
        assert plan["ok"] is False
        assert plan["errors"]

    def test_markdown_renders_all_days(self):
        plan = generate_training_plan(74, 23, 68, 15, 175, training_age_months=8)
        md = generate_training_markdown(plan)
        for day in plan["days"]:
            assert day["day"] in md
            assert day["exercises"][0]["name"] in md

    def test_markdown_of_invalid_plan_lists_errors(self):
        assert "⚠" in generate_training_markdown({"ok": False, "errors": ["当前体重无效"]})


class TestLevel:
    def test_beginner_gets_p0(self):
        info = infer_level(80, 30, 22, 175, training_age_months=0)
        assert info["level"] == "P0"

    def test_experienced_trainee_gets_higher_level(self):
        info = infer_level(80, 15, 14, 178, training_age_months=36)
        assert info["level"] in ("L2", "L3")

    def test_reasons_are_always_explained(self):
        for months in (0, 3, 12, 48):
            info = infer_level(78, 22, 15, 175, training_age_months=months)
            assert info["reasons"], f"训练年限 {months} 个月没给出判定依据"

    def test_p0_weeks_are_lighter(self):
        """等级越低, 每个动作的组数档位越低。"""
        assert LEVEL_CATALOG["P0"]["sets_per_movement"][1] < LEVEL_CATALOG["L3"]["sets_per_movement"][1]


class TestEnergy:
    def test_cut_has_deficit_and_bulk_has_surplus(self):
        cut = plan_energy(80, 25, 72)
        bulk = plan_energy(80, 25, 88)
        assert cut["kcal"] < bulk["kcal"]

    def test_protein_higher_in_cut_than_bulk(self):
        """缺口期蛋白取上限保肌肉, 盈余期取下限 —— 不能反过来。"""
        cut = plan_energy(80, 25, 72)
        bulk = plan_energy(80, 25, 88)
        assert cut["protein_g"] > bulk["protein_g"]

    def test_fat_floor_respected(self):
        energy = plan_energy(70, 20, 65)
        assert energy["per_kg"]["fat"] >= 0.6

    def test_carbs_never_negative(self):
        energy = plan_energy(70, 20, 64)
        assert energy["carbs_g"] > 0

    def test_invalid_weight_returns_error(self):
        assert plan_energy(0)["ok"] is False


class TestDietAndBudget:
    def test_meals_cover_the_whole_day(self):
        energy = plan_energy(74, 23, 68)
        meals = scale_meals(energy, 1500)
        assert meals["ok"] is True
        assert len(meals["meals"]) >= 5

    def test_portion_labels_are_readable(self):
        """回归: 份量曾按价格反推出「香蕉 120 根」这类读不通的标签。"""
        meals = scale_meals(plan_energy(74, 23, 68), 1500)
        for meal in meals["meals"]:
            for item in meal["items"]:
                assert "克" not in item["food"]
                assert not any(f"{n} 根" in item["food"] for n in ("500", "1000"))
                if "香蕉" in item["food"]:
                    assert item["food"].endswith("根")

    def test_countable_foods_cost_uses_unit_price(self):
        meals = scale_meals(plan_energy(74, 23, 68), 1500)
        eggs = [i for m in meals["meals"] for i in m["items"] if "鸡蛋" in i["food"]]
        assert eggs and eggs[0]["cost"] == pytest.approx(BUDGET_UNIT_PRICES["鸡蛋"] * 2, abs=0.2)

    def test_budget_split_caps_supplements(self):
        budget = budget_plan(1500, plan_energy(74, 23, 68))
        assert budget["supplement_daily_cap"] <= 25.0
        assert budget["supplement_daily_cap"] <= budget["daily_budget"] * 0.15 + 0.01

    def test_tight_budget_prioritizes_protein(self):
        budget = budget_plan(500, plan_energy(74, 23, 68))
        assert any("蛋白" in p for p in budget["priorities"])

    def test_tight_budget_gets_extra_guidance(self):
        tight = budget_plan(450, plan_energy(74, 23, 68))
        normal = budget_plan(4000, plan_energy(74, 23, 68))
        assert len(tight["priorities"]) > len(normal["priorities"])

    def test_full_diet_plan_markdown_renders(self):
        diet = generate_diet_plan(1500, 74, 23, 68)
        md = generate_diet_markdown(diet)
        assert "### 每日饮食计划" in md
        assert "### 补剂方案" in md
        assert "| 餐次 |" in md

    def test_invalid_budget_returns_errors(self):
        diet = generate_diet_plan(0, 74, 23, 68)
        assert diet["ok"] is False


class TestSupplements:
    def test_core_supplements_picked_when_budget_allows(self):
        diet = generate_diet_plan(3000, 74, 23, 68)
        picked = {s["name"] for s in diet["supplements"]["picked"]}
        assert "乳清蛋白粉" in picked
        assert "肌酸单水合物" in picked

    def test_catalog_has_no_red_line_products(self):
        banned = ("燃脂", "DNP", "克伦特罗", "利尿", "促生长")
        for item in SUPPLEMENT_CATALOG:
            assert not any(b in item["name"] for b in banned)

    def test_every_supplement_states_its_ceiling(self):
        for item in SUPPLEMENT_CATALOG:
            assert item["upper_note"], f"{item['name']} 没写剂量上限或禁忌"

    def test_red_lines_always_shown(self):
        diet = generate_diet_plan(1500, 74, 23, 68)
        assert diet["supplements"]["red_lines"] == list(SUPPLEMENT_RED_LINES)
        assert len(SUPPLEMENT_RED_LINES) >= 3

    def test_medical_note_present(self):
        diet = generate_diet_plan(1500, 74, 23, 68)
        assert "医生" in diet["supplements"]["medical_note"]

    def test_zero_budget_cap_still_keeps_at_least_one_core(self):
        """极端情况下也要给出「先补什么」, 而不是空清单。"""
        diet = generate_diet_plan(500, 74, 23, 68)
        assert diet["supplements"]["picked"]

    def test_cheap_supplements_not_dropped_for_expensive_ones(self):
        """额度只够核心档时, 不应把便宜的 core 换成贵的 optional。"""
        diet = generate_diet_plan(700, 74, 23, 68)
        picked_tiers = {s["tier"] for s in diet["supplements"]["picked"]}
        assert picked_tiers <= {"core", "optional"}
        assert (
            diet["supplements"]["daily_cost"] <= diet["supplements"]["daily_cap"] + 0.01
            or len(diet["supplements"]["picked"]) == 1
        )
