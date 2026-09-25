# fitness-tracker LOG

> 最新在顶部。每条 ≤ 20 行，仅摘要 + 指针。

## 2026-09-25 第五轮: Windows 发版流水线 + README 下载指引修正（Issue #5）
- `.cnb.yml` 新增 `$ / tag_push / windows-exe-release` 流水线: 推送 tag 自动打包 exe 并归档。
  4 个 stage: `pip install -r requirements-build.txt` → `PyInstaller 健身监控v9.0.spec` (复用仓库既有 spec,
  避免本地与 CI 两套打包参数漂移) → 校验 exe 存在 → `Compress-Archive` 打 zip
  (`健身监控-<tag>-windows-x64.zip`) → `git:release` 发 Release → `cnbcool/attachments` 把 zip 传为 Release
  附件 (页面内可下载)。
- **调度到自托管 Windows 构建机**: `runner.namespace: group` + `tags: [windows, win-x64]`。
  平台官方节点只有 amd64/arm64 Linux, 打不出 Windows exe; 因此本条流水线依赖根组织已接入 Windows 节点,
  没命中节点时直接失败 (不静默回退 Linux 产出无效产物)。前置条件与标签约定写进了 `.cnb.yml` 注释。
- **如实提示**: CNB 制品库页面里的制品都是包管理器/OCI 类型 (Docker/Helm/npm/PyPI 等), 没有「通用文件
  zip」这一类; exe 的公开交付出口是 Release 附件 (所需 token 仅是临时票据, 且公开仓可直接下载)。
  zip 同时留在构建工作区, 构件页可下载留档。README 也按这个口径写。
- 新增 `requirements-build.txt`: 打包依赖清单, 本地与 CI 共用。
- README 下载指引修正: 「方式一·免安装运行」改为本仓 Releases
  (`https://cnb.cool/yuppiez328/fitness-tracker/-/releases`), 并写明附件命名与来源; 顶部 Version 徽章、
  clone 地址、商业授权联系方式、BibTeX url 一并从 GitHub 指向本仓; 另补「推 tag 让流水线打包」的说明。
  子模块地址 (Lzheng-fitness / exercises-dataset) 保持 GitHub, 那是真实上游, 未改。
- 护栏: `.cnb.yml` 通过 cnb-pipeline 校验器三关 (YAML 语法 / 语义 / Schema) 全绿。
  流水线真机验证需等根组织 Windows 构建节点接入后推 tag 实测。

## 2026-09-25 第四轮: 输入驱动方案生成（Issue #5）
- 新增 `fitness_pkg/auto_plan.py`（纯逻辑, 无 GUI/无 numpy/pandas 依赖）: 体测输入 → 训练计划 + 每日动作;
  月度伙食费 → 每日饮食 + 补剂。`validate_body_inputs` / `validate_budget` / `body_composition_plan` /
  `infer_level` / `generate_training_plan` / `generate_training_markdown` / `plan_energy` / `scale_meals` /
  `budget_plan` / `generate_diet_plan` / `suggest_supplements` / `generate_diet_markdown`。
- 口径自律: 组数区间/减载/温差判断全部调 `science` 与 `plan_science`, 视图层不另算一套。周组数结论来自
  `weekly_volume_status`, 减载周沿用 W8/W13/W17/W21 且组数与 RPE 同步下调 (不变量已写进用例)。
- 安全约束写进代码: 减脂周速度上限 1% 体重、增肌 0.25%; 目标再激进只延长周期 (`weeks` 收敛到 4 的倍数),
  不加大缺口。体脂接近必需脂肪 (男 ≤5%/女 ≤12%) 直接提示不建议继续减脂。
- 补剂侧只保留乳清/肌酸/维D3/鱼油/镁/锌, 每项写剂量上限与禁忌; 额度 ≤ 预算 15% 且 ≤25 元/天,
  钱优先花在食物上; 燃脂丸/DNP/利尿剂等设为红线不碰项。饮食/训练两侧都列就医触发条件。
- 新增 GUI 页 `fitness_pkg/auto_plan_page.py`「🧭 自动方案」(主程序 Tab 7), 与 CLI `auto_plan.py` 同源。
  补测试时发现两个真 bug 并修掉: (1) 目标体重曾被去脂体重推算值覆盖, 导致「65→72kg 增重」被判成方向反转;
  (2) 餐次份量曾按单价反推克数, 出现「香蕉 120 根 / 全麦面包 70 片」这类读不通、也算不出成本的标签。
  现在方向判定优先采用用户填写值, 份量按固定档位表给并区分可数/按重食材。
- 测试 223 通过（新增 61 项 `tests/test_auto_plan.py`）; `ruff check` + `ruff format --check` 全绿;
  冒烟 4 组通过（模块清单已含新文件）。README 补「🧭 自动方案」章节与 CLI 用法。
- 未动既有页面布局与口径; `auto_plan.py` 命令行入口不读写任何个人数据。

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
