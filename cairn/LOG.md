# fitness-tracker LOG

> 最新在顶部。每条 ≤ 20 行，仅摘要 + 指针。

## 2026-09-04 训练科学性升级 (F5)
- 扫描 3 个 GitHub 关联仓库后，确认科学来源是 `Lzheng-fitness/knowledge/` 与六位专家模块；据此新增训练科学规则层并全链路接入。
- 新增 `fitness_pkg/science.py`：RPE/RIR 换算、e1RM 互逆口径、P0–L3 周组数区间、自动调节、反应式减载清单、停滞/平台检测、组间休息、热身流程、多组 RPE 路径、力竭策略、节奏建议、动作缺口审计、安全分流。
- `ai_coach_engine.py`：周期生成接入热身/休息/力竭/节奏并封顶减量强度；复盘改为科学层统一判定（含减载与停滞）；接回增加 48 小时动作与升级/维持/暂停条件；短版扩展到 5/2 分钟；导出 Markdown 增加「科学依据」「验证方式」。
- `fitness_pkg/ai_coach.py`：建档加周组数校验、周期页加训练等级与执行口径、复盘页加目标次数与减载信号勾选、接回页支持多动作、短版页加缺口审计。
- 新增 `tests/test_science.py`（49 项）+ `tests/smoke_check.py`（冒烟）；`python -m unittest discover -s tests` 与 `python tests/smoke_check.py` 均通过。
- README 增补训练科学规则层说明表；ROADMAP 增补 F5 交付清单与 F6/F7 排期。
- 边界：未改个人数据目录 / LICENSE / 子模块；未提交任何个人体测或训练数据。GUI 改动建议本地 Windows 冒烟。

## 2026-09-03 初始化 CNB 双轨 NPC 配置
- 克隆 GitHub `yuppiez99999/fitness-tracker` 到本地 `e:/各种PY程序/fitness-tracker`，生成 `.cnb.yml` + `.cnb/settings.yml`（照搬量化系统 28-终极量化交易系统8.4 的双轨模式，prompt 改写为健身监控上下文）。
- 目标 CNB 仓: `yuppiez328/fitness-tracker`（CNB 账号与 GitHub 源 yuppiez99999 不同名，沿用双轨惯例）。
- 补 `cairn/ROADMAP.md` + `cairn/LOG.md` 使自动接管可运行。
- 后续: 用户自行 commit & push（含 .cnb.yml / .cnb/settings.yml / cairn/）到 CNB 镜像，并在 cnb.cool 网页启用 NPC / 配置 crontab 触发。
