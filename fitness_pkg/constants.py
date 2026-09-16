"""
健身软件 — 全局配置与常量 (v7.0 模块化拆分)
路径常量、颜色主题、动作库图标映射、训练日程/阶段表、体测列定义。

设计系统层 (v10.1 结构升级, 视觉与 v10 完全一致):
  · 色彩体系 = 基础色板 _RAW_PALETTE(仅 #RRGGBB) + 派生 token(alpha/soft/border)
    → 换肤只需维护 _RAW_PALETTE; COLORS 为扁平兼容视图(既有 key/value 恒定)。
  · 样式函数 = 统一 QSS 生成(按钮/输入框/状态胶囊/媒体面板/切换按钮)。
    页面与全局样式表共用, 禁止再在页面内硬编码色值。
"""

import os
from typing import Dict, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "体重体脂监控")
CHART_DIR = os.path.join(DATA_DIR, "图表")
REPORT_DIR = os.path.join(DATA_DIR, "报告")
DATA_FILE = os.path.join(DATA_DIR, "体脂体重.txt")
EXERCISES_JSON = os.path.join(DATA_DIR, "exercises_matched.json")
GIF_DIR = os.path.join(DATA_DIR, "exercises_gif")
PLAN_MD = os.path.join(DATA_DIR, "居家平替计划_v3.0_单杠哑铃版_GUI解析.md")

for d in [DATA_DIR, CHART_DIR, REPORT_DIR, GIF_DIR]:
    os.makedirs(d, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# 设计系统层 · 色彩体系 (v10 现代清新风 — 暖纸白 + 品牌蓝 + 语义色板)
#
# 铁律:
#   1) 人工只维护 _RAW_PALETTE (全部 6 位 #RRGGBB, 无透明度)
#   2) soft/border/glow/hover 等派生 token 一律程序化生成,
#      禁止手写 8 位十六进制 #RRGGBBAA (防色值漂移)
#   3) UI 代码只消费 COLORS 与下方统一样式函数
# ═══════════════════════════════════════════════════════════════


def _rgb(h: str) -> Tuple[int, int, int]:
    """#RGB / #RRGGBB -> (r, g, b)"""
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def darken(color: str, factor: float = 0.85) -> str:
    """颜色加深 (hover/pressed 反馈用)"""
    r, g, b = _rgb(color)
    return f"#{int(r * factor):02X}{int(g * factor):02X}{int(b * factor):02X}"


def alpha(color: str, a: str) -> str:
    """追加 2 位十六进制透明度 -> #RRGGBBAA (如 '14'≈8%, '40'≈25%, 'B8'≈72%)"""
    return "#{:02X}{:02X}{:02X}{}".format(*_rgb(color), a)


# ────────────────────────────────────────────────────────────
# 基础色板: 唯一人工维护区 (全部 6 位 #RRGGBB, 无透明度)
# ────────────────────────────────────────────────────────────
_RAW_PALETTE: Dict[str, str] = {
    # 中性表面
    "bg": "#FAF7F1",  # 页面底(暖纸白)
    "card": "#FFFFFF",  # 卡片/弹层底
    "card2": "#F1ECE2",  # 内嵌浅底 / 禁用底
    "border": "#DDD3C2",  # 常规描边 (v10.2 略加深, 卡片更立体)
    "text": "#2E2720",  # 主文字
    "subtext": "#7A7264",  # 次要文字 (v10.2 略加深, 提升对比度)
    # 品牌主色 + 语义状态色
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "success": "#2DA44E",
    "success_dark": "#1F883D",
    "warning": "#C6800A",
    "warning_dark": "#9E6A00",
    "danger": "#CF222E",
    "danger_dark": "#A40E26",
    "purple": "#7C3AED",
    "cyan": "#0E9AA7",
    "accent": "#E8833A",
    # 训练类型色 (v5.9.2 HIIT/LISS/休息; 预调浅底作为固定值保存)
    "hiit_fg": "#E85D3A",
    "hiit_bg": "#FDE8E3",
    "liss_fg": "#2DA44E",
    "liss_bg": "#E6F4EA",
    "rest_fg": "#8250DF",
    # 顶部品牌头栏 (深墨蓝 → 宝蓝渐变)
    "appbar_a": "#101828",
    "appbar_b": "#1E3A8A",
    "appbar_text": "#FFFFFF",
    # 表格 / 滚动条细节
    "table_alt": "#F7F2E8",
    "scroll": "#C5BBA8",
    "scroll_hover": "#A89E8B",
    # 深色媒体 / GIF 播放区 (视频面板专用, 原 GitHub-Dark 系)
    "player_bg": "#0E1116",
    "player_border": "#2A313C",
    "player_subtext": "#8B949E",
    "player_error": "#F85149",
}


# ────────────────────────────────────────────────────────────
# 派生 token: 由基础色程序化生成 (视觉与 v10 完全一致)
# ────────────────────────────────────────────────────────────
_DERIVED_COLORS: Dict[str, str] = {
    # 主色系交互态: hover 底 / 焦点光圈 / 浅底内容框描边
    "primary_soft": alpha(_RAW_PALETTE["primary"], "1A"),
    "glow": alpha(_RAW_PALETTE["primary"], "40"),
    "primary_border": alpha(_RAW_PALETTE["primary"], "55"),
    # 状态色 soft(≈8%) / border(≈25%) 对 — 状态胶囊/提示条统一取用
    "success_soft": alpha(_RAW_PALETTE["success"], "14"),
    "success_border": alpha(_RAW_PALETTE["success"], "40"),
    "warning_soft": alpha(_RAW_PALETTE["warning"], "14"),
    "warning_border": alpha(_RAW_PALETTE["warning"], "40"),
    "danger_soft": alpha(_RAW_PALETTE["danger"], "14"),
    "danger_border": alpha(_RAW_PALETTE["danger"], "40"),
    # 通用叠加层: 悬停罩 / 深色头栏次要文字
    "hover": alpha("#000000", "14"),
    "appbar_sub": alpha("#FFFFFF", "B8"),
}


# ────────────────────────────────────────────────────────────
# COLORS: 扁平兼容视图 (既有 key/value 一律不变, 仅追加语义 token)
# ────────────────────────────────────────────────────────────
COLORS: Dict[str, str] = {}
COLORS.update(_RAW_PALETTE)
COLORS.update(_DERIVED_COLORS)

# 图表 / 饼图通用色板 (由语义 token 派生, 换肤自动跟随)
CHART_PALETTE: Tuple[str, ...] = tuple(
    COLORS[k] for k in ("primary", "cyan", "purple", "success", "accent", "warning", "danger", "hiit_fg")
)


def _css(text: str) -> str:
    """把文本中的 @@key@@ 占位符替换为 COLORS 值"""
    for k, v in COLORS.items():
        text = text.replace("@@" + k + "@@", str(v))
    return text


# 圆角 / 间距设计令牌 (v10.2 圆角加大更柔和, 间距略增呼吸感)
_RADIUS = 12
_RADIUS_LG = 16
PAGE_MARGINS = (24, 20, 24, 20)
PAGE_SPACING = 16


# ═══════════════════════════════════════════════════════════════
# 设计系统层 · 统一样式函数 (全部页面 / 全局 QSS 共用)
# ═══════════════════════════════════════════════════════════════


def button_style(
    bg: str,
    fg: str = "#FFFFFF",
    radius: int = _RADIUS,
    padding: str = "8px 18px",
    font_size: int = 12,
) -> str:
    """实心主按钮 — 自动生成 hover / pressed / disabled 反馈"""
    return _css(f"""
        QPushButton {{ background-color: {bg}; color: {fg}; border: none;
                       border-radius: {radius}px; padding: {padding}; min-height: 36px;
                       font-size: {font_size}px; font-weight: 700; }}
        QPushButton:hover {{ background-color: {darken(bg)}; }}
        QPushButton:pressed {{ background-color: {darken(bg, 0.75)}; }}
        QPushButton:disabled {{ background-color: @@border@@; color: @@subtext@@; }}
    """)


def outline_button_style(
    accent: Optional[str] = None,
    bg: Optional[str] = None,
    fg: Optional[str] = None,
    radius: int = _RADIUS,
    padding: str = "7px 16px",
    font_size: int = 11,
) -> str:
    """描边次按钮 — 传入高亮色 accent (默认主色)"""
    ac = accent or COLORS["primary"]
    bgb = bg or COLORS["card"]
    fgc = fg or COLORS["text"]
    return _css(f"""
        QPushButton {{ background-color: {bgb}; color: {fgc}; border: 1px solid @@border@@;
                       border-radius: {radius}px; padding: {padding}; min-height: 36px;
                       font-size: {font_size}px; font-weight: 600; }}
        QPushButton:hover {{ background-color: {alpha(ac, "1A")}; border-color: {ac}; color: {ac}; }}
        QPushButton:pressed {{ background-color: {alpha(ac, "33")}; }}
        QPushButton:checked {{ background-color: {ac}; border-color: {ac}; color: #FFFFFF; }}
        QPushButton:disabled {{ color: @@subtext@@; background-color: @@card2@@; }}
    """)


def toggle_button_style(
    on_color: Optional[str] = None,
    radius: int = _RADIUS,
    padding: str = "6px 18px",
    font_size: int = 12,
) -> str:
    """可勾选/切换按钮 (播放/暂停等): 常态描边 + checked 实心高亮"""
    on = on_color or COLORS["success"]
    return _css(f"""
        QPushButton {{ background-color: @@card@@; color: @@text@@;
                       border: 1px solid @@border@@; border-radius: {radius}px;
                       padding: {padding}; font-size: {font_size}px; font-weight: 600; }}
        QPushButton:hover {{ border-color: {on}; color: {on}; }}
        QPushButton:checked {{ background-color: {on}; border-color: {on}; color: #FFFFFF; }}
        QPushButton:checked:hover {{ background-color: {darken(on)}; border-color: {darken(on)}; }}
        QPushButton:disabled {{ color: @@subtext@@; background-color: @@card2@@; }}
    """)


def pill_style(
    fg: Optional[str] = None,
    bg: Optional[str] = None,
    border: Optional[str] = None,
    radius: int = _RADIUS,
    padding: str = "8px 12px",
    font_size: int = 12,
    weight: int = 600,
) -> str:
    """统一状态胶囊/提示条 (QLabel/QFrame 等)
    只传前景色时自动派生: 底 = 前景 8% 透明, 描边 = 前景 25% 透明。
    例: lbl.setStyleSheet(pill_style(COLORS["success"]))
    """
    fgc = fg or COLORS["success"]
    bga = bg or alpha(fgc, "14")
    bda = border or alpha(fgc, "40")
    return (
        f"color: {fgc}; background-color: {bga}; border: 1px solid {bda}; "
        f"border-radius: {radius}px; padding: {padding}; "
        f"font-size: {font_size}px; font-weight: {weight};"
    )


def player_panel_style(radius: int = _RADIUS_LG) -> str:
    """深色 GIF 播放区面板 — QFrame/QWidget 底色 + 描边"""
    return _css(f"background-color: @@player_bg@@; border-radius: {radius}px; border: 1px solid @@player_border@@;")


def player_text_style(error: bool = False, font_size: int = 13, padding: str = "0px") -> str:
    """GIF 播放区提示/错误文字 (透明底)"""
    key = "player_error" if error else "player_subtext"
    return _css(f"background-color: transparent; color: @@{key}@@; font-size: {font_size}px; padding: {padding};")


def surface_style(radius: int = _RADIUS_LG) -> str:
    """页面卡片表面 — 白底 + 细描边, 禁止页面内再手写一套卡片色"""
    return _css(f"background-color: @@card@@; border: 1px solid @@border@@; border-radius: {radius}px;")


def nav_button_style() -> str:
    """左侧导航项 — 常态透明, 选中主色浅底 + 左侧强调条 (v10.2 hover 也预留左条避免跳动)"""
    return _css(f"""
        QPushButton {{ background-color: transparent; color: @@subtext@@; border: none;
                       border-left: 3px solid transparent;
                       border-radius: {_RADIUS}px; padding: 10px 14px 10px 12px;
                       min-height: 44px; text-align: left; font-size: 13px; font-weight: 600; }}
        QPushButton:hover {{ background-color: @@hover@@; color: @@text@@; }}
        QPushButton:checked {{ background-color: @@primary_soft@@; color: @@primary@@; font-weight: 700;
                               border-left: 3px solid @@primary@@; }}
        QPushButton:pressed {{ background-color: @@primary_soft@@; }}
    """)


def input_style() -> str:
    """文本/数值输入框统一观感 (含 hover / focus / disabled) — v10.2 focus 加品牌色光圈"""
    return _css(
        """
        QLineEdit { background-color: @@card@@; color: @@text@@;
                    border: 1px solid @@border@@; border-radius: """
        + str(_RADIUS)
        + """px;
                    padding: 8px 12px; min-height: 20px;
                    selection-background-color: @@primary@@;
                    selection-color: #FFFFFF; }
        QLineEdit:hover { border-color: @@primary_border@@; }
        QLineEdit:focus { border: 1px solid @@primary@@; padding: 8px 12px; }
        QLineEdit:disabled { background-color: @@card2@@; color: @@subtext@@; }
    """
    )


def spin_style() -> str:
    """数字/日期输入框统一观感 (QSpinBox / QDoubleSpinBox / QDateEdit) — v10.2 focus 统一单线"""
    return _css(f"""
        QSpinBox, QDoubleSpinBox, QDateEdit {{ background-color: @@card@@; color: @@text@@;
            border: 1px solid @@border@@; border-radius: {_RADIUS}px;
            padding: 6px 10px; min-height: 28px; }}
        QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{ border-color: @@primary_border@@; }}
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{ border: 1px solid @@primary@@; }}
    """)


def select_style() -> str:
    """下拉框统一观感 (弹层视图样式由全局 QSS 提供) — v10.2 focus 统一单线"""
    return _css(f"""
        QComboBox {{ background-color: @@card@@; color: @@text@@;
                     border: 1px solid @@border@@; border-radius: {_RADIUS}px;
                     padding: 6px 12px; min-height: 28px; font-size: 12px; }}
        QComboBox:hover {{ border-color: @@primary_border@@; }}
        QComboBox:focus {{ border: 1px solid @@primary@@; }}
        QComboBox::drop-down {{ border: none; width: 28px; }}
    """)


def textedit_style() -> str:
    """只读/编辑多行文本域 (AI 教练输出等)"""
    return _css(
        """
        QTextEdit, QPlainTextEdit { background-color: @@card@@; color: @@text@@;
                    border: 1px solid @@border@@; border-radius: """
        + str(_RADIUS)
        + """px;
                    padding: 6px; selection-background-color: @@primary@@;
                    selection-color: #FFFFFF; }
    """
    )


def build_global_stylesheet() -> str:
    """应用级全局样式 — 未单独设置样式的控件统一获得现代观感"""
    core = """
        QMainWindow, QDialog { background-color: @@bg@@; }
        QWidget { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
        QLabel { color: @@text@@; }
        QToolTip { background-color: @@card@@; color: @@text@@;
                    border: 1px solid @@border@@; border-radius: 10px; padding: 6px 10px; }
        QMessageBox { background-color: @@card@@; }
        QStatusBar { background-color: @@card@@; color: @@subtext@@;
                      border-top: 1px solid @@border@@; font-size: 11px; min-height: 24px; }
        QStatusBar::item { border: none; }

        QScrollArea { border: none; background: transparent; }

        QTabWidget::pane { border: none; background-color: @@bg@@; top: 8px; }
        QTabWidget::tab-bar { left: 0px; }
        QTabBar::tab { background: @@card@@; color: @@subtext@@;
                        border: 1px solid @@border@@; border-radius: 12px;
                        padding: 8px 18px; margin-right: 6px; min-height: 36px; font-weight: 600; }
        QTabBar::tab:hover:!selected { color: @@text@@; border-color: @@primary_border@@;
                                        background-color: @@primary_soft@@; }
        QTabBar::tab:selected { color: #FFFFFF; background-color: @@primary@@;
                                 border-color: @@primary@@; font-weight: 700; }
        QTabBar::tab:focus { outline: none; }

        QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
        QScrollBar::handle:vertical { background-color: @@scroll@@; border-radius: 4px;
                                       min-height: 28px; }
        QScrollBar::handle:vertical:hover { background-color: @@scroll_hover@@; }
        QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
        QScrollBar::handle:horizontal { background-color: @@scroll@@; border-radius: 4px;
                                         min-width: 28px; }
        QScrollBar::handle:horizontal:hover { background-color: @@scroll_hover@@; }
        QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none;
                                                      background: transparent; }
        QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

        QMenuBar { background-color: @@appbar_a@@; color: @@appbar_text@@; }
        QMenuBar::item:selected { background-color: @@primary@@; }
        QMenu { background-color: @@card@@; color: @@text@@; border: 1px solid @@border@@; }
        QMenu::item:selected { background-color: @@primary@@; color: #FFFFFF; }

        QComboBox QAbstractItemView { background-color: @@card@@; color: @@text@@;
                        border: 1px solid @@border@@; border-radius: 8px; padding: 4px;
                        selection-background-color: @@primary@@; selection-color: #FFFFFF;
                        outline: 0; }
        QComboBox::item:selected { background-color: @@primary@@; color: #FFFFFF; }

        QHeaderView::section { background-color: @@card@@; color: @@subtext@@;
                        border: none; border-bottom: 1px solid @@border@@;
                        border-right: 1px solid @@border@@;
                        padding: 8px 10px; font-weight: 700; }
        QTableCornerButton::section { background-color: @@card@@; border: none; }
    """
    # 各控件完整样式块 (自身已含选择器), 直接平铺追加
    blocks = [
        input_style(),
        select_style(),
        spin_style(),
        textedit_style(),
        _css(
            """
            QPushButton { background-color: @@card@@; color: @@text@@;
                border: 1px solid @@border@@; border-radius: """
            + str(_RADIUS)
            + """px;
                padding: 7px 16px; font-weight: 600; }
            QPushButton:hover { background-color: @@card2@@; border-color: @@primary_border@@; }
            QPushButton:pressed { background-color: @@border@@; border-color: @@primary@@; }
            QPushButton:disabled { color: @@subtext@@; background-color: @@card2@@; }
        """
        ),
    ]
    return _css(core + "\n".join(blocks))


# 肌肉群 Emoji 映射 (缺GIF时的占位图标)
MUSCLE_EMOJI = {
    "胸": "💪",
    "上胸": "⬆️",
    "下胸": "⬇️",
    "背": "🏋️",
    "背部": "🏋️",
    "二头": "💪",
    "三头": "🤜",
    "腿": "🦵",
    "股四头": "🦵",
    "臀": "🍑",
    "小腿": "🦶",
    "肩": "🙆",
    "三角肌": "🙆",
    "核心": "🔥",
    "腹": "🔥",
    "腹斜": "🔥",
    "有氧": "🏃",
    "波比": "🔥",
    "壶铃": "🪨",
    "跳绳": "⤴️",
    "冲刺": "⚡",
    "HIIT": "⚡",
    "TABATA": "⚡",
    "LISS": "🚶",
    "徒手": "✊",
    "俯卧撑": "🤸",
    "下压": "⏬",
    "举腿": "🦵",
    "悬挂": "🔗",
    "弹力带": "🎀",
    "绳索": "🪢",
    "杠铃": "🏋️",
    "哑铃": "🥊",
    "默认": "🎯",
}

# 真空腹训练文字教程 (数据集无此动作, 通过弹窗提供专业指导)
VACUUM_TUTORIAL = [
    "选择姿势: 四点支撑（双手双膝着地）或跪姿或站姿, 新手推荐四点支撑, 最容易感知腹横肌。",
    "深吸一口气, 然后用力呼气, 把肺里所有空气都吐尽, 这是关键的一步 —— 必须完全排空。",
    "保持呼气末状态, 用力收腹, 想象把肚脐往脊椎方向拉, 同时收紧整个腹部区域（腹横肌收缩）。",
    '保持收缩状态 15-60 秒, 此期间用胸式呼吸（吸气时胸腔扩张但腹部不要鼓起）, 让腹部持续"内收"。',
    "放松呼气, 然后重复。每组 60 秒, 每天 3-5 组, 早晚各一次。",
    '进阶技巧: 保持真空腹时可配合站立/走路, 形成"动态真空腹", 腹横肌刺激翻倍。',
    "常见错误: ❌ 憋气（会导致血压飙升, 头晕）❌ 用腹直肌发力（应该深层收缩）❌ 腹直肌鼓起（必须内收）。",
    "⚠ 健康提示: 孕妇、高血压、心脏病患者不宜做; 训练中如感头晕立即停止, 正常呼吸休息。",
    "预期效果: 研究显示持续 8 周真空腹训练, 腰围可减少 2-3cm (视觉上更窄), 配合体脂降低效果更佳。",
    "训练时间安排: 早晨起床后空腹（代谢唤醒）+ 训练后（巩固效果）+ 睡前（替代腹部呼吸, 提升睡眠质量）。",
]

# 其他流程块通用教程 (HIIT/LISS/其他复合训练)
FLOW_TUTORIAL = {
    "hiit_loop": [
        "HIIT（高强度间歇训练）原理: 短时间全力运动 + 短休息, 提升心率至 150-170 bpm。",
        "每个动作 40 秒全力训练, 20 秒休息, 6 个动作为一组, 4 组循环。",
        "组间休息 90 秒, 让心率短暂恢复。",
        "⚠ 安全提示: 心血管疾病患者不宜做, 训练前充分热身, 训练中如感不适立即停止。",
        "预期效果: HIIT 比 LISS 燃脂效率高 30%, 运动后过量氧耗 (EPOC) 可持续 24 小时。",
    ],
    "liss_cardio": [
        "LISS（低强度稳态有氧）原理: 保持心率在脂肪供能区间 (120-135 bpm), 持续 35-45 分钟。",
        "推荐项目: 快走、慢跑机、椭圆机、骑车等, 选择能持续 30 分钟以上的低强度活动。",
        "⚠ 关键: 心率必须稳定在 120-135, 不要跑太快进入无氧区间, 否则燃脂效率反而下降。",
        "预期效果: 直接燃脂 + 提升心肺基础 + 不易疲劳, 适合每周 2-3 次作为减脂主轴。",
    ],
    "flow": [
        "这是一个训练流程组合, 由多个基础动作组成, 目的是综合刺激多个肌群或达到特定训练目标。",
        "执行要点: 按顺序完成每个动作, 组间休息根据动作复杂度调整 (30-90 秒)。",
        "训练前充分热身, 训练后拉伸放松, 避免运动损伤。",
    ],
}


# 按目标肌群关键词推断 emoji
def _emoji_for_target(target: str) -> str:
    """根据目标肌群中英文返回emoji"""
    if not target:
        return MUSCLE_EMOJI["默认"]
    t = target
    # 按优先级匹配
    for key, emoji in MUSCLE_EMOJI.items():
        if key in t:
            return emoji
    return MUSCLE_EMOJI["默认"]


# 体测指标完整列(扩展12项)
BODY_COLUMNS = [
    "日期",
    "体重(kg)",
    "体脂率(%)",
    "肌肉量(kg)",
    "内脏脂肪等级",
    "基础代谢率(kcal)",
    "体水分率(%)",
    "骨量(kg)",
    "BMI",
    "骨骼肌率(%)",
    "腰围(cm)",
    "臀围(cm)",
]

# 训练计划结构(v3.0 居家平替版, 单杠+哑铃, 22周塑形冲刺, 三阶段周期化, 6练1休)
# ★v3.0: 全部居家版动作, 单杠变式替代下拉/Pullover替代直臂下压, 弹力带补绳索
TRAINING_SCHEDULE = [
    {
        "day": "周一",
        "title": "背（宽）居家",
        "focus": "宽握引体+反握引体+单臂哑铃划船+哑铃Pullover, 背阔宽度",
        "icon": "🔙",
    },
    {"day": "周二", "title": "胸+三头居家", "focus": "上斜哑铃卧推+飞鸟+哑铃飞鸟+椅子臂屈伸, 上胸优先", "icon": "💪"},
    {"day": "周三", "title": "腿居家", "focus": "Goblet深蹲+罗马尼亚硬拉+保加利亚分腿蹲, 哑铃复合", "icon": "🦵"},
    {"day": "周四", "title": "背（厚）+二头居家", "focus": "对握引体+胸支撑哑铃划船+俯身划船, 上背厚度", "icon": "🏋️"},
    {"day": "周五", "title": "肩+核心居家", "focus": "坐姿肩推+侧平举+弹力带面拉+俯身飞鸟, 中束+肩袖", "icon": "🙆"},
    {"day": "周六", "title": "推+腿泵感居家", "focus": "上斜哑铃+椅子臂屈伸+Goblet深蹲泵感+俯卧撑循环", "icon": "🔥"},
    {"day": "周日", "title": "完全休息 + 真空腹", "focus": "真空腹 30→60秒递进, 控盐日 <3g, 窄腰核心", "icon": "😴"},
]

# 三阶段映射 (v3.0: 22周 居家平替版)
PHASE_INFO = {
    1: {
        "name": "基础建设",
        "weeks": "W1-W6",
        "desc": "动作固化+引体变式适应, 蛋白165g/天, 训练日2300/休息日2100kcal, 真空腹30s起步",
    },
    2: {
        "name": "体成分重组",
        "weeks": "W7-W14",
        "desc": "容量递进+离心慢速补偿, 真空腹每日60s×5, LISS≤2次/周, 减载W8/W13(-40%)",
    },
    3: {
        "name": "线条雕刻",
        "weeks": "W15-W22",
        "desc": "碳水循环(高碳日280g→中碳日200g→低碳日150g→休息日130g), HIIT≤2次/周, 减载W17/W21",
    },
}
