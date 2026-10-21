[**升级打怪开源社区**](https://github.com/shengjidaguai-china) 共建项目 · [点击组织首页右上角 **Follow**](https://github.com/shengjidaguai-china)，及时获取新项目与共建活动

# 健身监控 FITNESS TRACKER

### 个人体脂体重监控 + 自动方案 + AI 教练，把真实训练经历变成有人愿意读完的长期闭环

[![GitHub Stars](https://img.shields.io/github/stars/shengjidaguai-china/fitness-tracker?style=flat-square&logo=github)](https://github.com/shengjidaguai-china/fitness-tracker/stargazers) [![Version](https://img.shields.io/badge/version-v9.2%20自动方案-ff6b35?style=flat-square)](https://cnb.cool/yuppiez328/fitness-tracker/-/releases) [![Tests](https://img.shields.io/badge/tests-213%20passed%20·%205%20skipped-3FB950?style=flat-square)](tests/) [![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/) [![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)

**如果健身监控对你有帮助，请点一个 Star。你的 Star 会帮助更多独立开发者发现它。**

> 上游仓库：[GitHub · shengjidaguai-china/fitness-tracker](https://github.com/shengjidaguai-china/fitness-tracker)；本仓 [CNB 镜像](https://cnb.cool/yuppiez328/fitness-tracker) 跑 NPC 自动开发，Tag 触发流水线出 exe。

[![健身监控架构](docs/fitness-arch.visual-check.1440x900.light.png)](docs/fitness-arch.html)

## 健身监控是什么

健身监控是一套面向个人训练者、独立开发者和 AI 创作者的中文体测与训练桌面应用。

它读取本地体测数据、动作示范、训练计划、专家知识库和用户口述，先建立训练事实边界，再把真实训练经历写成具有冲突、选择、训练取舍和结果边界的长期闭环。

健身监控不是把训练日志扩写成图表，也不是用闭源 App 锁定用户数据。

> 它要做的，是让真实训练经历变得可信、好懂、可追踪，而且数据永远在本地。

## 为什么做健身监控

很多个人训练者遇到的并不是“没有数据”，而是：

- 体测数据散落在 Excel、Keep、体测仪 App 和纸质表中；
- 现成健身 App 闭源、数据不导出、广告多；
- 训练计划与体测数据割裂，看不到长期关联；
- 在线 AI 教练要么收费，要么不懂训练科学；
- 换设备或换 App 就丢数据，每次重新建档；
- 训练科学规则散落在书里和视频里，没法落地成可执行规则；
- 网上的补剂推荐和速度上限没有安全约束，照着练容易出事。

健身监控把这些问题变成一条可执行的训练生产管线。

## 核心能力

### 1. 体测仪表盘

12 项体测指标快速录入与历史记录：日期、体重、体脂率、肌肉量、内脏脂肪等级、基础代谢率、体水分率、骨量、BMI、骨骼肌率、腰围、臀围。支持目标体重 / 目标体脂率自定义，变化值以“当前 - 初始”计算，降低显示为负数。

### 2. 趋势分析

7 日 EMA 平滑曲线、目标达标日预测、体成分饼图。把散落的体测数据变成可读的趋势，不夸大进度，不偷换局部指标为整体提升。

### 3. 动作示范库

66 个动作卡片（其中 60 个带 GIF 示范）、中文步骤教学、肌群信息。支持按动作名 / 肌群 / 器材搜索，点击卡片即可查看示范与详细步骤。

### 4. 训练计划

22 周宽背窄腰塑形 v2.1，三阶段周期化，6 练 1 休。背（宽）→ 胸 + 三头 → 腿 → 背（厚）+ 二头 → 肩 + 核心 → 推 + 腿泵感 → 完全休息。每日动作带 GIF 预览、组数次数标注与替代方案说明。

### 5. 饮食与补剂

三阶段营养方案、五餐明细、补剂表、饮水指南。训练日 / 休息日差异化热量结构，实时追踪蛋白质、碳水、脂肪三大宏量。补剂方案按训练前后时段智能推荐。

### 6. 自动方案 · 输入驱动 (v9.2 新增)

两条输入 → 两条输出，规则全部复用既有规则层，GUI 页与 CLI 同源（`fitness_pkg/auto_plan.py` + CLI `auto_plan.py`）：

| 输入 | 输出 |
|:-----|:-----|
| 当前体重 / 体脂率 + 目标体重 / 体脂率（可选身高 / 年龄 / 性别 / 训练年限） | 训练计划：方向 + 周期周数 + P0–L3 等级 + 每周分化 + **每日动作的组 × 次 × RPE** |
| 月度伙食费预算 | 每日饮食计划：热量与三大宏量 + 六餐份量与采购参考 + 补剂清单（含剂量上限与禁忌） |

```bash
# GUI: 左侧「自动方案」页, 填参数点「生成方案」
# CLI: 不读写任何个人数据, 直接出 Markdown
python auto_plan.py --weight 74 --bodyfat 23 --target-weight 68 --target-bodyfat 15 --budget 1500 --height 175
python auto_plan.py --weight 74 --bodyfat 23 --target-bodyfat 15 --budget 1500 --out 方案.md   # 落成文件
```

**安全约束（写死在代码里，不是文案）**：

- 减脂周速度上限 **1% 体重**、增肌 **0.25% 体重**；目标再激进也只会延长周期，不会加大缺口
- 体脂接近必需脂肪区间（男 ≤5% / 女 ≤12%）→ 提示不建议继续减脂，先做医学评估
- 补剂只保留乳清 / 肌酸 / 维 D3 / 鱼油 / 镁 / 锌这类常用安全品类，每项写明**剂量上限与禁忌**
- 补剂占比不超过预算 15% 且不超过 25 元 / 天：钱先花在真食物上，蛋白缺口优先补齐
- 补剂红线（燃脂丸、促生长类、利尿剂等）直接列为不碰项；有基础病 / 服药 / 孕期先问医生

### 7. AI 教练

基于 Lzheng-fitness 六位专家知识库的增肌规划系统，**纯 Python 实现，离线运行，无需 AI 对话**：

- 建档与分层：P0-L3 四级训练阶段评估 + 周组数区间校验
- 力量周期：8-12 周动态周期生成（积累 → 强度 → 实现 → 减量），含热身流程、顶组 + 回退组、逐组 RPE 路径
- 训练复盘：单次复盘 + 渐进超负荷决策（双重渐进：先加次再加重）+ 反应式减载清单 + 停滞检测
- 停训接回：三档接回方案（正常 / 降级 / 最低）+ 48 小时接回动作 + 升级 / 维持 / 暂停条件
- 短版训练：30/20/10/5/2 分钟最低执行版本 + 动作模式缺口审计

### 8. 训练科学规则层

把 Lzheng-fitness 知识库里的判断规则收敛为**可配置、可测试**的参数（`fitness_pkg/science.py`，用例覆盖规则层 / AI 引擎 / 数据层 / 解析器 / 计划视图 + 冒烟检查）：

| 规则 | 口径 | 来源 |
|:-----|:-----|:-----|
| RPE/RIR | RPE 10 ≈ 0 RIR、9 ≈ 1 RIR、8 ≈ 2 RIR、7 ≈ 3 RIR，半档取更保守一侧 | Helms 训练金字塔 pp.64-65 |
| 周组数 | 每肌群 / 动作模式 10–20 组起始区间，按 P0–L3 分层取值 | Helms Level 2；Nuckols |
| 组间休息 | 复合主项 ≥2.5 分钟、孤立动作 ≥1.5 分钟；时间紧用拮抗肌配对组 | Helms Level 5 pp.171-187 |
| 力竭使用 | 多数组保留 1–2 RIR；复合主项常规不做力竭，孤立动作仅末组可接近 | Schoenfeld 第 4 章 |
| 渐进方式 | 复合动作用线性 / 波浪周期，孤立动作优先双重渐进 | Helms Level 3 pp.99-125 |
| 自动调节 | 按 e1RM 与目标 RPE 校正当日负荷；一次只动一个主要变量 | Nuckols APRE |
| e1RM 口径 | 先按 RIR 折算到力竭重量再套 Epley，与负荷换算互为逆运算 | Lzheng 03 |
| 节律减载 | 约每 4 周一次，减载周强度必须低于任何实现周；连续 3 个中周期未减载 → 预防性减载 | Helms pp.121-125 |
| 反应式减载 | 命中 2 项及以上 → 减载一周 | Helms pp.121-125 |
| 停滞判定 | 同重量掉次数或 RPE 升约一级，连续两次才怀疑结构 | Lzheng 03/05 |
| 安全分流 | 胸痛 / 晕厥 / 麻木 / 放射痛直接暂停常规处方并建议专业评估 | Lzheng 01；ACSM/WHO |
| 短版训练 | 保留当天主线、先减附件、不压缩复合主项休息；漏 1 次不补课、漏 2 次用短版接回 | Lzheng 04；Helms Level 5 |

### 9. 一键封装与质量工程

PyInstaller 一键封装为独立 .exe（`build_exe.py`），免安装 Python 直接运行。集成 ruff + pre-commit + pytest 三条开源质量链，213 项测试提交即自动把关。CNB 流水线（`.cnb.yml` 的 `windows-exe-release`）在推 Tag 时自动在 Windows 构建机打包并上传 Releases 附件。

## 当前能力规模

| 能力 | 当前版本 |
|:---|:---|
| 侧边栏页面 | 7 个（含自动方案） |
| 体测指标 | 12 项 |
| 动作卡片 | 66 个（60 个带 GIF） |
| 训练计划 | 22 周周期化 |
| 专家知识库 | 6 位 |
| 训练科学规则 | 12 类口径 |
| 自动方案链路 | 2 条（体测 → 训练，预算 → 饮食） |
| 单元 / 冒烟测试 | 213 passed · 5 skipped |
| Git 子模块 | 2 个 |
| 力量周期阶段 | 4 个（积累 / 强度 / 实现 / 减量） |
| 训练分层 | P0-L3 四级 |
| 接回方案 | 3 档（正常 / 降级 / 最低） |
| 短版训练 | 5 档（30/20/10/5/2 分钟） |
| 代码质量链 | ruff + pre-commit + pytest |
| 打包分发 | PyInstaller .exe + CNB 流水线 |

当前实现不保存任何个人体测正文到远端；AI 教练数据存储在本地 `体重体脂监控/ai_coach/`，不随仓库分发。`dist/` 已被 `.gitignore` 排除，exe 由 CNB 流水线或本地 Windows 打包生成。

## 适合谁

- 有真实训练，却总把记录写成训练日志的人；
- 想长期追踪体测趋势，又不想被闭源 App 锁定数据的人；
- 需要同时兼顾体测、训练、饮食和 AI 教练的人；
- 希望训练科学规则可配置、可测试，又不依赖在线 AI 的人；
- 想输入体重体脂和预算就出整套方案，且速度上限 / 补剂有安全约束的人；
- 经常遭遇“换 App 就丢数据”或“计划被 App 随意修改”的人。

## 与替代方案的区别

| 方案 | 优势 | 常见限制 |
|:---|:---|:---|
| Keep / Fitbod | 动作库大、社区活跃 | 闭源、数据不导出、广告多 |
| Hevy / Strong | 训练记录快 | 无体测追踪、无 AI 教练、无知识库 |
| 通用 AI 对话 | 快速生成计划 | 不懂训练科学、每次重新调教、无安全约束 |
| 在线 AI 教练 | 个性化强 | 收费、数据上传、离线不可用 |
| **健身监控** | 体测 + 自动方案 + AI 教练 + 知识库 + 离线 + 安全约束 + 可封装 | 仍需用户提供真实体测数据与训练判断 |

## 安装

### 方式一：免安装运行（CNB Releases 附件）

> 仓库源码不提交 exe，也不提交 `dist/`——产物由 CNB 流水线在 Windows 构建机上生成，或在 Windows 本机自行打包（PySide6 桌面程序无法跨平台打包）。

1. 打开本仓 Releases：<https://cnb.cool/yuppiez328/fitness-tracker/-/releases>
2. 找到对应版本附件 `健身监控-<tag>-windows-x64.zip`，下载解压（无需安装 Python）
3. 复制到任意 Windows 电脑，双击 `健身监控v9.0.exe` 即可运行

若 Releases 里还没有附件，说明尚未推过 Tag，请按下文「封装为独立 .exe」在 Windows 本机打包一次。

### 方式二：源码运行

- Python 3.8+
- 建议使用虚拟环境运行，避免全局包冲突

```bash
# 克隆仓库（含子模块）
git clone --recurse-submodules https://cnb.cool/yuppiez328/fitness-tracker.git
cd fitness-tracker

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安装依赖
pip install PySide6 matplotlib pandas numpy Pillow

# 直接运行
python 体脂体重监控_完整版.py
```

也可双击 `启动体脂体重监控.bat` 一键启动（Windows）。

### 封装为独立 .exe

```bash
pip install pyinstaller
python build_exe.py          # 推荐: 一键打包（含图标 + 精简排除项）
# 或使用 spec 文件:
python -m PyInstaller 健身监控v9.0.spec --noconfirm --clean
# 产物: dist\健身监控v9.0\健身监控v9.0.exe
```

启动异常需要看报错时，改用 `健身监控_debug.spec`（保留控制台窗口）。**让流水线帮你打包**：推一个 Tag（如 `git tag v9.2 && git push origin v9.2`），CNB 的 `windows-exe-release` 流水线会自动打包并上传 Releases 附件。本地依赖清单见 `requirements-build.txt`，与 CI 保持一致。

更新前请备份本地体测数据与 AI 教练数据，直接覆盖 `体重体脂监控/` 会丢失个人记录：

- `体重体脂监控/ai_coach/`
- `体重体脂监控/报告/`
- `体重体脂监控/图表/`

## 快速开始

### 录入体测数据

```
打开健身监控，进入「体测仪表盘」，
录入 12 项体测指标，查看 7 日 EMA 平滑曲线与目标达标日预测。
先建立体测事实边界，再设计训练主矛盾和结构。
```

### 自动方案（输入驱动）

```
进入「自动方案」页或 CLI：
python auto_plan.py --weight 74 --bodyfat 23 --target-weight 68 --target-bodyfat 15 --budget 1500 --height 175
输入体测 → 训练计划 + 每日动作（组 × 次 × RPE）；
输入预算 → 每日饮食 + 补剂清单（含剂量上限与禁忌）。
速度上限与补剂红线写死在代码里，不是文案。
```

### 停训接回

```
漏练或停训后，进入「AI 教练 → 停训接回」，
生成三档接回方案（正常 / 降级 / 最低）+ 48 小时接回动作。
不要修改已确认的计划顺序，只提出必要建议。
```

## 技术架构

```
PySide6 桌面应用（侧边栏 7 页）
  └── 体脂体重监控_完整版.py 主入口与路由
      ├── fitness_pkg 模型 / 页面 / 解析器
      │   ├── science.py 训练科学规则层（12 类口径）
      │   ├── plan_science.py 22 周计划科学化视图
      │   ├── auto_plan.py 输入驱动方案生成
      │   └── auto_plan_page.py 自动方案页面
      ├── auto_plan.py CLI 入口（不读写个人数据）
      ├── ai_coach_engine P0-L3 / 周期 / 复盘 / 接回 / 短版
      ├── Lzheng-fitness 六位专家知识库（Git 子模块）
      └── exercises-dataset 60 动作 GIF（Git 子模块）
```

健身监控采用渐进式知识加载：主入口负责流程和边界，详细方法按页读取，规则层口径收敛到 `fitness_pkg/science.py` 单一来源，引擎、GUI、自动方案与 22 周计划视图都按它下判，避免两套逻辑打架。

## 项目结构

```
fitness-tracker/
├── 体脂体重监控_完整版.py
├── fitness_modules.py
├── fitness_pkg/
│   ├── science.py
│   ├── plan_science.py
│   ├── auto_plan.py
│   └── auto_plan_page.py
├── auto_plan.py
├── ai_coach_engine.py
├── tests/
│   ├── smoke_check.py
│   ├── test_science.py
│   ├── test_plan_science.py
│   ├── test_auto_plan.py
│   ├── test_ai_coach_engine.py
│   └── test_fitness_pkg.py
├── build_exe.py
├── requirements-build.txt
├── 健身监控v9.0.spec
├── 健身监控_debug.spec
├── fitness_icon.ico
├── 启动体脂体重监控.bat
├── .cnb.yml
├── Lzheng-fitness/
├── exercises-dataset/
├── docs/
├── cairn/
├── 体重体脂监控/
│   ├── 训练计划文档（.md）
│   ├── ai_coach/
│   ├── exercises_gif/
│   └── exercises_matched.json
└── README.md
```

## 本地校验

```bash
# 冒烟: py_compile 全部核心模块 + 规则层断言 + 引擎端到端 + 4 项口径不变量
python tests/smoke_check.py

# 自动方案链路（无需 GUI）
python auto_plan.py --weight 74 --bodyfat 23 --target-weight 68 --target-bodyfat 15 --budget 1500 --height 175

# 单元测试
python -m pytest tests

# 代码风格
python -m ruff check .
python -m ruff format --check .
```

当前实测（Python 3.11，无 PySide6）：`pytest tests` → **213 passed · 5 skipped**，`smoke_check.py` → 4 组全过，`ruff` → 全绿。缺 PySide6 / numpy / pandas 时相关用例自动跳过；纯逻辑层在 CI 与 CLI 里可直接用。

## 版本

当前版本：**v9.2**

版本号口径：程序名统一为 **v9.0**，`v9.1` = 训练科学规则层，`v9.2` = 自动方案（输入驱动）；不是三个独立可执行文件。当前源码包含体测仪表盘、趋势分析、动作示范库、22 周训练计划、饮食与补剂、自动方案、AI 教练、训练科学规则层与 CNB 流水线一键封装。

## 许可证

**PolyForm Noncommercial License 1.0.0** · 非商业用途 · 必须署著作名

| | |
|:---|:---|
| ✅ 允许 | 个人使用 · 学习研究 · 兴趣项目 · 修改自用 · 非商业组织使用 · 学术引用 |
| ❌ 禁止 | 商业产品 / 服务 · 企业商业运营 · 付费分发 · 商业 AI 训练 · 移除署名 · 再许可 |

```text
Required Notice: Copyright (c) 2026 yuppiez99999 (https://github.com/yuppiez99999)
```

完整法律文本见 [`LICENSE`](./LICENSE)。两个 Git 子模块（`Lzheng-fitness` / `exercises-dataset`）各自保留原许可证，主仓库 PolyForm NC 不覆盖子模块内部。商业授权请通过 [本仓 Issues](https://cnb.cool/yuppiez328/fitness-tracker/-/issues) 联系作者。

## 支持健身监控

如果健身监控帮你完成了一次体测追踪、生成了一套自动方案，或者让训练项目终于有人愿意读完，请点一个 Star。

### ⭐ Star 是对独立开发最直接的支持

[给健身监控一个 Star](https://github.com/shengjidaguai-china/fitness-tracker) · [提交问题](https://cnb.cool/yuppiez328/fitness-tracker/-/issues) · [查看版本](https://cnb.cool/yuppiez328/fitness-tracker/-/releases)
