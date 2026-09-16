# fitness-tracker LOG

> 最新在顶部。每条 ≤ 20 行，仅摘要 + 指针。

## 2026-09-16 规则层科学化第二轮 + 测试基建（Issue #1 追问「还有需要改进的地方吗」）
- 新增 `tests/smoke_check.py`（py_compile 12 模块 + 链路 + 4 项口径不变量）与 `tests/test_ai_coach_engine.py`、`tests/test_fitness_pkg.py`，共 39 项用例，缺 GUI 依赖自动跳过。
- 修正 `estimate_1rm`：RPE 描述余力(RIR)，原实现把当前次数当力竭次数；移除 RPE 加成，改为先换算力竭次数再套 Epley。
- 新增 `rpe_to_rir` 表（10≈0、9≈1、8≈2、7≈3，半档取保守侧）、`weekly_set_range`/`check_weekly_sets`、`is_compound`/`rest_seconds`/`allows_failure`。
- 周期生成：明示每周暴露次数、周组数区间与说明、逐组 RPE 路径、热身流程、日目的与技术检查点、节律减载周（保证减载周轻于任何实现周）、5/2 分钟短版。
- 复盘：疼痛/异常疲劳/动作失控输入；命中 2 项信号建议减载一周；危险信号（胸痛/晕厥/麻木/放射痛）直接暂停；单次异常不改结构，连续两次才怀疑周期。
- 接回：漏 1 次不补课 / 漏 2 次 30 分钟版；补 48 小时首步与升级-维持-暂停条件；57-84 天区间；成功标准改为「恢复自主判断」。
- 持久化：`_read_json` 编码探测 + `.bad` 备份，`_atomic_write_json` 原子写；建档缺/多字段不致崩溃。
- 打包：`.gitmodules` 移除不存在的 `BettaFish`（与 README 子模块表一致改为两个）；3 个 spec 收敛为「主 + 调试」；`build_exe.py` 补 `--icon`。
- README：结构树/模块名/脚本名与实际对齐，AI 教练章补规则层说明与校验命令，移除失效 Star History 图表。
- 验证：`python tests/smoke_check.py` 4 组通过；`python -m unittest discover -s tests` 39 项通过（10 项跳过：云端无 PySide6）。GUI 未动布局，仍需本地 Windows 目视确认。

## 2026-09-03 初始化 CNB 双轨 NPC 配置
- 克隆 GitHub `yuppiez99999/fitness-tracker` 到本地 `e:/各种PY程序/fitness-tracker`，生成 `.cnb.yml` + `.cnb/settings.yml`（照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。
- 目标 CNB 仓: `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例）。
- 补 `cairn/ROADMAP.md` + `cairn/LOG.md` 使自动接管可运行。
- 后续: 用户自行 commit & push（含 .cnb.yml / .cnb/settings.yml / cairn/）到 CNB 镜像，并在 cnb.cool 网页启用 NPC / 配置 crontab 触发。
