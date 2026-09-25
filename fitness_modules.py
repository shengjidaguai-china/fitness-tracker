"""
fitness_modules — v7.0 模块化兼容层 (Compatibility Shim)
原单文件实现已拆分到 fitness_pkg/ 包。本文件仅做 re-export,
保证现有调用方 (体脂体重监控_完整版.py 等) 无需改动即可继续工作。

如需直接引用, 推荐改为:  from fitness_pkg import BodyDataModel, ...

v9.1: 纯逻辑层 (数据模型 / 解析器 / 规则层) 不再要求安装 PySide6, 因此分开导出 ——
缺 GUI 依赖时 GUI 名字不会出现在本命名空间, 调用方用 `GUI_AVAILABLE` 判断
(主程序启动本来就依赖 PySide6)。
"""

import matplotlib

matplotlib.use("QtAgg")  # 必须在导入 pyplot 之前设置后端 (原 fitness_modules.py 顶部设置)

from fitness_pkg import (
    BODY_COLUMNS,
    COLORS,
    DATA_FILE,
    FLOW_TUTORIAL,
    GUI_AVAILABLE,
    MUSCLE_EMOJI,
    PHASE_INFO,
    QT_GUI_AVAILABLE,
    TRAINING_SCHEDULE,
    VACUUM_TUTORIAL,
    BodyDataModel,
    NutritionParser,
    TrainingPlanParser,
    generate_diet_plan,
    generate_training_plan,
)

if QT_GUI_AVAILABLE:
    from fitness_pkg import ExerciseLibrary  # noqa: F401  (兼容层对外导出)

if GUI_AVAILABLE:
    from fitness_pkg import (
        AI_COACH_AVAILABLE,
        AICoachPage,
        AutoPlanPage,
        DashboardPage,
        ExerciseDetailDialog,
        ExerciseLibraryPage,
        NutritionPage,
        TrainingPlanPage,
        TrendChartPage,
    )
else:  # pragma: no cover - 依赖运行环境
    AI_COACH_AVAILABLE = False

__all__ = [
    "AI_COACH_AVAILABLE",
    "BODY_COLUMNS",
    "COLORS",
    "DATA_FILE",
    "FLOW_TUTORIAL",
    "GUI_AVAILABLE",
    "MUSCLE_EMOJI",
    "PHASE_INFO",
    "QT_GUI_AVAILABLE",
    "TRAINING_SCHEDULE",
    "VACUUM_TUTORIAL",
    "BodyDataModel",
    "NutritionParser",
    "TrainingPlanParser",
    "generate_diet_plan",
    "generate_training_plan",
]

if QT_GUI_AVAILABLE:
    __all__.append("ExerciseLibrary")

if GUI_AVAILABLE:
    __all__ += [
        "AICoachPage",
        "AutoPlanPage",
        "DashboardPage",
        "ExerciseDetailDialog",
        "ExerciseLibraryPage",
        "NutritionPage",
        "TrainingPlanPage",
        "TrendChartPage",
    ]
