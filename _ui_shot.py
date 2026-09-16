"""离屏渲染各页面截图，用于视觉验证。"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fitness_pkg.constants import build_global_stylesheet

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fitness_app_main", os.path.join(ROOT, "体脂体重监控_完整版.py"))
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
MainWindow = mod.MainWindow

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(build_global_stylesheet())

win = MainWindow()
win.resize(1440, 920)
win.show()
app.processEvents()

tabs = win.tabs
for i in range(min(tabs.count(), 6)):
    tabs.setCurrentIndex(i)
    for _ in range(4):
        app.processEvents()
    win.grab().save(os.path.join(ROOT, f"_shot_tab{i}.png"))
    print(f"saved _shot_tab{i}.png [{tabs.tabText(i)}]")

try:
    found = win.exercise_lib.search("")
    ex = found[0] if found else win.exercise_lib.exercises[0]
    from fitness_pkg.dialogs import ExerciseDetailDialog

    dlg = ExerciseDetailDialog(ex, win.exercise_lib, win)
    dlg.resize(980, 640)
    dlg.show()
    for _ in range(6):
        app.processEvents()
    dlg.grab().save(os.path.join(ROOT, "_shot_dialog.png"))
    print("saved _shot_dialog.png")
except Exception as e:
    print("dialog shot failed:", e)

app.quit()
