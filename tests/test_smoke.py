"""模块导入冒烟 — 工程配置(lint/格式化)改动后确保全链路模块可导入"""


def test_all_core_modules_importable():
    import ai_coach_engine  # noqa: F401
    import fitness_pkg
    import fitness_pkg.ai_coach
    import fitness_pkg.data_model
    import fitness_pkg.exercise_lib
    import fitness_pkg.parsers  # noqa: F401


def test_nutrition_parser_and_schedule_consistency():
    """三阶段周数常量与训练安排可互相引用(基础健全性)"""
    from fitness_pkg.constants import PHASE_INFO, TRAINING_SCHEDULE

    assert len(TRAINING_SCHEDULE) >= 5
    # 各阶段内应有周数信息
    for _phase, info in PHASE_INFO.items():
        assert info["name"]
