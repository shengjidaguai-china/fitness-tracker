# fitness-tracker (健身监控 v9.0) 路线图

> 本文件为 CNB 双轨 NPC 自动开发的排期事实源。roadmap-dev 角色每日读取顶部「最新状态同步」与「当前焦点」推进开发。
> 若此文件不存在，NPC 会回退读取 README.md 与仓库 Issues。

## 最新状态同步
- 2026-09-04: 完成 F5「训练科学性升级」(PR 待评审)。新增 `fitness_pkg/science.py` 训练科学规则层，
  把 Lzheng-fitness 知识库 (Helms/Schoenfeld/Nuckols/DanJohn) 的判断规则收敛为可配置、可测试的参数；
  AI 教练引擎与 GUI 页面全部接入。新增 `tests/test_science.py` (49 项) + `tests/smoke_check.py` 冒烟。
- 2026-09-03: 初始化 CNB 双轨配置（.cnb.yml + .cnb/settings.yml 照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。仓库当前为 v9.0，主程序 `体脂体重监控_完整版.py`，核心模块 `fitness_pkg/` + `ai_coach_engine.py`。目标 CNB 仓 `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例；GitHub 源为 yuppiez99999/fitness-tracker）。

## 当前焦点
- 稳定化与测试: `fitness_pkg/science.py` 已带单元测试; 下一步为 `parsers.py` / `data_model.py` 补测试
- AI 教练增强: 科学性升级已完成 (F5); 下一步把科学规则层接入 22 周训练计划页与报告输出
- 打包优化: `健身监控.spec` 的 PyInstaller 配置清理与体积优化

## 待办 / 排期项（建议编号 Fx.x）
- F1: 为 fitness_pkg 模块补单元测试骨架 + 一个冒烟脚本
- F2: ai_coach 周期生成的可配置化（当前部分参数硬编码）
- F3: generate_report.py 的报告健壮性与本地数据隔离校验
- F4: 引入 ruff 基础门禁（当前仅有 py_compile + unittest）
- F5: 训练科学性升级 — 已完成（2026-09-04，见下方「F5 交付清单」）
- F6: 把科学规则层接入 22 周训练计划页与 `generate_report.py` 报告输出
- F7: 为 `fitness_pkg/parsers.py` / `data_model.py` 补单元测试

## 开放问题
- 是否引入 ruff/mypy 作为门禁（当前仅有 py_compile 基础校验）
- 子模块 (Lzheng-fitness / exercises-dataset / BettaFish) 的版本钉定策略
- 云端无 GUI，GUI 改动如何做冒烟验证（建议本地 Windows + 截图）


## F5 交付清单（训练科学性升级，2026-09-04）

对应 Issue: 「扫描 GitHub 相关仓库 优化本项目 让健身方案更科学有效 循序渐进打造身材」

### 扫描结论
- GitHub 关联仓库共 3 个：`Lzheng-fitness`(已集成知识库) / `exercises-dataset`(已集成动作数据集) / `BettaFish`(舆情，与训练无关)
- 真正可提升「科学性」的知识来源是 `Lzheng-fitness/knowledge/` 与
  `lzheng-training-expert-library` 六位专家模块；本次直接把这些规则代码化

### 改动的科学性缺口 → 对策
| 原实现的缺口 | 对策 | 对应文件 |
|:---|:---|:---|
| e1RM 把「保留次数」当力竭次数，系统性高估 | 改为 RPE/RIR 折减口径，与强度百分比互逆 | `science.py` `e1rm_from_set` |
| 未校验周组数，容易越练越多 | 引入 P0–L3 分层的 10–20 组起始区间与 20 组上限校验 | `science.py` `analyze_weekly_volume` |
| 周期只有单一静态 RPE | 增加逐组 RPE 路径（首组→末组）+ 热身流程 | `science.py` `build_rpe_path` `build_warmup_sets` |
| 未区分复合/孤立动作 | 按动作类型给出休息下限、力竭策略、渐进方式 | `science.py` `classify_movement` `failure_allowance` |
| 周期内负荷只增不减 | 减量阶段封顶强度，避免把减载写成「更重的验证周」 | `ai_coach_engine.py` `generate_strength_cycle` |
| 复盘只按单次 RPE 判定 | 增加自动调节、反应式减载清单、停滞/平台检测、安全分流 | `science.py` `review_session` |
| 接回只有 7 天安排 | 增加 48 小时接回动作 + 升级/维持/暂停条件 + 多动作支持 | `ai_coach_engine.py` `generate_return_plan` |
| 短版只有 30/20/10 分钟 | 增加 5/2 分钟档 + 保留/舍弃规则 | `ai_coach_engine.py` `generate_short_plan` |
| 无自动化验证 | 49 项单元测试 + 端到端冒烟脚本 | `tests/` |

### 验证结果
```bash
python tests/smoke_check.py          # 4 组检查全部通过
python -m unittest discover -s tests # 49 tests OK
```

### 未做 / 待确认
- 未改动任何个人数据目录、LICENSE、子模块
- GUI 改动仅新增控件与文案，未改布局契约；建议在本地 Windows 做一次界面冒烟并截图
- `science.py` 的负荷估算仍需真实训练记录校准（RPE 校准训练）
