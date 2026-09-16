"""UI 页面构造冒烟 — 在 Qt offscreen 平台实例化主要页面

验证工程化重构(ruff format/死代码移除/缓存拷贝化)未破坏窗口构建。
不进入事件循环(不 exec), 仅构造后即释放。
"""

# 注意: 这里用 try/ImportError 而不是 pytest.importorskip —— `python -m unittest discover`
# 会把 importorskip 抛出的 Skipped 当成本模块导入失败 (ERROR), 从而报假失败。
import unittest

try:
    import PySide6  # noqa: F401
except ImportError as _exc:  # 无 GUI 环境 (CI / 无显示器)
    raise unittest.SkipTest(f"缺少 GUI 依赖: {_exc}") from _exc

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    _app = QApplication.instance() or QApplication([])
    yield _app


def test_main_pages_construct(app):
    from fitness_pkg.data_model import BodyDataModel
    from fitness_pkg.ui_pages import DashboardPage, TrendChartPage

    model = BodyDataModel()
    DashboardPage(model)
    TrendChartPage(model)


def test_training_plan_page_construct(app):
    from fitness_pkg.exercise_lib import ExerciseLibrary
    from fitness_pkg.parsers import TrainingPlanParser
    from fitness_pkg.ui_pages import TrainingPlanPage

    TrainingPlanPage(TrainingPlanParser(), ExerciseLibrary())


def test_nutrition_page_construct(app):
    from fitness_pkg.ui_pages import NutritionPage

    NutritionPage()


def test_exercise_library_page_construct(app):
    from fitness_pkg.exercise_lib import ExerciseLibrary
    from fitness_pkg.ui_pages import ExerciseLibraryPage

    ExerciseLibraryPage(ExerciseLibrary())


def test_ai_coach_page_construct(app):
    from fitness_pkg.ai_coach import AICoachPage

    AICoachPage()
