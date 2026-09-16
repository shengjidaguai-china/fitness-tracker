"""
体脂体重监控 + 健身计划软件 v9.0 — PySide6 重构版
基于市场主流健身软件(Keep/Fitbod/Hevy/Strong)特性优化
v9.0: 更新到居家平替计划 v3.0 (单杠+哑铃版) + 海豹徒手 + 囚徒健身体系
v3.0.1: GUI解析版正式并入海豹徒手(Navy SEAL 六支柱+SEAL 500)与囚徒健身(CC 六艺十阶)两大补位体系

功能模块:
  1. 📊 体测仪表盘 — 12项体测指标 + 快速录入 + 历史记录
  2. 📈 趋势分析 — 7日EMA平滑曲线 + 目标达标日预测 + 体成分饼图
  3. 🏋️ 动作示范库 — 38个动作 GIF动画 + 中文步骤教学 + 肌群信息
  4. 📅 训练计划 — 22周居家平替塑形 + 三阶段周期化 + 点击动作看示范
  5. 🍽 饮食与补剂 — 三阶段营养方案 + 五餐明细 + 补剂表 + 饮水指南

技术栈: PySide6 + matplotlib + pandas + Pillow
数据源: exercises-dataset (GitHub: yuppiez99999/exercises-dataset)
"""

import os
import sys

from PySide6.QtGui import QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QMainWindow

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitness_modules import (
    AI_COACH_AVAILABLE,
    COLORS,
    AICoachPage,
    BodyDataModel,
    DashboardPage,
    ExerciseLibrary,
    ExerciseLibraryPage,
    NutritionPage,
    TrainingPlanPage,
    TrainingPlanParser,
    TrendChartPage,
)
from fitness_pkg.constants import build_global_stylesheet
from fitness_pkg.shell import SidebarShell

# 应用图标（随 PyInstaller datas 打包）
APP_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fitness_icon.ico")


class MainWindow(QMainWindow):
    """主窗口 — 左侧导航 + 内容栈"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("健身监控 v9.0 — 居家平替 v3.0 · 体测/动作库/训练计划/饮食 · AI 教练")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setWindowIcon(QIcon(APP_ICON))

        # 初始化数据模型
        self.body_model = BodyDataModel()
        self.exercise_lib = ExerciseLibrary()
        self.training_plan = TrainingPlanParser()

        # 构建UI
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        self.tabs = SidebarShell()
        self.setCentralWidget(self.tabs)
        self.lbl_quick_stats = self.tabs.lbl_quick_stats

        self.page_dashboard = DashboardPage(self.body_model)
        self.page_dashboard.record_added.connect(self._on_data_changed)
        self.tabs.add_page(self.page_dashboard, "仪表盘", "nav_dashboard", "📊")

        self.page_trend = TrendChartPage(self.body_model)
        self.tabs.add_page(self.page_trend, "趋势分析", "nav_trend", "📈")

        self.page_exercises = ExerciseLibraryPage(self.exercise_lib)
        n_ex = len(self.exercise_lib.exercises)
        self.tabs.add_page(self.page_exercises, f"动作库 ({n_ex})", "nav_exercises", "🏋️")

        self.page_plan = TrainingPlanPage(self.training_plan, self.exercise_lib)
        self.tabs.add_page(self.page_plan, "训练计划", "nav_plan", "📅")

        self.page_nutrition = NutritionPage()
        self.tabs.add_page(self.page_nutrition, "饮食与补剂", "nav_nutrition", "🍽")

        if AI_COACH_AVAILABLE:
            self.page_coach = AICoachPage()
            self.tabs.add_page(self.page_coach, "AI 教练", "nav_coach", "🤖")

        self.statusBar().showMessage(
            "就绪 · 居家平替 v3.0 单杠+哑铃" + (" · AI 教练已加载" if AI_COACH_AVAILABLE else "")
        )

    def _update_status(self):
        """更新侧栏快速统计"""
        stats = self.body_model.get_stats()
        if stats["count"] == 0:
            self.lbl_quick_stats.setText("暂无体测记录")
            return
        w = stats["cur_weight"]
        f = stats["cur_fat"]
        fat_text = f"\n体脂 {f:.1f}%" if f == f else ""
        self.lbl_quick_stats.setText(f"当前 {w:.1f} kg{fat_text}\n{stats['count']} 条记录")

    def _on_data_changed(self):
        """数据变化时刷新所有页面"""
        self.page_dashboard.refresh()
        self.page_trend._draw()
        self._update_status()
        self.statusBar().showMessage("数据已更新", 3000)

    def closeEvent(self, event):
        """关闭时保存"""
        self.body_model.save()
        event.accept()


# ═══════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("健身监控 v9.0")

    # Fusion 引擎统一观感（跨 Windows 主题表现一致）
    app.setStyle("Fusion")

    # 全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 调色板（作用于未单独内联样式的系统控件与对话框）
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(COLORS["bg"]))
    pal.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    pal.setColor(QPalette.Base, QColor(COLORS["card"]))
    pal.setColor(QPalette.AlternateBase, QColor(COLORS["table_alt"]))
    pal.setColor(QPalette.Text, QColor(COLORS["text"]))
    pal.setColor(QPalette.Button, QColor(COLORS["card"]))
    pal.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(COLORS["card"]))
    pal.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    pal.setColor(QPalette.Highlight, QColor(COLORS["primary"]))
    pal.setColor(QPalette.HighlightedText, QColor(COLORS["appbar_text"]))
    app.setPalette(pal)

    # 全局现代样式（滚动条 / Tab / 输入框 / 下拉 / 默认按钮）
    app.setStyleSheet(build_global_stylesheet())

    icon = QIcon(APP_ICON)
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
