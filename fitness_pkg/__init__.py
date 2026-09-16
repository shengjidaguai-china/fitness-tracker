"""
fitness_pkg — 健身监控模块化包 (v7.0)
将原本单文件 fitness_modules.py 拆分为:
  constants.py   全局配置/常量/工具
  data_model.py  体测数据模型 BodyDataModel
  exercise_lib.py 动作库 ExerciseLibrary
  parsers.py     训练计划/营养方案解析器
  dialogs.py     动作详情弹窗
  ui_pages.py    5个UI页面
  ai_coach.py    AI 教练页面
"""

from .ai_coach import AI_COACH_AVAILABLE, AICoachPage
from .constants import (
    BODY_COLUMNS,
    COLORS,
    DATA_FILE,
    FLOW_TUTORIAL,
    MUSCLE_EMOJI,
    PHASE_INFO,
    TRAINING_SCHEDULE,
    VACUUM_TUTORIAL,
)
from .data_model import BodyDataModel
from .dialogs import ExerciseDetailDialog
from .exercise_lib import ExerciseLibrary
from .parsers import NutritionParser, TrainingPlanParser
from .ui_pages import (
    DashboardPage,
    ExerciseLibraryPage,
    NutritionPage,
    TrainingPlanPage,
    TrendChartPage,
)

__all__ = [
    "AI_COACH_AVAILABLE",
    "BODY_COLUMNS",
    "COLORS",
    "DATA_FILE",
    "FLOW_TUTORIAL",
    "MUSCLE_EMOJI",
    "PHASE_INFO",
    "TRAINING_SCHEDULE",
    "VACUUM_TUTORIAL",
    "AICoachPage",
    "BodyDataModel",
    "DashboardPage",
    "ExerciseDetailDialog",
    "ExerciseLibrary",
    "ExerciseLibraryPage",
    "NutritionPage",
    "NutritionParser",
    "TrainingPlanPage",
    "TrainingPlanParser",
    "TrendChartPage",
]
