"""
fitness_pkg — 健身监控模块化包 (v7.0)
将原本单文件 fitness_modules.py 拆分为:
  constants.py   全局配置/常量/工具
  data_model.py  体测数据模型 BodyDataModel
  exercise_lib.py 动作库 ExerciseLibrary
  parsers.py     训练计划/营养方案解析器
  science.py     训练科学规则层 (无 GUI 依赖)
  plan_science.py 22 周计划的科学化视图 (无 GUI 依赖)
  dialogs.py     动作详情弹窗
  ui_pages.py    5个UI页面
  ai_coach.py    AI 教练页面
  auto_plan.py   输入驱动方案生成 (体测→训练计划, 预算→饮食与补剂)
  auto_plan_page.py 自动方案页面

导入约定 (v9.1 修正): 只有 GUI 子模块才需要 PySide6, 所以这里逐个软导入 ——
无显示器 / 未装 PySide6 的环境 (CI、CLI 脚本、纯逻辑测试) 仍能 `import fitness_pkg`,
并直接使用 data_model / parsers / science / plan_science。
缺失依赖的名字不会出现在本命名空间, 调用方以 `GUI_AVAILABLE` / `QT_GUI_AVAILABLE` 判断。
"""

from importlib.util import find_spec

from .auto_plan import (
    generate_diet_plan,
    generate_training_plan,
    validate_body_inputs,
    validate_budget,
)

# ── 无 GUI 依赖的子模块 (CI / CLI / 纯逻辑测试都会用到) ──
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
from .parsers import NutritionParser, TrainingPlanParser
from .plan_science import week_display_meta, weekly_volume_status
from .science import weekly_set_band

# ── 可选依赖探测: 缺 PySide6 时相关页面不导出, 但包本身照常可用 ──
QT_GUI_AVAILABLE = find_spec("PySide6") is not None

if QT_GUI_AVAILABLE:  # pragma: no cover - 依赖运行环境
    from .exercise_lib import ExerciseLibrary

try:  # pragma: no cover - 依赖运行环境
    from .ai_coach import AI_COACH_AVAILABLE, AICoachPage
    from .auto_plan_page import AutoPlanPage
    from .dialogs import ExerciseDetailDialog
    from .ui_pages import (
        DashboardPage,
        ExerciseLibraryPage,
        NutritionPage,
        TrainingPlanPage,
        TrendChartPage,
    )

    GUI_AVAILABLE = True
    GUI_IMPORT_ERROR = ""
except ImportError as exc:  # 缺可选依赖: 记录原因, 不阻断包导入
    GUI_AVAILABLE = False
    GUI_IMPORT_ERROR = str(exc)

__all__ = [
    "BODY_COLUMNS",
    "COLORS",
    "DATA_FILE",
    "FLOW_TUTORIAL",
    "GUI_AVAILABLE",
    "GUI_IMPORT_ERROR",
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
    "validate_body_inputs",
    "validate_budget",
    "week_display_meta",
    "weekly_set_band",
    "weekly_volume_status",
]

if QT_GUI_AVAILABLE:  # pragma: no cover - 依赖运行环境
    __all__ += ["ExerciseLibrary"]

if GUI_AVAILABLE:  # pragma: no cover - 依赖运行环境
    __all__ += [
        "AI_COACH_AVAILABLE",
        "AICoachPage",
        "AutoPlanPage",
        "DashboardPage",
        "ExerciseDetailDialog",
        "ExerciseLibraryPage",
        "NutritionPage",
        "TrainingPlanPage",
        "TrendChartPage",
    ]
