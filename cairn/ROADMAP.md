# fitness-tracker (健身监控 v9.0) 路线图

> 本文件为 CNB 双轨 NPC 自动开发的排期事实源。roadmap-dev 角色每日读取顶部「最新状态同步」与「当前焦点」推进开发。
> 若此文件不存在，NPC 会回退读取 README.md 与仓库 Issues。

## 最新状态同步
- 2026-09-25 (第五轮, Issue #5): 新增 Windows 发版流水线 `.cnb.yml` → `$ / tag_push / windows-exe-release` —— 推送 Tag 自动打包 exe 并归档到 Release 附件。调度到根组织自托管 Windows 构建机 (`runner.namespace: group` + `tags: [windows, win-x64]`, 平台官方节点只有 Linux), 复用仓库既有 `健身监控v9.0.spec` 保证与本地打包一致; 新增 `requirements-build.txt` 统一打包依赖。**前置条件**: 根组织需已接入 Windows 构建节点 (标签含 `windows`), 未接入时该流水线会直接失败。README 下载指引从 GitHub Releases 修正到本仓 Releases (`https://cnb.cool/yuppiez328/fitness-tracker/-/releases`), 顶部徽章/clone 地址/授权联系方式/BibTeX 一并指向本仓。护栏: `.cnb.yml` 通过 cnb-pipeline 校验器 (语法/语义/Schema) 三关全绿; 真机发包需待 Windows 节点接入后推 tag 实测。
- 2026-09-25 (第四轮, Issue #5): 新增 `fitness_pkg/auto_plan.py` —— **输入驱动方案生成**。体测输入 (当前/目标体重体脂) → 训练计划 + 每日训练动作 (方向/周期/P0–L3 等级/每周分化/组×次×RPE); 月度伙食费预算 → 每日饮食计划 (热量+宏量+六餐份量+采购参考) + 补剂方案 (剂量上限与禁忌 + 红线不碰项)。速度上限 (减脂 1%/周、增肌 0.25%/周) 与周组数区间全部走既有规则层, 视图层不另算。新增 GUI 页「🧭 自动方案」与 CLI `auto_plan.py` (同源, 不读写个人数据)。补测试时修掉两个真 bug: 目标体重被推算值覆盖导致方向反转、餐次份量按单价反推出读不通的标签。护栏: 测试 162→223 项全通过, `ruff check` 与 `ruff format --check` 全绿, 冒烟 4 组通过。
- 2026-09-16 (第三轮, Issue #1): 新增 `fitness_pkg/plan_science.py` —— 把规则层接到 22 周计划视图 (F9)。原来的组次解析只在 GUI 详情弹窗里有, 现在有了可测试的纯逻辑层: `parse_group_spec` / `muscle_bucket_of` / `estimate_weekly_sets` / `weekly_volume_status` / `week_display_meta` / `deload_guidance`。**只按 Helms 的「组/周/肌群」下结论**: 周计划正文写的是「单次训练该动作做几组」, 不是周组数, 所以解析到几个训练日就除以几, 休息周直接返回「不判定」而不是误报「练得太少」。同时修掉阻塞验证的三个工程问题: `import fitness_pkg` 不再强依赖 PySide6 (缺依赖时降级并在 `GUI_AVAILABLE`/`GUI_IMPORT_ERROR` 里给原因)、`unittest discover` 不再对 UI 用例报假失败、`data_model.predict_target_date` 的 numpy object dtype 崩溃。护栏: 测试 141→152 项全通过 (含 39 项新用例), `ruff check` 与 `ruff format --check` 全绿, 冒烟 4 组通过; 补测试后计数说明改为「测试用例数由采集结果给出, 不再写死数字」, 防止文档再次漂移。
- 2026-09-16: 规则层「科学化」第二轮（Issue #1，PR #3）。新增 `tests/`（冒烟 + 引擎/规则层/数据层用例）；修正 e1RM 余力口径；补周期/频率/周组数自检、逐组 RPE 路径、热身与检查点、节律减载周、RPE 触发的减载信号、危险信号暂停、48 小时接回首步、5/2 分钟短版；持久化改为原子写 + 编码探测 + 损坏备份；收敛 3 个 PyInstaller spec 为「主 + 调试」两套；README 结构与实际代码对齐（移除失效 Star History、修正文件名/结构描述）。
- 2026-09-16: PR #2（F5 训练科学规则层）已合并入 master（`fitness_pkg/science.py` + 引擎/GUI 接入）。
- 2026-09-03: 初始化 CNB 双轨配置（.cnb.yml + .cnb/settings.yml 照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。仓库当前为 v9.0，主程序 `体脂体重监控_完整版.py`，核心模块 `fitness_pkg/` + `ai_coach_engine.py`。目标 CNB 仓 `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例；GitHub 源为 yuppiez99999/fitness-tracker）。

## 当前焦点
- 自动方案: 规则链路已打通 (体测→计划, 预算→饮食+补剂) 并有 61 项用例; 下一步把方案接入 `generate_report.py` 报告输出, 并让减载周的饮食随训练量联动
- 稳定化与测试: `fitness_pkg/science.py` / `plan_science.py` 与 `ai_coach_engine.py` 的口径已统一并有用例覆盖；`parsers.py` / `data_model.py` 用例已补齐（含 GBK 回退、原子写、缓存不污染、未知列容错）。下一步：把 `generate_report.py` 纳入测试（F3）
- AI 教练增强: 规则层已接入周期/复盘/接回/短版 + 22 周计划视图；下一步把科学化视图接到 GUI 训练计划页与报告输出
- 打包优化: PyInstaller spec 已收敛为「主 + 调试」两套，下一步做体积优化

## 待办 / 排期项（建议编号 Fx.x）
- ~~F1: 为 fitness_pkg 模块补单元测试骨架 + 一个冒烟脚本~~ → 已完成（`tests/smoke_check.py` + `tests/test_*.py`，pytest/unittest 双跑）
- F2: ai_coach 周期生成的可配置化（当前部分参数硬编码）—— 部分完成（周组数/频率/减载已可配）
- F3: generate_report.py 的报告健壮性与本地数据隔离校验
- ~~F4: 引入 ruff 基础门禁~~ → 已完成（master 已接入 ruff + pre-commit + pytest）
- ~~F5: 训练科学规则层~~ → 已完成并合并（PR #2，`fitness_pkg/science.py`）
- ~~F6: 规则层接入周期/复盘/接回/短版~~ → 已完成（PR #2 引擎接入 + PR #3 口径统一）
- ~~F7: 为 `fitness_pkg/parsers.py` / `data_model.py` 补更完整的单元测试~~ → 已完成（`tests/test_parsers.py` / `test_data_model.py` 补齐并在 CI 可跑，顺带修掉包导入强依赖 PySide6 与 numpy dtype 崩溃）
- F8: GUI 冒烟验证脚本化（无显示器环境下用 QTest 或离屏平台跑通 6 个页面的构造；现有 `tests/test_ui_construct.py` 已覆盖构造，但云端缺 PySide6 仍跳过）
- ~~F9: AI 教练规则层接入 22 周训练计划页~~ → 规则层侧已完成（`fitness_pkg/plan_science.py` + 39 项用例）；剩余：把 `plan_science` 的文案接到 GUI 训练计划页展示
- F10: `generate_report.py` 的健壮性与本地数据隔离校验纳入测试（原 F3 的具体化）
- ~~F11: 输入驱动方案生成（体测→训练计划+动作, 预算→饮食+补剂）~~ → 已完成（`fitness_pkg/auto_plan.py` + GUI 页 + CLI + 61 项用例）
- F12: 自动方案接入报告输出与减载-饮食联动
- ~~F13: Windows 发版流水线 (推 tag 自动打包 exe 并归档) + README 下载指引修正~~ → 已完成 (`$ / tag_push / windows-exe-release` + `requirements-build.txt`; README 已指向本仓 Releases); **遗留**: 根组织自托管 Windows 构建节点接入后需推 tag 实测一次
- F14: 为 exe 产物加校验与版本信息 (Release 附件附 SHA256; exe 版本号从 tag 注入, 不再硬编码 v9.0)

## 开放问题
- Windows 构建节点是否接入 (未接入时 `windows-exe-release` 流水线无可用节点, 推送 tag 会失败)
- 是否引入 ruff/mypy 作为门禁（当前仅有 py_compile 基础校验）
- 子模块 (Lzheng-fitness / exercises-dataset) 的版本钉定策略
- 云端无 GUI，GUI 改动如何做冒烟验证（建议本地 Windows + 截图，或用 `QT_QPA_PLATFORM=offscreen`）
- AI 教练的「可比记录」判定目前仅用同动作最近一条，是否需要器械/动作标准字段
- 周组数区间按「10-20 组/训练日」推导，全身 vs 分化训练是否需要不同口径
