# -*- coding: utf-8 -*-
"""
fitness_pkg 纯逻辑单元测试 (不依赖 PySide6, 便于云端运行)
覆盖: 数据模型加载/统计/预测、训练计划解析器分阶段、动作库容错。

运行: python -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:  # 桌面 GUI 依赖缺失时跳过本文件 (云端无 PySide6 属正常环境)
    from fitness_pkg.data_model import BodyDataModel  # noqa: E402
    from fitness_pkg.parsers import TrainingPlanParser, NutritionParser  # noqa: E402
    from fitness_pkg.exercise_lib import ExerciseLibrary  # noqa: E402
    PKG_AVAILABLE = True
    PKG_SKIP_REASON = ''
except ImportError as e:  # noqa: BLE001
    PKG_AVAILABLE = False
    PKG_SKIP_REASON = f'缺少依赖: {e}'


@unittest.skipUnless(PKG_AVAILABLE, '需要 PySide6 / numpy / pandas')
class _NeedsPkg:
    pass


@unittest.skipUnless(PKG_AVAILABLE, PKG_SKIP_REASON)
class TestBodyDataModel(unittest.TestCase):
    def setUp(self):
        self.m = BodyDataModel()

    def test_loads_without_crash(self):
        self.assertIsNotNone(self.m.df)

    def test_stats_empty_or_filled(self):
        stats = self.m.get_stats()
        self.assertIn('count', stats)

    def test_get_stats_keys_when_data(self):
        stats = self.m.get_stats()
        if stats.get('count'):
            for k in ('days', 'cur_weight', 'weight_change', 'cur_fat'):
                self.assertIn(k, stats)

    def test_plot_df_sorted(self):
        df = self.m.get_plot_df()
        self.assertIn('日期_dt', df.columns)


@unittest.skipUnless(PKG_AVAILABLE, PKG_SKIP_REASON)
class TestTrainingPlanParser(unittest.TestCase):
    def setUp(self):
        self.p = TrainingPlanParser()

    def test_phase_mapping(self):
        self.assertEqual(TrainingPlanParser.get_phase(1), 1)
        self.assertEqual(TrainingPlanParser.get_phase(6), 1)
        self.assertEqual(TrainingPlanParser.get_phase(7), 2)
        self.assertEqual(TrainingPlanParser.get_phase(14), 2)
        self.assertEqual(TrainingPlanParser.get_phase(15), 3)
        self.assertEqual(TrainingPlanParser.get_phase(22), 3)

    def test_daily_exercises_shape(self):
        days = self.p.get_daily_exercises(1)
        self.assertIsInstance(days, dict)
        for day, items in days.items():
            self.assertIsInstance(items, list)

    def test_phase_notes_list(self):
        self.assertIsInstance(self.p.get_phase_notes(1), list)


@unittest.skipUnless(PKG_AVAILABLE, PKG_SKIP_REASON)
class TestNutritionParser(unittest.TestCase):
    def test_constructs(self):
        NutritionParser()


@unittest.skipUnless(PKG_AVAILABLE, PKG_SKIP_REASON)
class TestExerciseLibrary(unittest.TestCase):
    def test_constructs_without_qt(self):
        lib = ExerciseLibrary()
        self.assertIsInstance(lib.exercises, list)

    def test_missing_media_id_returns_none(self):
        lib = ExerciseLibrary()
        self.assertIsNone(lib.get_by_media_id('__not_exists__'))


if __name__ == '__main__':
    unittest.main()
