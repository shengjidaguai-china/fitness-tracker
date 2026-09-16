"""
fitness_modules — v7.0 模块化兼容层 (Compatibility Shim)
原单文件实现已拆分到 fitness_pkg/ 包。本文件仅做 re-export,
保证现有调用方 (体脂体重监控_完整版.py 等) 无需改动即可继续工作。

如需直接引用, 推荐改为:  from fitness_pkg import BodyDataModel, ...
"""

import matplotlib

matplotlib.use("QtAgg")  # 必须在导入 pyplot 之前设置后端 (原 fitness_modules.py 顶部设置)

from fitness_pkg import (
    AI_COACH_AVAILABLE,
    BODY_COLUMNS,
    COLORS,
    DATA_FILE,
    FLOW_TUTORIAL,
    MUSCLE_EMOJI,
    PHASE_INFO,
    TRAINING_SCHEDULE,
    VACUUM_TUTORIAL,
    AICoachPage,
    BodyDataModel,
    DashboardPage,
    ExerciseDetailDialog,
    ExerciseLibrary,
    ExerciseLibraryPage,
    NutritionPage,
    NutritionParser,
    TrainingPlanPage,
    TrainingPlanParser,
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
