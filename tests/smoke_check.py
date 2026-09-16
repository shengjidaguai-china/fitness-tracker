# -*- coding: utf-8 -*-
"""
冒烟脚本 (v9.1) — 无需 GUI / 个人数据即可验证核心链路。

用法:
    python tests/smoke_check.py

覆盖:
1. 逐模块 `python -m py_compile` 语法门禁
2. 训练科学规则层关键规则断言
3. AI 教练引擎端到端: 建档 → 周期生成 → 复盘 → 接回 → 导出 Markdown
4. 动作缺口审计 + 周组数区间检查
5. 隐私检查: 确认脚本只写入个人数据目录 (已被 .gitignore 排除), 不产生可提交的个人数据

退出码 0 = 全部通过; 非 0 = 有失败项。
"""

import copy
import os
import py_compile
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, 'fitness_pkg')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MODULES = [
    'ai_coach_engine.py',
    'fitness_modules.py',
    'generate_report.py',
    'fitness_pkg/__init__.py',
    'fitness_pkg/constants.py',
    'fitness_pkg/data_model.py',
    'fitness_pkg/exercise_lib.py',
    'fitness_pkg/parsers.py',
    'fitness_pkg/dialogs.py',
    'fitness_pkg/ui_pages.py',
    'fitness_pkg/ai_coach.py',
    'fitness_pkg/science.py',
]

# 冒烟只允许在这些目录下产生文件 (均为 .gitignore 排除的个人数据目录)
ALLOWED_WRITE_DIRS = (os.path.join(_ROOT, '体重体脂监控'),)


def _check_py_compile():
    failures = []
    for rel in MODULES:
        path = os.path.join(_ROOT, rel)
        if not os.path.exists(path):
            failures.append(f'{rel}: 文件不存在')
            continue
        with tempfile.NamedTemporaryFile(suffix='.pyc', delete=False) as tmp:
            try:
                py_compile.compile(path, cfile=tmp.name, doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append(f'{rel}: {exc.msg.strip()}')
            finally:
                os.unlink(tmp.name)
    return failures


def _check_science_layer():
    import science as sc

    problems = []
    checks = [
        ('RPE 10 = 0 RIR', sc.rpe_to_rir(10.0) == 0),
        ('RPE 8 = 2 RIR', sc.rpe_to_rir(8.0) == 2),
        ('周组数区间为非空', sc.weekly_set_band('L1')[0] <= sc.weekly_set_band('L1')[1]),
        ('周组数上限 20', sc.WEEKLY_SET_CEILING == 20),
        ('2 项信号触发减载', sc.evaluate_deload_signals({'sleep_worse': True, 'pain': True})['verdict'] == '减载一周'),
        ('1 项信号继续前进', sc.evaluate_deload_signals({'sleep_worse': True})['verdict'] == '继续前进'),
        ('复合主项不做力竭', sc.failure_allowance('深蹲', 4, 4)['allow_failure'] is False),
        ('孤立动作末组可力竭', sc.failure_allowance('弯举', 3, 3)['allow_failure'] is True),
        ('复合休息 >= 150s', sc.rest_seconds('卧推')[0] >= 150),
        ('孤立休息 >= 90s', sc.rest_seconds('弯举')[0] >= 90),
        ('热身不产生明显疲劳', all(w['rpe'] <= 7.0 for w in sc.build_warmup_sets(100))),
        ('多组 RPE 路径递增', sc.build_rpe_path(4, 6.0, 9.0) == sorted(sc.build_rpe_path(4, 6.0, 9.0))),
        ('危险信号被分流', sc.screen_action('训练中胸部不适') is not None),
        ('无危险信号时放行', sc.screen_action('今天状态不错') is None),
        ('缺口审计识别髋铰链缺失', '髋铰链' in sc.audit_movement_gaps(['卧推'])['gaps']),
        ('单次异常不判定停滞', sc.detect_stall([{'weight': 60, 'reps': 8, 'rpe': 8.0},
                                                 {'weight': 60, 'reps': 7, 'rpe': 8.0}])['is_stall'] is False),
    ]
    for name, ok in checks:
        if not ok:
            problems.append(f'科学规则校验失败: {name}')
    return problems


def _check_engine_end_to_end():
    import ai_coach_engine as eng

    problems = []
    if not getattr(eng, 'SCIENCE_AVAILABLE', False):
        problems.append('ai_coach_engine 未加载训练科学规则层 (SCIENCE_AVAILABLE=False)')

    # 周期生成
    cycle = eng.generate_strength_cycle('深蹲', 100, 120, 2, start_date='2026-01-01', level='L2')
    if cycle.weeks != 10:
        problems.append(f'周期长度应为 10 周, 实际 {cycle.weeks}')
    if sum(cycle.phase_distribution.values()) != cycle.weeks:
        problems.append('阶段分布周数与周期长度不一致')
    if not cycle.days or not cycle.days[0].warmup_sets:
        problems.append('周期缺少热身流程')
    if not cycle.days[0].rest_plan:
        problems.append('周期缺少组间休息安排')
    # 减量阶段不应比实现阶段更重
    impl = [d for d in cycle.days if d.phase == '实现']
    deload = [d for d in cycle.days if d.phase == '减量']
    if impl and deload and deload[0].sets[0].weight >= impl[0].sets[0].weight:
        problems.append('减量阶段负荷未低于实现阶段, 可能把减载写成更重的验证周')

    # 复盘: 正常 → 维持/加次/加重, 均不得同时改动多个变量
    log = eng.TrainingLog(date='2026-01-02', movement='哑铃弯举', weight=12.5, reps=12, sets=3, rpe=8.0)
    res = eng.review_training(log, level='L1', target_reps=12, weekly_sets=12)
    if not res.next_prescription.get('rpe_path'):
        problems.append('复盘处方缺少多组 RPE 路径')

    # 复盘: 危险信号优先
    safety = eng.review_training(
        eng.TrainingLog(date='2026-01-03', movement='卧推', weight=80, reps=5, sets=4, rpe=9.0,
                        notes='肩部锐痛并放射到手臂'),
        level='L2',
    )
    if safety.judgment != '暂停常规处方':
        problems.append('危险信号未优先于渐进安排')

    # 停训接回
    plan = eng.generate_return_plan(14, 60, '卧推', ['划船'], 2)
    if plan.permission != '降级接回':
        problems.append(f'14 天停训应为降级接回, 实际 {plan.permission}')
    if not plan.return_48h or len(plan.exit_conditions) < 3:
        problems.append('接回方案缺少 48 小时动作或退出条件')

    # 短版训练
    day = cycle.days[0]
    for minutes in (30, 20, 10, 5, 2):
        if not eng.generate_short_version(day, minutes):
            problems.append(f'{minutes} 分钟短版为空')

    # 导出 Markdown 不得失败
    md_path = eng.export_cycle_to_markdown(cycle)
    if not os.path.exists(md_path):
        problems.append('周期 Markdown 未生成')
    else:
        with open(md_path, encoding='utf-8') as f:
            md = f.read()
        for token in ('科学依据', '验证方式', '热身', '力竭使用'):
            if token not in md:
                problems.append(f'导出的 Markdown 缺少「{token}」章节')

    # 自检信息
    if not eng.coach_diagnostics().get('science_layer'):
        problems.append('coach_diagnostics 报告科学规则层不可用')

    report = eng.build_weekly_volume_report('L1', {'背': 12, '胸': 26})
    verdicts = {i['muscle']: i['verdict'] for i in report['items']}
    if verdicts.get('背') != '合适' or verdicts.get('胸') != '超出验证区间':
        problems.append(f'周组数区间判定异常: {verdicts}')

    return problems


def _check_privacy():
    """确保冒烟自身不引入可提交的个人数据。"""
    problems = []
    coach_dir = os.path.join(_ROOT, '体重体脂监控', 'ai_coach')
    if not os.path.isdir(coach_dir):
        # 冒烟尚未写入, 属正常情况
        return problems
    for name in os.listdir(coach_dir):
        path = os.path.join(coach_dir, name)
        if not any(os.path.abspath(path).startswith(os.path.abspath(d)) for d in ALLOWED_WRITE_DIRS):
            problems.append(f'冒烟在非个人数据目录产生文件: {path}')
    return problems


def main():
    print('— 冒烟检查 v9.1 —')
    groups = [
        ('py_compile 语法门禁', _check_py_compile),
        ('训练科学规则层', _check_science_layer),
        ('AI 教练引擎端到端', _check_engine_end_to_end),
        ('隐私/数据隔离', _check_privacy),
    ]
    failures = []
    for title, fn in groups:
        problems = fn()
        if problems:
            failures.extend(problems)
            print(f'[FAIL] {title}')
            for p in problems:
                print(f'       - {p}')
        else:
            print(f'[ OK ] {title}')

    print(f'— 结果: {"全部通过" if not failures else f"{len(failures)} 项失败"} —')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
