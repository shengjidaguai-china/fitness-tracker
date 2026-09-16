"""应用壳层 — 左侧导航 + 页面标题条。"""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .constants import COLORS, PAGE_MARGINS, PAGE_SPACING, nav_button_style, surface_style


def apply_shadow(widget: QWidget, blur: int = 18, y_offset: int = 3, alpha_hex: str = "28") -> None:
    """给控件加柔和投影 (v10.2 卡片层次感) — alpha_hex: 28≈16% 透明度"""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, y_offset)
    eff.setColor(QColor(46, 39, 32, int(alpha_hex, 16)))
    widget.setGraphicsEffect(eff)


class SidebarShell(QWidget):
    """左侧导航 + 内容栈。保留 count / setCurrentIndex / tabText 供截图脚本使用。"""

    currentChanged = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.nav_buttons: List[QPushButton] = []
        self._titles: List[str] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("appSidebar")
        sidebar.setFixedWidth(212)
        sidebar.setStyleSheet(
            f"QFrame#appSidebar {{ background-color: {COLORS['card']}; border-right: 1px solid {COLORS['border']}; }}"
        )
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 20, 16, 18)
        side.setSpacing(6)

        brand = QLabel("健身监控")
        brand.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        brand.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        side.addWidget(brand)

        tag = QLabel("居家平替 · 体测与计划")
        tag.setWordWrap(True)
        tag.setStyleSheet(f"color: {COLORS['subtext']}; font-size: 11px; background: transparent; padding-bottom: 10px;")
        side.addWidget(tag)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        side.addWidget(sep)

        self._nav_box = QVBoxLayout()
        self._nav_box.setSpacing(6)
        side.addLayout(self._nav_box)
        side.addStretch(1)

        self.lbl_quick_stats = QLabel("暂无数据")
        self.lbl_quick_stats.setWordWrap(True)
        self.lbl_quick_stats.setStyleSheet(
            f"color: {COLORS['text']}; background-color: {COLORS['bg']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 14px; "
            f"padding: 12px 14px; font-size: 12px; font-weight: 600;"
        )
        side.addWidget(self.lbl_quick_stats)

        ver = QLabel("v9.0")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {COLORS['subtext']}; font-size: 10px; background: transparent; padding-top: 8px;")
        side.addWidget(ver)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['bg']};")
        self.stack.currentChanged.connect(self.currentChanged.emit)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)

    def add_page(self, widget: QWidget, title: str, object_name: str = "", icon: str = "") -> int:
        idx = self.stack.addWidget(widget)
        label = f"{icon}  {title}".strip() if icon else title
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(nav_button_style())
        if object_name:
            btn.setObjectName(object_name)
            btn.setAccessibleName(title)
        btn.clicked.connect(lambda _=False, i=idx: self.setCurrentIndex(i))
        self._group.addButton(btn, idx)
        self._nav_box.addWidget(btn)
        self.nav_buttons.append(btn)
        self._titles.append(title)
        if idx == 0:
            btn.setChecked(True)
        return idx

    def count(self) -> int:
        return self.stack.count()

    def currentIndex(self) -> int:
        return self.stack.currentIndex()

    def currentWidget(self) -> QWidget:
        return self.stack.currentWidget()

    def setCurrentIndex(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def tabText(self, index: int) -> str:
        if 0 <= index < len(self._titles):
            return self._titles[index]
        return ""


def apply_page_layout(layout: QVBoxLayout) -> None:
    layout.setContentsMargins(*PAGE_MARGINS)
    layout.setSpacing(PAGE_SPACING)


def make_page_heading(title: str, subtitle: str = "") -> QWidget:
    wrap = QWidget()
    wrap.setStyleSheet("background: transparent;")
    v = QVBoxLayout(wrap)
    v.setContentsMargins(0, 0, 0, 2)
    v.setSpacing(4)
    t = QLabel(title)
    t.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
    t.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
    v.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(f"color: {COLORS['subtext']}; font-size: 12px; background: transparent;")
        v.addWidget(s)
    return wrap


def kpi_card_style(accent: str) -> str:
    return (
        f"background-color: {COLORS['card']}; border: 1px solid {COLORS['border']}; "
        f"border-left: 4px solid {accent}; border-radius: 14px;"
    )


def apply_surface(frame: QWidget) -> None:
    frame.setStyleSheet(surface_style())
    frame.setAttribute(Qt.WA_StyledBackground, True)
