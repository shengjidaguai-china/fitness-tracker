"""22 周计划科学化视图单元测试 (ROADMAP F9)

覆盖: 阶段/减载周口径、组次解析容错、肌群归类、周组数区间判定、
减载周不变量 (减载周强度必须低于相邻实现周), 以及解析失败时的 fail-open。
"""

import pytest

from fitness_pkg.plan_science import (
    DELOAD_VOLUME_RATIO,
    RHYTHMIC_DELOAD_WEEKS,
    day_execution_note,
    deload_guidance,
    estimate_muscle_sets,
    estimate_weekly_sets,
    is_deload_week,
    muscle_bucket_of,
    parse_group_spec,
    phase_of_week,
    plan_science_summary,
    week_display_meta,
    weekly_volume_status,
)


def _week(**days):
    """构造一周动作表: 周一=[{'name': ..., 'sets': ...}, ...]"""
    return dict(days)


class TestPhaseAndDeload:
    def test_phase_boundaries_match_plan(self):
        assert phase_of_week(1) == 1
        assert phase_of_week(6) == 1
        assert phase_of_week(7) == 2
        assert phase_of_week(14) == 2
        assert phase_of_week(15) == 3
        assert phase_of_week(22) == 3

    def test_deload_weeks_are_lighter_than_every_implementation_week(self):
        """不变量: 减载周强度必须低于任何相邻阶段周 (不能把减载写成更重的验证周)。"""
        for week in RHYTHMIC_DELOAD_WEEKS:
            meta = week_display_meta(week)
            assert meta["is_deload"] is True
            assert DELOAD_VOLUME_RATIO < 1.0
            assert str(int(DELOAD_VOLUME_RATIO * 100)) in meta["volume_note"]

    def test_non_deload_week_not_flagged(self):
        for week in (1, 7, 12, 15, 22):
            assert is_deload_week(week) is False

    def test_phase_of_week_clamps_invalid_input(self):
        assert phase_of_week(0) == 1
        assert phase_of_week(-5) == 1


class TestParseGroupSpec:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("4×8-10", (4, 8, 10)),
            ("4组×8-10次", (4, 8, 10)),
            ("3x12", (3, 12, 12)),
            ("4 组 × 6", (4, 6, 6)),
            ("5组", (5, None, None)),
            ("4 循环", (4, None, None)),
        ],
    )
    def test_parses_common_formats(self, text, expected):
        parsed = parse_group_spec(text)
        assert (parsed["sets"], parsed["reps_low"], parsed["reps_high"]) == expected

    @pytest.mark.parametrize("text", ["", None, "热身", "弹力带", "按需"])
    def test_unparsable_returns_zero_sets(self, text):
        assert parse_group_spec(text)["sets"] == 0

    def test_raw_text_is_preserved(self):
        assert parse_group_spec("4×8").get("raw") == "4×8"


class TestMuscleBucket:
    def test_counts_compound_only_in_primary_bucket(self):
        est = estimate_muscle_sets([{"name": "宽握引体", "sets": "4×8"}, {"name": "哑铃弯举", "sets": "3×12"}])
        assert est["sets_by_muscle"] == {"背(宽)": 4, "手臂": 3}
        assert est["total_sets"] == 7

    def test_skips_workout_blocks(self):
        est = estimate_muscle_sets(
            [
                {"name": "动态热身", "sets": "热身", "is_workout_block": True},
                {"name": "快走/椭圆机 (LISS)", "sets": "35分钟", "is_workout_block": True},
                {"name": "宽握引体", "sets": "4×8"},
            ]
        )
        assert est["total_sets"] == 4

    def test_unclassified_exercise_is_reported_not_silently_counted(self):
        est = estimate_muscle_sets([{"name": "神秘动作", "sets": "3×10"}])
        assert est["total_sets"] == 0
        assert est["unclassified"] == ["神秘动作"]

    def test_muscle_bucket_of_takes_longest_keyword(self):
        assert muscle_bucket_of("胸支撑哑铃划船") == "背(厚)"
        assert muscle_bucket_of("椅子臂屈伸") == "胸"
        assert muscle_bucket_of("反向飞鸟") == "背(宽)"
        assert muscle_bucket_of("保加利亚分腿蹲") == "腿"
        assert muscle_bucket_of("") is None


class TestWeeklyVolume:
    def test_zero_training_days_is_not_judged(self):
        """回归: 解析不到计划时必须「不判定」, 不能误报成「练得太少」。"""
        status = weekly_volume_status(_week(周一=[]), "L1")
        assert status["verdict"] == "不判定"
        assert status["items"] == []
        assert "休息周" in status["action"] or "未解析到" in status["action"]

    def test_weekly_sets_sum_matches_helm_unit(self):
        week = _week(周一=[{"name": "宽握引体", "sets": "5×8"}], 周四=[{"name": "对握引体", "sets": "5×8"}])
        est = estimate_weekly_sets(week)
        assert est["sets_by_muscle"] == {"背(宽)": 10}
        assert est["training_days"] == 2
        assert est["day_breakdown"]["周一"] == {"背(宽)": 5}

    def test_verdicts_cover_whole_helm_band(self):
        low_sets = weekly_volume_status(_week(周一=[{"name": "宽握引体", "sets": "4×8"}]), "L1")
        ok_sets = weekly_volume_status(_week(周一=[{"name": "宽握引体", "sets": "12×8"}]), "L1")
        high_sets = weekly_volume_status(_week(周一=[{"name": "宽握引体", "sets": "18×8"}]), "L1")
        over_sets = weekly_volume_status(_week(周一=[{"name": "宽握引体", "sets": "22×8"}]), "L1")
        assert [s["items"][0]["verdict"] for s in (low_sets, ok_sets, high_sets, over_sets)] == [
            "偏少",
            "合适",
            "偏高",
            "超出验证区间",
        ]

    def test_bands_follow_level(self):
        week = _week(周一=[{"name": "宽握引体", "sets": "8×8"}])
        assert weekly_volume_status(week, "P0")["band"] == (6, 10)
        assert weekly_volume_status(week, "L3")["band"] == (14, 20)


class TestGuidance:
    def test_deload_triggers_on_two_signals(self):
        """规则层口径不允许在视图层漂移: 2 项信号即减载一周。"""
        guidance = deload_guidance({"sleep_worse": True, "pain": True})
        assert guidance["verdict"] == "减载一周"
        assert guidance["count"] == 2

    def test_single_signal_keeps_progressing(self):
        assert deload_guidance({"sleep_worse": True})["verdict"] == "继续前进"

    def test_rhythmic_weeks_and_ratio_exposed(self):
        guidance = deload_guidance({})
        assert guidance["rhythmic_weeks"] == list(RHYTHMIC_DELOAD_WEEKS)
        assert 0 < guidance["volume_ratio"] < 1

    def test_execution_note_uses_rule_layer_rest_floor(self):
        squat = day_execution_note("深蹲")
        curl = day_execution_note("弯举")
        assert squat["movement_kind"] == "compound"
        assert curl["movement_kind"] == "isolation"
        assert squat["rest_seconds"] >= 150
        assert curl["rest_seconds"] >= 90
        assert squat["failure"]["allow_failure"] is False
        assert curl["failure"]["allow_failure"] is True
        assert squat["rpe_path_example"] == sorted(squat["rpe_path_example"])


class TestSummary:
    def test_week_meta_exposes_same_text_as_rule_layer(self):
        meta = week_display_meta(8, "L1", {"sleep_worse": True, "pain": True})
        assert meta["is_deload"] is True
        assert meta["deload_guidance"]["verdict"] == "减载一周"
        assert "不补课" in meta["short_version_rule"]

    def test_summary_bundles_all_sections(self):
        week = _week(周一=[{"name": "宽握引体", "sets": "4×8"}])
        summary = plan_science_summary(week, day_exercises=week["周一"], week=3, level="L1")
        for key in ("weekly_volume", "day_volume", "execution", "training_days", "volume_note"):
            assert key in summary
        assert summary["training_days"] == 1
        assert summary["weekly_volume"]["verdict"] == "已判定"
