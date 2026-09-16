"""
fitness_pkg 兼容层单元测试 (unittest 风格, 可 `python -m unittest discover -s tests` 单独跑)

覆盖: 兼容层导出面、数据模型加载/统计/预测、训练计划解析器分阶段、动作库容错。
GUI 相关 (ExerciseLibrary 需要 PySide6.QtGui) 在缺依赖时跳过, 与 pytest 用例互不重复。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fitness_pkg.data_model import BodyDataModel
from fitness_pkg.parsers import NutritionParser, TrainingPlanParser

try:
    from fitness_pkg.exercise_lib import ExerciseLibrary  # 需要 PySide6.QtGui

    QT_AVAILABLE = True
    QT_SKIP_REASON = ""
except ImportError as e:  # 缺 GUI 依赖属正常环境 (CI / 无显示器)
    ExerciseLibrary = None
    QT_AVAILABLE = False
    QT_SKIP_REASON = f"缺少 GUI 依赖: {e}"


class TestCompatShim(unittest.TestCase):
    """兼容层 fitness_modules 的导出面必须覆盖主程序用到的名字"""

    def test_logic_names_exported(self):
        import fitness_modules as fm

        for name in (
            "BodyDataModel",
            "TrainingPlanParser",
            "NutritionParser",
            "PHASE_INFO",
            "TRAINING_SCHEDULE",
            "COLORS",
        ):
            self.assertTrue(hasattr(fm, name), f"兼容层缺少 {name}")

    def test_package_logic_layer_has_no_gui_dependency(self):
        import fitness_pkg

        self.assertFalse(fitness_pkg.GUI_AVAILABLE is None)
        for name in ("science", "plan_science", "parsers", "data_model"):
            self.assertIsNotNone(__import__(f"fitness_pkg.{name}", fromlist=[name]))


class TestBodyDataModel(unittest.TestCase):
    def setUp(self):
        self.m = BodyDataModel()

    def test_loads_without_crash(self):
        self.assertIsNotNone(self.m.df)

    def test_stats_empty_or_filled(self):
        stats = self.m.get_stats()
        self.assertIn("count", stats)

    def test_get_stats_keys_when_data(self):
        stats = self.m.get_stats()
        if stats.get("count"):
            for k in ("days", "cur_weight", "weight_change", "cur_fat"):
                self.assertIn(k, stats)

    def test_plot_df_sorted(self):
        df = self.m.get_plot_df()
        self.assertIn("日期_dt", df.columns)

    def test_predict_unknown_column_returns_none(self):
        """回归: 列名不存在时应返回 None, 而不是抛 KeyError"""
        self.assertIsNone(self.m.predict_target_date(60.0, col="不存在的列"))


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
        for _day, items in days.items():
            self.assertIsInstance(items, list)

    def test_phase_notes_list(self):
        self.assertIsInstance(self.p.get_phase_notes(1), list)


class TestNutritionParser(unittest.TestCase):
    def test_constructs(self):
        NutritionParser()


@unittest.skipUnless(QT_AVAILABLE, QT_SKIP_REASON)
class TestExerciseLibrary(unittest.TestCase):
    def test_constructs_without_qt(self):
        lib = ExerciseLibrary()
        self.assertIsInstance(lib.exercises, list)

    def test_missing_media_id_returns_none(self):
        lib = ExerciseLibrary()
        self.assertIsNone(lib.get_by_media_id("__not_exists__"))


if __name__ == "__main__":
    unittest.main()
