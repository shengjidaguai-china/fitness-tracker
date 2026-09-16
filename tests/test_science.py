# -*- coding: utf-8 -*-
"""
训练科学规则层单元测试 (v9.1)

不依赖第三方包, 用标准库 unittest 运行:
    python -m unittest discover -s tests -v
    python tests/test_science.py

测试只使用匿名示例数据, 不读取也不写入个人数据目录。
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, 'fitness_pkg')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import science  # noqa: E402


class TestRpeScale(unittest.TestCase):
    """RPE / RIR 换算 (Helms 训练金字塔 pp.64-65)"""

    def test_rpe_to_rir_mapping(self):
        self.assertEqual(science.rpe_to_rir(10.0), 0)
        self.assertEqual(science.rpe_to_rir(9.0), 1)
        self.assertEqual(science.rpe_to_rir(8.0), 2)
        self.assertEqual(science.rpe_to_rir(7.0), 3)

    def test_rpe_to_rir_on_half_steps_is_conservative(self):
        # 半档取更保守 (RIR 更多) 的一侧, 避免高估训练者的余力
        self.assertEqual(science.rpe_to_rir(8.5), 1)
        self.assertEqual(science.rpe_to_rir(7.5), 3)

    def test_rpe_to_rir_clamps_out_of_range(self):
        self.assertEqual(science.rpe_to_rir(11.0), 0)
        self.assertEqual(science.rpe_to_rir(3.0), 5)

    def test_rpe_text_keeps_rir_context(self):
        self.assertIn('≈2 RIR', science.rpe_to_rir_text(8.0))


class TestE1rm(unittest.TestCase):
    """e1RM 估算与负荷换算"""

    def test_e1rm_scales_with_rpe(self):
        low = science.e1rm_from_set(100, 5, 7.0)
        high = science.e1rm_from_set(100, 5, 9.0)
        self.assertGreater(low, high, '同样的重量次数, 离力竭越远 e1RM 应越高')

    def test_e1rm_single_regression(self):
        self.assertEqual(science.e1rm_from_set(100, 1, 10.0), 100.0)

    def test_e1rm_guards_invalid_input(self):
        self.assertEqual(science.e1rm_from_set(0, 5, 8.0), 0.0)
        self.assertEqual(science.e1rm_from_set(100, 0, 8.0), 0.0)

    def test_load_for_target_reps_inverse_of_e1rm(self):
        e1rm = 100.0
        load = science.load_for_target_reps(e1rm, 8, 8.0)
        self.assertIsInstance(load, float)
        self.assertTrue(70 <= load <= 85, f'8 次 @RPE8 约在 70-85% e1RM, 实际 {load}')

    def test_e1rm_and_load_are_mutually_inverse(self):
        # 同一口径闭环: 由记录反推的 e1RM 再按同一次数/RPE 折回来应回到原重量
        e1rm = science.e1rm_from_set(100, 8, 8.0)
        self.assertAlmostEqual(science.load_for_target_reps(e1rm, 8, 8.0), 100.0, delta=2.5)  # 0.5kg 取整

    def test_reps_to_intensity_monotonic(self):
        pcts = [science.reps_to_intensity(r, 8.0) for r in (3, 8, 12)]
        self.assertEqual(pcts, sorted(pcts, reverse=True), '次数越多强度百分比应越低')

    def test_no_e1rm_returns_zero(self):
        self.assertEqual(science.load_for_target_reps(0, 8, 8.0), 0.0)


class TestVolumeBands(unittest.TestCase):
    """周组数区间 (Helms: 每肌群 10–20 组起始区间, 20 组非上限)"""

    def test_band_ranges(self):
        low, high = science.weekly_set_band('L1')
        self.assertEqual((low, high), (10, 14))

    def test_unknown_level_falls_back_to_p0(self):
        self.assertEqual(science.weekly_set_band('X9'), science.weekly_set_band('P0'))

    def test_verdicts(self):
        self.assertEqual(science.analyze_weekly_volume('L1', 8)['verdict'], '偏少')
        self.assertEqual(science.analyze_weekly_volume('L1', 12)['verdict'], '合适')
        self.assertEqual(science.analyze_weekly_volume('L1', 18)['verdict'], '偏高')
        self.assertEqual(science.analyze_weekly_volume('L1', 26)['verdict'], '超出验证区间')

    def test_ceiling_documented(self):
        self.assertEqual(science.WEEKLY_SET_CEILING, 20)


class TestAutoregulation(unittest.TestCase):
    """自动调节 (Nuckols APRE/RPE; 一次只动一个变量)"""

    def test_downgrade_when_too_hard(self):
        r = science.autoregulated_set(100, 5, 9.5, target_reps=8, target_rpe=8.0)
        self.assertEqual(r['action'], '降级')
        self.assertLess(r['suggested_weight'], 100)

    def test_upgrade_step_is_minimal(self):
        r = science.autoregulated_set(100, 10, 7.0, target_reps=8, target_rpe=8.0)
        self.assertEqual(r['action'], '上调')
        self.assertLessEqual(r['suggested_weight'] - 100, science.min_weight_step(100))

    def test_hold_when_on_target(self):
        r = science.autoregulated_set(60, 8, 8.0, target_reps=8, target_rpe=8.0)
        self.assertEqual(r['action'], '维持')
        self.assertEqual(r['suggested_weight'], 60)

    def test_weight_step_tiers(self):
        self.assertEqual(science.min_weight_step(15), 1.0)
        self.assertEqual(science.min_weight_step(40), 2.5)
        self.assertEqual(science.min_weight_step(120), 5.0)


class TestDoubleProgression(unittest.TestCase):
    """双重渐进 (Helms: 孤立/小肌群适合双重渐进; 复合优先线性-波浪)"""

    def test_adds_rep_before_load(self):
        rx = science.apply_double_progression(12, 8, 3, 8.0, (8, 12), is_isolation=True)
        self.assertEqual(rx['progression_type'], '加次')
        self.assertEqual(rx['weight'], 12)
        self.assertEqual(rx['reps'], 9)

    def test_adds_load_after_rep_ceiling(self):
        rx = science.apply_double_progression(12, 12, 3, 8.0, (8, 12), is_isolation=True)
        self.assertEqual(rx['progression_type'], '加重')
        self.assertGreater(rx['weight'], 12)
        self.assertEqual(rx['reps'], 8)

    def test_rep_cap_not_exceeded(self):
        rx = science.apply_double_progression(20, 11, 3, 8.0, (8, 12), is_isolation=True)
        self.assertLessEqual(rx['reps'], 12)

    def test_compound_not_forced_into_double_progression(self):
        rx = science.apply_double_progression(100, 8, 4, 8.0, (8, 12), is_isolation=False)
        self.assertIn('线性', rx['progression_type'])


class TestDeloadSignals(unittest.TestCase):
    """反应式减载清单 (Helms pp.121-125)"""

    def test_zero_or_one_signal_continues(self):
        out = science.evaluate_deload_signals({'sleep_worse': True})
        self.assertEqual(out['verdict'], '继续前进')
        self.assertEqual(out['volume_reduction'], 0.0)

    def test_two_signals_trigger_deload(self):
        out = science.evaluate_deload_signals({'sleep_worse': True, 'performance_drop': True})
        self.assertEqual(out['verdict'], '减载一周')
        self.assertAlmostEqual(out['volume_reduction'], 0.2)

    def test_proactive_deload_after_three_cycles(self):
        out = science.evaluate_deload_signals({'cycles_since_deload': 3})
        self.assertEqual(out['verdict'], '预防性减载')

    def test_all_signals_reported(self):
        out = science.evaluate_deload_signals({k: True for k, _ in science.DELOAD_SIGNALS})
        self.assertEqual(out['count'], len(science.DELOAD_SIGNALS))


class TestSetStructure(unittest.TestCase):
    """热身/多组 RPE 路径/休息/力竭 (Helms Level 5, Schoenfeld 第 4 章)"""

    def test_warmup_is_ascending_and_not_fatiguing(self):
        warmup = science.build_warmup_sets(100)
        weights = [w['weight'] for w in warmup if w['weight'] > 0]
        self.assertEqual(weights, sorted(weights))
        self.assertTrue(all(w['rpe'] <= 7.0 for w in warmup), '热身不应产生明显疲劳')

    def test_warmup_without_e1rm_is_safe(self):
        self.assertTrue(len(science.build_warmup_sets(0)) >= 1)

    def test_rpe_path_spans_start_to_end(self):
        path = science.build_rpe_path(4, 6.0, 9.0)
        self.assertEqual(len(path), 4)
        self.assertEqual(path[0], 6.0)
        self.assertEqual(path[-1], 9.0)
        self.assertEqual(path, sorted(path))

    def test_rpe_path_single_set(self):
        self.assertEqual(science.build_rpe_path(1, 6.0, 8.0), [8.0])

    def test_rest_compound_longer_than_isolation(self):
        self.assertGreater(science.rest_seconds('深蹲')[0], science.rest_seconds('哑铃弯举')[0])
        self.assertGreaterEqual(science.rest_seconds('卧推')[0], 150)

    def test_compound_disallows_failure(self):
        f = science.failure_allowance('卧推', 4, 4)
        self.assertFalse(f['allow_failure'])
        self.assertEqual(f['max_rpe'], 9.0)

    def test_isolation_allows_failure_on_last_set_only(self):
        self.assertTrue(science.failure_allowance('哑铃弯举', 3, 3)['allow_failure'])
        self.assertFalse(science.failure_allowance('哑铃弯举', 1, 3)['allow_failure'])

    def test_tempo_never_prescribes_slow_eccentric_by_default(self):
        t = science.tempo_prescription(True, '增肌')
        self.assertIn('不做刻意的 4 秒超慢离心', t['note'])


class TestStallAndPlateau(unittest.TestCase):
    """停滞与平台判定 (Lzheng: 连续两次异常才怀疑结构)"""

    def test_single_anomaly_is_not_stall(self):
        history = [
            {'index': 1, 'weight': 60, 'reps': 8, 'rpe': 8.0},
            {'index': 2, 'weight': 60, 'reps': 7, 'rpe': 8.0},
        ]
        self.assertFalse(science.detect_stall(history)['is_stall'])

    def test_two_anomalies_trigger_stall(self):
        history = [
            {'index': 1, 'weight': 60, 'reps': 8, 'rpe': 8.0},
            {'index': 2, 'weight': 60, 'reps': 7, 'rpe': 8.5},
            {'index': 3, 'weight': 60, 'reps': 7, 'rpe': 9.5},
        ]
        out = science.detect_stall(history)
        self.assertTrue(out['is_stall'])
        self.assertGreaterEqual(out['flags'], out['threshold'])

    def test_weight_change_is_not_comparable(self):
        history = [
            {'index': 1, 'weight': 60, 'reps': 8, 'rpe': 8.0},
            {'index': 2, 'weight': 62.5, 'reps': 7, 'rpe': 9.0},
            {'index': 3, 'weight': 65, 'reps': 6, 'rpe': 9.5},
        ]
        self.assertFalse(science.detect_stall(history)['is_stall'])

    def test_plateau_needs_enough_records(self):
        self.assertFalse(science.detect_plateau([100, 102])['is_plateau'])
        self.assertIn('不足', science.detect_plateau([100, 102])['reason'])

    def test_plateau_detected_on_flat_trend(self):
        out = science.detect_plateau([100, 100.5, 100.2, 100.1, 100.0, 100.1], sessions=6)
        self.assertTrue(out['is_plateau'])

    def test_progressing_trend_is_not_plateau(self):
        out = science.detect_plateau([100, 101, 102, 103, 104, 105], sessions=6)
        self.assertFalse(out['is_plateau'])


class TestSafetyAndAudit(unittest.TestCase):
    """安全分流与动作缺口审计"""

    def test_red_flag_is_screened_out(self):
        self.assertIsNotNone(science.screen_action('训练时出现胸部不适和麻木'))
        self.assertIn('专业评估', science.screen_action('腰痛伴腿麻'))

    def test_benign_note_passes(self):
        self.assertIsNone(science.screen_action('今天状态不错, 睡眠充足'))

    def test_movement_gaps_detected(self):
        out = science.audit_movement_gaps(['杠铃卧推', '引体向上', '深蹲'])
        self.assertIn('髋铰链', out['gaps'])
        self.assertIn('负重行走', out['gaps'])
        self.assertIn('推', out['covered'])

    def test_full_coverage_reports_no_gap(self):
        names = ['卧推', '划船', '硬拉', '深蹲', '农夫走', '单腿罗马尼亚硬拉']
        out = science.audit_movement_gaps(names)
        self.assertEqual(out['gaps'], [])


class TestReviewSession(unittest.TestCase):
    """端到端复盘决策"""

    def test_safety_first(self):
        ctx = science.ReviewContext(movement='卧推', weight=80, reps=5, sets=4, rpe=9.0,
                                    pain_note='肩部锐痛并放射到手臂')
        out = science.review_session(ctx)
        self.assertEqual(out.judgment, '暂停常规处方')
        self.assertIsNotNone(out.safety)

    def test_incomplete_session_does_not_add_volume(self):
        ctx = science.ReviewContext(movement='深蹲', weight=100, reps=8, sets=4, rpe=8.0,
                                    completed=False, level='L2')
        out = science.review_session(ctx)
        self.assertEqual(out.judgment, '部分完成')
        self.assertEqual(out.progression_type, '维持')

    def test_deload_overrides_progression(self):
        ctx = science.ReviewContext(movement='深蹲', weight=100, reps=8, sets=4, rpe=8.0,
                                    level='L2', signals={'sleep_worse': True, 'life_stress': True})
        out = science.review_session(ctx)
        self.assertEqual(out.progression_type, '减量')
        self.assertEqual(out.next_prescription['sets'], 3)

    def test_normal_session_carries_full_prescription(self):
        ctx = science.ReviewContext(movement='哑铃弯举', weight=12.5, reps=12, sets=3, rpe=8.0,
                                    target_reps=12, level='L1', weekly_sets=12)
        rx = science.review_session(ctx).next_prescription
        for key in ('weight', 'reps', 'sets', 'rpe_path', 'rest', 'failure', 'tempo'):
            self.assertIn(key, rx)


if __name__ == '__main__':
    unittest.main(verbosity=2)
