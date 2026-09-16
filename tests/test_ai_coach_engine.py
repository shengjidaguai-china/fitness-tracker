# -*- coding: utf-8 -*-
"""
ai_coach_engine 规则层单元测试
覆盖: RPE/RIR 换算、e1RM 与负荷换算互逆、周组数校验、复合禁止力竭、
      减量阶段不得重于实现阶段、2 项信号触发减载、危险信号优先、
      停滞需连续两次、停训接回判定、短版 5/2 分钟档、规则来源可追溯。

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
        # 100kg x 5 @8 → 还能做 2 次(RIR 2); 先按 RIR 折算到当天力竭会用的重量再套 Epley
        v = estimate_1rm(100, 5, 8.0)
        self.assertGreater(v, 100.0)
        # 旧实现把当前次数直接当力竭次数(100*(1+5/30)=116.67), 该高估口径已移除
        self.assertNotAlmostEqual(v, 100 * (1 + 5 / 30.0), places=1)
        # 口径自洽: 同一次数与重量下 RPE 越高(余力越少) → e1RM 越低
        self.assertLess(estimate_1rm(100, 5, 9.0), estimate_1rm(100, 5, 8.0))

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
        self.assertEqual(determine_cycle_length(2, '力量'), 10)
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
        # 孤立动作在次数区间内 → 双重渐进先加次数
        r = review_training(self._log(movement='哑铃弯举', reps=8, rpe=8.0),
                            target_reps=12, rep_window=(8, 12))
        self.assertEqual(r.judgment, '合适')
        self.assertEqual(r.progression_type, '加次')
        self.assertEqual(r.next_prescription['reps'], 9)

    def test_compound_uses_linear_wave_progression(self):
        # 复合主项走线性/波浪推进, 不在复盘里机械加次
        r = review_training(self._log(movement='卧推', reps=5, rpe=8.0))
        self.assertEqual(r.progression_type, '线性/波浪')
        self.assertTrue(r.next_prescription['rpe_path'])

    def test_two_signals_trigger_deload(self):
        log = self._log()
        signals = {'sleep_worse': True, 'pain': True}
        self.assertGreaterEqual(len(deload_signals(log, signals=signals)), 2)
        r = review_training(log, signals=signals)
        self.assertTrue(r.deload_recommended)
        self.assertEqual(r.progression_type, '减量')
        self.assertLess(r.next_prescription['weight'], log.weight)

    def test_single_signal_does_not_deload(self):
        log = self._log()
        signals = {'sleep_worse': True}
        self.assertLess(len(deload_signals(log, signals=signals)), 2)
        self.assertFalse(review_training(log, signals=signals).deload_recommended)

    def test_danger_signal_holds_training(self):
        log = self._log(notes='胸部不适并向左臂放射痛')
        self.assertTrue(screen_danger(log.notes))
        r = review_training(log)
        self.assertTrue(r.safety_hold)
        self.assertEqual(r.progression_type, '暂停')
        self.assertEqual(r.next_prescription['action'], '先评估再恢复训练')

    def test_single_stall_does_not_change_structure(self):
        # 单次同重量掉次数 → 只维持观察, 不改周期结构
        prev = self._log(movement='哑铃弯举', reps=10, rpe=8.0)
        cur = self._log(movement='哑铃弯举', reps=9, rpe=8.0)
        r = review_training(cur, prev_log=prev, target_reps=12, rep_window=(8, 12))
        self.assertFalse(r.deload_recommended)
        self.assertTrue(r.key_findings)
        self.assertNotEqual(r.progression_type, '结构调整')

    def test_stall_repeats_are_reported(self):
        # 连续两次可比记录异常 → 怀疑周期结构而非当日状态
        hist = [{'weight': 80.0, 'reps': 8, 'rpe': 8.0},
                {'weight': 80.0, 'reps': 7, 'rpe': 9.0}]
        r = review_training(self._log(movement='哑铃弯举', reps=6, rpe=9.0), history=hist)
        self.assertTrue(r.key_findings)
        self.assertIn(r.judgment, ('停滞', '合适', '偏重'))

    def test_review_reports_rule_source(self):
        # 判定口径来自规则层, 可追溯到来源
        r = review_training(self._log(movement='哑铃弯举', reps=8, rpe=8.0), target_reps=12)
        self.assertIn('规则层', r.rule_source)

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
        self.assertIn('48 小时', plan.return_48h)
        self.assertEqual(len(plan.exit_conditions), 3)
        self.assertTrue(plan.exit_conditions.get('upgrade'))
        self.assertTrue(plan.exit_conditions.get('stop'))

    def test_56_days_lowest_task(self):
        plan = generate_return_plan(56, 100, '深蹲')
        self.assertEqual(plan.permission, '最低任务')

    def test_90_days_reset(self):
        plan = generate_return_plan(90, 100, '深蹲')
        self.assertEqual(plan.permission, '暂停')
        self.assertIn('重新建档', plan.normal_version)


if __name__ == '__main__':
    unittest.main()
