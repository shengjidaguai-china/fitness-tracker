"""AI 教练引擎单元测试 — 等级评估/1RM估算/周期生成/训练复盘"""

import pytest

from ai_coach_engine import (
    AthleteProfile,
    ReviewResult,
    StrengthCycle,
    TrainingLog,
    assess_level,
    assess_overall_level,
    calc_target_weight,
    determine_cycle_length,
    distribute_phases,
    e1rm_from_set,
    estimate_1rm,
    generate_strength_cycle,
    review_training,
)


class TestEstimate:
    def test_one_rep_is_itself(self):
        assert estimate_1rm(100.0, 1) == pytest.approx(100.0)

    def test_epley_formula(self):
        # v9.1 口径: RPE 7 → 3 RIR, 先折算到力竭等效重量再套 Epley
        # e1RM = 100 / (1 + 3 × RIR_LOAD_STEP) × (1 + (5+3)/30) ≈ 117.83
        assert estimate_1rm(100.0, 5) == pytest.approx(e1rm_from_set(100.0, 5, 7.0))
        assert estimate_1rm(100.0, 5) == pytest.approx(117.83)

    def test_lower_rpe_higher_estimate(self):
        # v9.1: 同样 5 次, RPE 越低 (RIR 越多) 代表当天真实 1RM 越高
        low_effort = estimate_1rm(100.0, 5, rpe=7.0)
        high_effort = estimate_1rm(100.0, 5, rpe=9.0)
        assert low_effort > high_effort

    def test_calc_target_weight_rounds_to_half_kilo(self):
        # 0.5kg 精度
        assert calc_target_weight(100.0, 0.7, 8) in (70.0, 70.5)
        w = calc_target_weight(100.0, 0.7, 8)
        assert w * 2 == int(w * 2)


class TestCycleLength:
    def test_frequency_ge3_returns_8(self):
        assert determine_cycle_length(3) == 8
        assert determine_cycle_length(5) == 8

    def test_frequency_2_power_goal_returns_10(self):
        assert determine_cycle_length(2, goal="力量") == 10
        assert determine_cycle_length(2, goal="增肌") == 8

    def test_low_frequency_returns_12(self):
        assert determine_cycle_length(1) == 12

    def test_distribute_phases_sums_to_total(self):
        for weeks in (8, 10, 12):
            dist = distribute_phases(weeks)
            assert sum(dist.values()) == weeks
            assert list(dist.keys()) == ["积累", "强度", "实现", "减量"]

    def test_distribute_8_week_layout(self):
        assert distribute_phases(8) == {"积累": 3, "强度": 3, "实现": 1, "减量": 1}


class TestAssessLevel:
    def _profile(self, quality=5, years=3, has_record=True):
        prof = AthleteProfile(training_years=years)
        prof.movement_proficiency = {
            "深蹲": {
                "level": "L3",
                "recent_1rm": 140.0 if has_record else 0.0,
                "quality": quality,
            }
        }
        return prof

    def test_no_record_returns_p0(self):
        assert assess_level(self._profile(has_record=False), "深蹲") == "P0"

    def test_low_quality_returns_l1(self):
        assert assess_level(self._profile(quality=3, years=5), "深蹲") == "L1"

    def test_mid_experience_returns_l2(self):
        assert assess_level(self._profile(quality=5, years=2), "深蹲") == "L2"

    def test_master_returns_l3(self):
        assert assess_level(self._profile(quality=5, years=5), "深蹲") == "L3"

    def test_overall_empty_proficiency(self):
        p = AthleteProfile(training_years=2)
        assert assess_overall_level(p) == "L1"

    def test_overall_average_of_movements(self):
        p = AthleteProfile(training_years=5)
        p.movement_proficiency = {
            "深蹲": {"recent_1rm": 140.0, "quality": 5},  # L3
            "卧推": {"recent_1rm": 80.0, "quality": 3},  # L1
        }
        assert assess_overall_level(p) in ("L1", "L2")


class TestStrengthCycleGeneration:
    def test_cycle_structure(self):
        cycle = generate_strength_cycle("深蹲", current_1rm=100.0, target_1rm=140.0, weekly_exposures=2)
        assert isinstance(cycle, StrengthCycle)
        assert cycle.weeks == 10  # 频率2 + 力量目标
        assert len(cycle.days) == 10
        assert cycle.start_date  # 默认今天
        assert sum(cycle.phase_distribution.values()) == 10

    def test_first_week_is_accumulation(self):
        cycle = generate_strength_cycle("深蹲", current_1rm=100.0, target_1rm=140.0)
        assert cycle.days[0].phase == "积累"
        assert cycle.days[0].week == 1
        assert len(cycle.days[0].sets) == 2  # 顶组 + 回退组
        top = cycle.days[0].sets[0]
        assert top.set_type == "顶组"
        assert top.weight < 100.0  # 70% × (略高于当前1rm) < 当前1rm
        assert top.reps >= 8

    def test_intensity_progresses_over_cycle(self):
        cycle = generate_strength_cycle("深蹲", current_1rm=100.0, target_1rm=140.0)
        weights = [d.sets[0].weight for d in cycle.days]
        assert weights[-1] > weights[0]

    def test_last_week_is_deload(self):
        cycle = generate_strength_cycle("深蹲", current_1rm=100.0, target_1rm=140.0)
        assert cycle.days[-1].phase == "减量"
        assert cycle.days[-1].sets[0].reps >= 5

    def test_phase_distribution_matches_days(self):
        cycle = generate_strength_cycle("深蹲", current_1rm=100.0, target_1rm=140.0)
        from collections import Counter

        actual = Counter(d.phase for d in cycle.days)
        assert dict(actual) == cycle.phase_distribution


class TestReview:
    def _log(self, weight=100.0, reps=5, rpe=8.0, completed=True, prev=None):
        return TrainingLog(
            date="2026-06-01",
            movement="深蹲",
            weight=weight,
            reps=reps,
            sets=4,
            rpe=rpe,
            completed=completed,
            notes="",
        )

    def test_incomplete_session(self):
        r = review_training(self._log(completed=False))
        assert r.judgment == "部分完成"
        assert r.progression_type == "维持"

    def test_overload_downgrades_weight(self):
        # v9.1: RPE ≥9.5 或比目标少 ≥2 次 → 直接降约 5% 保住动作质量
        r = review_training(self._log(rpe=9.8))
        assert r.judgment == "合适"
        assert r.progression_type == "线性/波浪"  # 深蹲为复合主项
        assert r.next_prescription["weight"] == pytest.approx(95.0)

    def test_far_below_target_downgrades(self):
        # v9.1: 比目标少 ≥2 次 → 按表现降级, 而非旧版的"偏轻加次"
        r = review_training(self._log(rpe=6.0, reps=5))
        assert r.judgment == "合适"
        assert r.progression_type == "线性/波浪"
        assert r.next_prescription["weight"] == pytest.approx(95.0)

    def test_beat_target_with_low_rpe_adds_weight(self):
        # v9.1: 达到目标次数且 RPE 低于目标半档以上 → 上调一个最小重量档 (100kg 档位 → +5kg)
        r = review_training(self._log(rpe=6.0, reps=12))
        assert r.judgment == "偏轻"
        assert r.progression_type == "线性/波浪"
        assert r.next_prescription["weight"] == pytest.approx(105.0)

    def test_rpe_drop_with_same_load_downgrades(self):
        # v9.1: 次数仍远低于目标 (5/10) → 降约 5%, 不因 RPE 下降而直接加重
        prev = self._log(rpe=8.5)
        r = review_training(self._log(weight=100.0, reps=5, rpe=8.0), prev_log=prev)
        assert r.progression_type == "线性/波浪"
        assert r.next_prescription["weight"] == pytest.approx(95.0)

    def test_below_target_suggests_downgrade(self):
        # v9.1: 与上次同负荷同次数但仍低于目标次数 → 折算降级, 先补齐次数缺口
        prev = self._log(rpe=8.0)
        r = review_training(self._log(weight=100.0, reps=5, rpe=8.0), prev_log=prev)
        assert r.progression_type == "线性/波浪"
        assert r.next_prescription["weight"] == pytest.approx(95.0)

    def test_mid_range_below_target_downgrades(self):
        # v9.1: RPE 7.5 但比目标少 5 次 → 降级分支, 由复合主项线性/波浪推进
        r = review_training(self._log(rpe=7.5, reps=5))
        assert r.progression_type == "线性/波浪"
        assert r.next_prescription["weight"] == pytest.approx(95.0)

    def test_result_shape(self):
        r = review_training(self._log())
        assert isinstance(r, ReviewResult)
        assert isinstance(r.key_findings, list)
        assert "movement" in r.next_prescription
