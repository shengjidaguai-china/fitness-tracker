# -*- coding: utf-8 -*-
"""
冒烟检查 — 云端无 GUI 环境下可运行的最小校验

1) 对核心模块执行 py_compile
2) 导入 ai_coach_engine 并跑通周期生成/复盘/接回链路
3) 导入 fitness_pkg 纯逻辑模块 (data_model/parsers/exercise_lib)
4) 校验规则口径自洽 (减载周不重于实现周、危险信号优先于渐进)

用法: python tests/smoke_check.py
"""
import os
import py_compile
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

MODULES = [
    'ai_coach_engine.py',
    'fitness_modules.py',
    'fitness_pkg/__init__.py',
    'fitness_pkg/constants.py',
    'fitness_pkg/data_model.py',
    'fitness_pkg/exercise_lib.py',
    'fitness_pkg/parsers.py',
    'fitness_pkg/dialogs.py',
    'fitness_pkg/ui_pages.py',
    'fitness_pkg/ai_coach.py',
    'generate_report.py',
    '体脂体重监控_完整版.py',
]

failures = []


OPTIONAL_DEPS = ('numpy', 'pandas')


def step(name, fn):
    try:
        fn()
        print(f'  [OK] {name}')
    except ImportError as e:
        # 缺第三方依赖属环境问题, 不计入失败 (AI 教练规则层为纯标准库实现)
        print(f'  [SKIP] {name}: 缺少依赖 {e} (pip install numpy pandas 后可完整校验)')
    except Exception as e:  # noqa: BLE001
        failures.append(f'{name}: {e}')
        print(f'  [FAIL] {name}: {e}')


print('== 1. py_compile 全部核心模块 ==')


def _compile_all():
    for m in MODULES:
        py_compile.compile(os.path.join(ROOT, m), doraise=True, quiet=1)


step('py_compile 12 个模块', _compile_all)

print('== 2. AI 教练规则链路 ==')


def _engine_chain():
    import ai_coach_engine as eng
    cycle = eng.generate_strength_cycle('卧推', 100, 115, 2)
    assert cycle.days, '周期无训练日'
    assert cycle.deload_weeks, '缺少节律减载周'
    day = cycle.days[0]
    assert day.short_version_5 and day.short_version_2, '缺少 5/2 分钟短版'
    plan = eng.generate_return_plan(14, 100, '深蹲')
    assert plan.first_step_48h, '缺少 48 小时首步'
    log = eng.TrainingLog('2026-09-16', '卧推', 80, 8, 4, 7.5)
    res = eng.review_training(log)
    assert res.next_prescription.get('weight'), '缺少下一次处方'


step('周期/复盘/接回链路', _engine_chain)

print('== 3. 规则口径自洽 ==')


def _invariants():
    import ai_coach_engine as eng
    # 减载周不得重于任何实现周 (对 1/2/3 次暴露频率全覆盖)
    for exposures, sessions in ((1, 3), (2, 4), (3, 5)):
        cycle = eng.generate_strength_cycle('深蹲', 120, 140, exposures,
                                            sessions_per_week=sessions)
        deload = [d for d in cycle.days if d.week in cycle.deload_weeks]
        realiz = [d for d in cycle.days if d.phase == '实现']
        assert deload, f'暴露 {exposures} 次时缺少节律减载'
        assert realiz, f'暴露 {exposures} 次时缺少实现阶段'
        lightest_realiz = min(d.sets[0].weight for d in realiz)
        for d in deload:
            assert d.sets[0].weight < lightest_realiz, \
                f'减载周重于实现周 (暴露 {exposures} 次): {d.sets[0].weight} vs {lightest_realiz}'
    # 危险信号优先于渐进
    r = eng.review_training(eng.TrainingLog('2026-09-16', '卧推', 60, 8, 4, 7.5,
                                            pain=True, pain_desc='胸闷、晕厥前兆'))
    assert r.safety_hold and r.progression_type == '暂停', '危险信号未优先'
    # 复合动作禁止力竭
    assert not eng.allows_failure('深蹲', last_set=True)
    # 2 项信号触发减载
    r2 = eng.review_training(eng.TrainingLog('2026-09-16', '卧推', 80, 8, 4, 7.5,
                                             completed=False, abnormal_fatigue=True))
    assert r2.deload_recommended, '2 项信号未触发减载'


step('减载/安全/力竭/信号 4 项不变量', _invariants)

print('== 4. fitness_pkg 纯逻辑模块 ==')


def _pkg_import():
    from fitness_pkg.data_model import BodyDataModel
    from fitness_pkg.parsers import TrainingPlanParser
    from fitness_pkg.exercise_lib import ExerciseLibrary
    BodyDataModel().get_stats()
    TrainingPlanParser().get_daily_exercises(1)
    ExerciseLibrary()


step('data_model / parsers / exercise_lib', _pkg_import)

print()
if failures:
    print(f'[FAIL] {len(failures)} 项检查未通过:')
    for f in failures:
        print('  -', f)
    sys.exit(1)
print('[OK] 全部冒烟检查通过')
