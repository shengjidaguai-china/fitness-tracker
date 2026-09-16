# fitness-tracker LOG

> 最新在顶部。每条 ≤ 20 行，仅摘要 + 指针。

## 2026-09-16 第三轮: 规则层接入 22 周计划视图 + 验证链路修复（Issue #1「继续」）
- 新增 `fitness_pkg/plan_science.py`（F9 规则层侧）: `parse_group_spec`（组次文本容错解析）、`muscle_bucket_of`、
  `estimate_muscle_sets` / `estimate_weekly_sets`、`weekly_volume_status`、`week_display_meta`、`deload_guidance`、
  `day_execution_note`、`plan_science_summary`。无 GUI 依赖, 纯函数, fail-open。
- 口径自律: 训练量统一按 Helms 的「组/周/肌群」计量。计划正文写的是「单次训练该动作做几组」——不是周组数,
  所以新增 `estimate_weekly_sets` 先把一周 7 天各自的动作表汇总, 与 10–20 起始区间比对的只有它;
  训练日为 0 (休息周/解析失败) 时 `weekly_volume_status` 返回「不判定」, 不误报「练得太少」。
- 减载: W8/W13/W17/W21, 组数保留 80%, 并在 `week_display_meta` 里写明「强度必须低于相邻实现周」。
- 修掉阻塞验证的三个问题（补测试时才暴露出来的）:
  1. `import fitness_pkg` 曾硬依赖 PySide6 → `tests/test_data_model.py` / `test_parsers.py` 在云端无法**收集**,
     等于这两组用例一直没在跑。改为软导入: 缺依赖时 GUI 名字不出现在命名空间, `GUI_AVAILABLE` /
     `GUI_IMPORT_ERROR` / `QT_GUI_AVAILABLE` 给出降级标记; `fitness_modules` 兼容层同步。
  2. `unittest discover` 对 UI 用例报假失败: `pytest.importorskip` 抛出的 Skipped 被 unittest 当成本模块导入 ERROR。
     改用 `raise unittest.SkipTest(...)`。结果: `unittest discover` 从「2 error」变成 OK。
  3. `data_model.predict_target_date` 在新格式 CSV 下 `np.polyfit` 崩: 数值列可能是 object dtype →
     `Cannot cast ufunc 'lstsq' input 1 from dtype('O') to dtype('float64')`。现在显式 `astype(float)` +
     未知列返回 None, 不再抛异常。
- 测试 141 → 152 项（新增 39 项 `tests/test_plan_science.py`，另修 2 项 UI 假失败）；`ruff check` 与
  `ruff format --check` 全绿（顺手清掉 master 遗留的 8 项 lint: UTF-8 声明 / 未用 noqa / 未用循环变量）；
  冒烟 4 组通过。README 里写死的用例数改为由采集结果给出, 不再手写数字。
- 未动 GUI 布局；`plan_science` 的文案尚未接到训练计划页（剩余 F9 GUI 侧）。

## 2026-09-16 规则层科学化第二轮 + 测试基建（Issue #1 追问「还有需要改进的地方吗」）
- 修正 `estimate_1rm`：RPE 描述余力(RIR)，原实现把当前次数当力竭次数；改为统一走规则层 `e1rm_from_set` 口径，与负荷换算互为逆运算。
- 规则层 `fitness_pkg/science.py` 保留为唯一来源；`ai_coach_engine.py` 不再重复实现同一套规则（避免两套口径打架）。
- `rpe_to_rir` 表（10≈0、9≈1、8≈2、7≈3，半档取保守侧）、`weekly_set_range`/`check_weekly_sets`、`is_compound`/`rest_seconds`/`allows_failure`。
- 周期生成：明示每周暴露次数、周组数区间说明、逐组 RPE 路径、热身流程、日目的与技术检查点、节律减载周（不变量：减载周必须轻于任何实现周）、5/2 分钟短版。
- 复盘：疼痛/异常疲劳/动作失控输入；命中 2 项信号建议减载一周；危险信号（胸痛/晕厥/麻木/放射痛）直接暂停；单次异常不改结构，连续两次才怀疑周期。
- 接回：漏 1 次不补课 / 漏 2 次 30 分钟版；48 小时首步 + 升级/维持/暂停条件；>56 天暂停并重新建档。
- 持久化：`_read_json` 编码探测 + `.bad` 备份，`_atomic_write_json` 原子写；建档缺字段/多字段不再崩溃。
- 打包：`.gitmodules` 移除不存在的 `BettaFish`；3 个 spec 收敛为「主 + 调试」两套；`build_exe.py` 补 `--icon`。
- README：结构树/模块名/脚本名与实际对齐，AI 教练章补规则层说明与校验命令，移除失效 Star History 图表。
- 验证：`python tests/smoke_check.py` 4 组通过；`python -m pytest tests` 通过（AI 引擎/规则层/数据层，UI 用例云端自动跳过）。GUI 未动布局，仍需本地 Windows 目视确认。
- 冲突收口：master 先合并了 PR #2，又推进到 v10.x（ruff + pre-commit + pytest + 架构图）。本分支两次合并 master，冲突文件按「科学版口径 + 规则层实现」合并，并按 `pyproject.toml` 的 ruff 配置（target py38 / quote-style double）统一格式，`ruff check` 全绿。

## 2026-09-03 初始化 CNB 双轨 NPC 配置
- 克隆 GitHub `yuppiez99999/fitness-tracker` 到本地 `e:/各种PY程序/fitness-tracker`，生成 `.cnb.yml` + `.cnb/settings.yml`（照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。
- 目标 CNB 仓: `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例）。
- 补 `cairn/ROADMAP.md` + `cairn/LOG.md` 使自动接管可运行。
- 后续: 用户自行 commit & push（含 .cnb.yml / .cnb/settings.yml / cairn/）到 CNB 镜像，并在 cnb.cool 网页启用 NPC / 配置 crontab 触发。
