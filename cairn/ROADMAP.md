# fitness-tracker (健身监控 v9.0) 路线图

> 本文件为 CNB 双轨 NPC 自动开发的排期事实源。roadmap-dev 角色每日读取顶部「最新状态同步」与「当前焦点」推进开发。
> 若此文件不存在，NPC 会回退读取 README.md 与仓库 Issues。

## 最新状态同步
- 2026-09-03: 初始化 CNB 双轨配置（.cnb.yml + .cnb/settings.yml 照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。仓库当前为 v9.0，主程序 `体脂体重监控_完整版.py`，核心模块 `fitness_pkg/` + `ai_coach_engine.py`。目标 CNB 仓 `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例；GitHub 源为 yuppiez99999/fitness-tracker）。

## 当前焦点
- 稳定化与测试: 为 `fitness_pkg/` 各模块补充 `python -m py_compile` 冒烟与基本单元测试
- AI 教练增强: `ai_coach_engine.py` / `fitness_pkg/ai_coach.py` 的周期化与训练复盘逻辑打磨
- 打包优化: `健身监控.spec` 的 PyInstaller 配置清理与体积优化

## 待办 / 排期项（建议编号 Fx.x）
- F1: 为 fitness_pkg 模块补单元测试骨架 + 一个冒烟脚本
- F2: ai_coach 周期生成的可配置化（当前部分参数硬编码）
- F3: generate_report.py 的报告健壮性与本地数据隔离校验
- F4: 引入 ruff 基础门禁（当前仅有 py_compile）

## 开放问题
- 是否引入 ruff/mypy 作为门禁（当前仅有 py_compile 基础校验）
- 子模块 (Lzheng-fitness / exercises-dataset / BettaFish) 的版本钉定策略
- 云端无 GUI，GUI 改动如何做冒烟验证（建议本地 Windows + 截图）
