# fitness-tracker LOG

> 最新在顶部。每条 ≤ 20 行，仅摘要 + 指针。

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
- 验证：`python tests/smoke_check.py` 4 组通过；`python -m unittest discover -s tests` **91 项通过**（10 项跳过：云端无 PySide6）。GUI 未动布局，仍需本地 Windows 目视确认。
- 冲突收口：PR #2 的实现先合并进 master，本分支（PR #3）改为「科学版口径 + 规则层实现」的合并版，新 commit 合并 master 并解决 6 个文件冲突。

## 2026-09-03 初始化 CNB 双轨 NPC 配置
- 克隆 GitHub `yuppiez99999/fitness-tracker` 到本地 `e:/各种PY程序/fitness-tracker`，生成 `.cnb.yml` + `.cnb/settings.yml`（照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。
- 目标 CNB 仓: `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例）。
- 补 `cairn/ROADMAP.md` + `cairn/LOG.md` 使自动接管可运行。
- 后续: 用户自行 commit & push（含 .cnb.yml / .cnb/settings.yml / cairn/）到 CNB 镜像，并在 cnb.cool 网页启用 NPC / 配置 crontab 触发。
