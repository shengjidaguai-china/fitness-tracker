"""UI 设计令牌与侧栏壳 — 美化改版的契约测试"""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel


@pytest.fixture(scope="module")
def app():
    _app = QApplication.instance() or QApplication([])
    yield _app


def test_surface_and_nav_styles_use_palette():
    from fitness_pkg.constants import COLORS, build_global_stylesheet, nav_button_style, surface_style

    surf = surface_style()
    assert COLORS["card"] in surf
    assert COLORS["border"] in surf
    assert "border-radius" in surf

    nav = nav_button_style()
    assert "QPushButton:checked" in nav
    assert COLORS["primary"] in nav

    qss = build_global_stylesheet()
    assert "QTabBar::tab" in qss
    assert "QScrollArea" in qss
    assert COLORS["bg"] in qss


def test_sidebar_shell_switches_pages(app):
    from fitness_pkg.shell import SidebarShell

    shell = SidebarShell()
    a = QLabel("page-a")
    b = QLabel("page-b")
    shell.add_page(a, "仪表盘", "nav_dashboard")
    shell.add_page(b, "趋势分析", "nav_trend")

    assert shell.count() == 2
    assert shell.tabText(0) == "仪表盘"
    assert shell.currentIndex() == 0
    assert shell.currentWidget() is a

    shell.setCurrentIndex(1)
    assert shell.currentIndex() == 1
    assert shell.currentWidget() is b
    assert shell.nav_buttons[1].isChecked()
    assert not shell.nav_buttons[0].isChecked()
