# fitness-tracker (健身监控 v9.0) 路线图

> 本文件为 CNB 双轨 NPC 自动开发的排期事实源。roadmap-dev 角色每日读取顶部「最新状态同步」与「当前焦点」推进开发。
> 若此文件不存在，NPC 会回退读取 README.md 与仓库 Issues。

## 最新状态同步
- 2026-09-16: 规则层「科学化」第二轮（Issue #1，PR #3）。新增 `tests/`（冒烟 + 91 项单元测试）；修正 e1RM 余力口径；补周期/频率/周组数自检、逐组 RPE 路径、热身与检查点、节律减载周、RPE 触发的减载信号、危险信号暂停、48 小时接回首步、5/2 分钟短版；持久化改为原子写 + 编码探测 + 损坏备份；收敛 3 个 PyInstaller spec 为「主 + 调试」两套；README 结构与实际代码对齐（移除失效 Star History、修正文件名/结构描述）。
- 2026-09-16: PR #2（F5 训练科学规则层）已合并入 master（`fitness_pkg/science.py` + 引擎/GUI 接入）。
- 2026-09-03: 初始化 CNB 双轨配置（.cnb.yml + .cnb/settings.yml 照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。仓库当前为 v9.0，主程序 `体脂体重监控_完整版.py`，核心模块 `fitness_pkg/` + `ai_coach_engine.py`。目标 CNB 仓 `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例；GitHub 源为 yuppiez99999/fitness-tracker）。

## 当前焦点
- 稳定化与测试: `fitness_pkg/science.py` 与 `ai_coach_engine.py` 的口径已统一并有 91 项测试；下一步为 `parsers.py` / `data_model.py` 补更完整用例（现有 `tests/test_fitness_pkg.py` 为骨架）
- AI 教练增强: 规则层已接入周期/复盘/接回/短版；下一步接入 22 周训练计划页与报告输出
- 打包优化: PyInstaller spec 已收敛为「主 + 调试」两套，下一步做体积优化

## 待办 / 排期项（建议编号 Fx.x）
- ~~F1: 为 fitness_pkg 模块补单元测试骨架 + 一个冒烟脚本~~ → 已完成（`tests/smoke_check.py` + `tests/test_*.py`，91 项）
- F2: ai_coach 周期生成的可配置化（当前部分参数硬编码）—— 部分完成（周组数/频率/减载已可配）
- F3: generate_report.py 的报告健壮性与本地数据隔离校验
- F4: 引入 ruff 基础门禁（当前仅有 py_compile + unittest）
- ~~F5: 训练科学规则层~~ → 已完成并合并（PR #2，`fitness_pkg/science.py`）
- ~~F6: 规则层接入周期/复盘/接回/短版~~ → 已完成（PR #2 引擎接入 + PR #3 口径统一）
- F7: 为 `fitness_pkg/parsers.py` / `data_model.py` 补更完整的单元测试
- F8: GUI 冒烟验证脚本化（无显示器环境下用 QTest 或离屏平台跑通 6 个页面的构造）
- F9: AI 教练规则层接入 22 周训练计划页（把 RPE 路径/减载周写进周计划展示）

## 开放问题
- 是否引入 ruff/mypy 作为门禁（当前仅有 py_compile 基础校验）
- 子模块 (Lzheng-fitness / exercises-dataset) 的版本钉定策略
- 云端无 GUI，GUI 改动如何做冒烟验证（建议本地 Windows + 截图，或用 `QT_QPA_PLATFORM=offscreen`）
- AI 教练的「可比记录」判定目前仅用同动作最近一条，是否需要器械/动作标准字段
- 周组数区间按「10-20 组/训练日」推导，全身 vs 分化训练是否需要不同口径
