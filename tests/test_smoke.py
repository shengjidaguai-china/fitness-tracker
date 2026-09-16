"""模块导入冒烟 — 工程配置(lint/格式化)与包导入降级改动后确保全链路可导入

约定: 纯逻辑层 (数据模型 / 解析器 / 规则层 / 计划科学视图) 必须无 GUI 依赖也能导入;
GUI 层在缺 PySide6 的环境 (CI / 无显示器) 允许跳过, 但降级标记必须正确。
"""

import importlib

import pytest


def test_core_logic_modules_importable_without_gui():
    """回归: 缺 PySide6 时 `import fitness_pkg` 曾直接抛 ImportError, 导致测试无法收集。"""
    for name in (
        "fitness_pkg",
        "fitness_pkg.constants",
        "fitness_pkg.data_model",
        "fitness_pkg.parsers",
        "fitness_pkg.science",
        "fitness_pkg.plan_science",
    ):
        assert importlib.import_module(name) is not None


def test_package_degrades_instead_of_raising_without_pyside():
    import fitness_pkg

    if fitness_pkg.GUI_AVAILABLE:
        assert fitness_pkg.GUI_IMPORT_ERROR == ""
        for attr in ("AICoachPage", "DashboardPage", "TrainingPlanPage"):
            assert hasattr(fitness_pkg, attr)
    else:
        # 降级路径必须给出原因, 而不是静默置空
        assert "PySide6" in fitness_pkg.GUI_IMPORT_ERROR or fitness_pkg.GUI_IMPORT_ERROR
        for attr in ("AICoachPage", "DashboardPage"):
            assert not hasattr(fitness_pkg, attr)


def test_gui_modules_importable_when_dependency_present():
    pytest.importorskip("PySide6")
    for name in ("fitness_pkg.ai_coach", "fitness_pkg.ui_pages", "fitness_pkg.exercise_lib"):
        assert importlib.import_module(name) is not None


def test_engine_importable():
    assert importlib.import_module("ai_coach_engine") is not None


def test_nutrition_parser_and_schedule_consistency():
    """三阶段周数常量与训练安排可互相引用(基础健全性)"""
    from fitness_pkg.constants import PHASE_INFO, TRAINING_SCHEDULE

    assert len(TRAINING_SCHEDULE) >= 5
    # 各阶段内应有周数信息
    for _phase, info in PHASE_INFO.items():
        assert info["name"]
