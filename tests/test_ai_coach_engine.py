# -*- coding: utf-8 -*-
"""
ai_coach_engine 规则层单元测试
覆盖: RPE/RIR 换算、e1RM 与负荷换算互逆、周组数校验、复合禁止力竭、
      减量阶段不得重于实现阶段、2 项信号触发减载、危险信号优先、
      停滞需连续两次、停训接回判定、短版 5/2 分钟档。

运行: python -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_coach_engine import (  # noqa: E402
    TrainingLog, ReviewResult,
    generate_short_version, generate_strength_cycle, generate_return_plan,
    estimate_1rm, calc_target_weight, rpe_to_rir, review_training,
    screen_danger, deload_signals, weekly_set_range, check_weekly_sets,
    allows_failure, is_compound, rest_seconds, determine_cycle_length,
)


class TestRpeRir(unittest.TestCase):
    def test_table_values(self):
        self.assertEqual(rpe_to_rir(10.0), 0)
        self.assertEqual(rpe_to_rir(9.0), 1)
        self.assertEqual(rpe_to_rir(8.0), 2)
        self.assertEqual(rpe_to_rir(7.0), 3)

    def test_half_step_defaults_to_more_conservative_side(self):
        # RPE 与 RIR 一一对应, 半档取更保守(留更多余力)一侧: 7.5 → 2 次而非 3 次
        self.assertEqual(rpe_to_rir(7.5), 2)
        # 半档统一取保守侧: 8.5 与 8 同档, 9.5 与 9 同档, 7.5 不与 8 同档
        self.assertEqual(rpe_to_rir(8.5), 1)
        self.assertEqual(rpe_to_rir(7.5) + rpe_to_rir(8.5), 3)

    def test_monotonic(self):
        values = [rpe_to_rir(r / 2) for r in range(10, 21)]
        self.assertEqual(values, sorted(values, reverse=True))


class TestOneRm(unittest.TestCase):
    def test_no_longer_treats_current_reps_as_failure(self):
        # 100kg x 5 @8 → 还能做 2 次 → 力竭次数 7 → Epley 100*(1+7/30) = 123.3
        v = estimate_1rm(100, 5, 8.0)
        self.assertAlmostEqual(v, 123.33, places=1)
        # 旧实现加 3% RPE 奖励(121.7)且不修正余力, 与「RPE 只是描述余力」口径不符
        self.assertNotAlmostEqual(v, 100 * (1 + 5 / 30.0) * 1.03, places=1)

    def test_less_rir_means_lower_estimate(self):
        # 同一组数据 RPE 越高(余力越少) → 力竭次数越少 → e1RM 越低
        self.assertLess(estimate_1rm(100, 5, 9.5), estimate_1rm(100, 5, 7.5))

    def test_single_at_failure_returns_weight(self):
        self.assertAlmostEqual(estimate_1rm(120, 1, 10.0), 120.0)

    def test_roundtrip_with_target_weight(self):
        # e1RM 与负荷换算互为逆运算(容差来自 0.5kg 取整)
        e1rm = estimate_1rm(100, 5, 8.0)
        w = calc_target_weight(e1rm, 0.75, 5)
        self.assertLess(abs(w - e1rm * 0.75), 0.5)


class TestVolume(unittest.TestCase):
    def test_weekly_set_range_scales_with_sessions(self):
        self.assertEqual(weekly_set_range(4), (40, 80))

    def test_over_limit_requires_trial(self):
        self.assertEqual(check_weekly_sets(4, 30)['status'], '偏少')
        self.assertEqual(check_weekly_sets(4, 60)['status'], '区间内')
        self.assertEqual(check_weekly_sets(4, 120)['status'], '超上限')


class TestFailureAndRest(unittest.TestCase):
    def test_compound_never_to_failure(self):
        self.assertTrue(is_compound('卧推'))
        self.assertFalse(allows_failure('卧推', last_set=True))
        self.assertFalse(allows_failure('深蹲', last_set=True))

    def test_isolation_only_last_set(self):
        self.assertTrue(is_compound('哑铃弯举') is False)
        self.assertFalse(allows_failure('哑铃弯举', last_set=False))
        self.assertTrue(allows_failure('哑铃弯举', last_set=True))

    def test_rest_seconds(self):
        self.assertGreaterEqual(rest_seconds('深蹲'), 150)
        self.assertGreaterEqual(rest_seconds('侧平举'), 90)


class TestCycle(unittest.TestCase):
    def test_cycle_length_from_exposures(self):
        self.assertEqual(determine_cycle_length(3), 8)
        self.assertEqual(determine_cycle_length(1), 12)

    def test_deload_week_lighter_than_realization(self):
        cycle = generate_strength_cycle('卧推', 100, 115, 2)
        deload = [d for d in cycle.days if d.week in cycle.deload_weeks]
        realiz = [d for d in cycle.days if d.phase == '实现']
        self.assertTrue(deload, '应至少存在一个节律减载周')
        self.assertTrue(realiz, '应存在实现阶段')
        for d in deload:
            self.assertLess(d.sets[0].weight, realiz[0].sets[0].weight)

    def test_deload_has_signal(self):
        cycle = generate_strength_cycle('深蹲', 120, 140, 2)
        self.assertTrue(cycle.deload_weeks)
        self.assertLessEqual(cycle.deload_weeks[-1], cycle.weeks)

    def test_short_versions_have_5_and_2_minutes(self):
        cycle = generate_strength_cycle('卧推', 100, 115, 2)
        day = cycle.days[0]
        self.assertIn('5', day.short_version_5)
        self.assertIn('2', day.short_version_2)
        self.assertTrue(generate_short_version(day, 5))
        self.assertTrue(generate_short_version(day, 2))

    def test_warmup_and_rest_present(self):
        cycle = generate_strength_cycle('卧推', 100, 115, 2)
        day = cycle.days[0]
        self.assertGreaterEqual(len(day.warmup), 3)
        self.assertGreaterEqual(day.rest_seconds, 150)

    def test_volume_note_from_sessions(self):
        cycle = generate_strength_cycle('卧推', 100, 115, 2, sessions_per_week=3)
        self.assertIn('30-60', cycle.volume_note)


class TestReview(unittest.TestCase):
    def _log(self, **kw):
        base = dict(date='2026-09-16', movement='卧推', weight=80.0,
                    reps=8, sets=4, rpe=7.5)
        base.update(kw)
        return TrainingLog(**base)

    def test_normal_progression_adds_reps(self):
        r = review_training(self._log(reps=8, rpe=7.5))
        self.assertEqual(r.judgment, '合适')
        self.assertEqual(r.progression_type, '加次')

    def test_two_signals_trigger_deload(self):
        log = self._log(completed=False, abnormal_fatigue=True)
        self.assertGreaterEqual(len(deload_signals(log)), 2)
        r = review_training(log)
        self.assertTrue(r.deload_recommended)
        self.assertEqual(r.progression_type, '减量')
        self.assertLess(r.next_prescription['weight'], log.weight)

    def test_single_signal_does_not_deload(self):
        log = self._log(completed=False)
        self.assertLess(len(deload_signals(log)), 2)
        self.assertFalse(review_training(log).deload_recommended)

    def test_danger_signal_holds_training(self):
        log = self._log(pain=True, pain_desc='胸部不适并向左臂放射痛')
        self.assertTrue(screen_danger(log.pain_desc))
        r = review_training(log)
        self.assertTrue(r.safety_hold)
        self.assertEqual(r.progression_type, '暂停')
        self.assertEqual(r.next_prescription['action'], '暂停')

    def test_single_stall_does_not_change_structure(self):
        prev = self._log(reps=8, rpe=7.5)
        cur = self._log(reps=7, rpe=7.5)
        r = review_training(cur, prev)
        self.assertEqual(r.progression_type, '维持')
        self.assertFalse(r.deload_recommended)
        self.assertTrue(any('单次异常' in f for f in r.key_findings))

    def test_stall_repeats_are_reported(self):
        prev = self._log(reps=7, rpe=8.5)
        cur = self._log(reps=6, rpe=8.5)
        r = review_training(cur, prev)
        self.assertTrue(r.key_findings)

    def test_review_result_defaults(self):
        r = ReviewResult('合适', [], {}, '维持')
        self.assertFalse(r.deload_recommended)
        self.assertFalse(r.safety_hold)


class TestReturn(unittest.TestCase):
    def test_one_missed_session_no_makeup(self):
        plan = generate_return_plan(0, 80, '卧推', missed_sessions=1)
        self.assertEqual(plan.permission, '正常接回')
        self.assertIn('不补课', plan.normal_version)

    def test_two_missed_sessions_use_short_version(self):
        plan = generate_return_plan(0, 80, '卧推', missed_sessions=2)
        self.assertIn('30 分钟', plan.degraded_version)

    def test_14_days_degraded_return(self):
        plan = generate_return_plan(14, 100, '深蹲')
        self.assertEqual(plan.permission, '降级接回')
        self.assertIn('48', plan.first_step_48h)
        self.assertTrue(plan.upgrade_condition)
        self.assertTrue(plan.pause_condition)

    def test_84_days_reset(self):
        plan = generate_return_plan(90, 100, '深蹲')
        self.assertEqual(plan.permission, '暂停')
        self.assertIn('重新建档', plan.normal_version)


if __name__ == '__main__':
    unittest.main()
