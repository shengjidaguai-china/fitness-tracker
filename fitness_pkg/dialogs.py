"""
动作详情弹窗 (v7.0 模块化拆分)
ExerciseDetailDialog: QMovie 播放 GIF + 循环控制 + 速度选择 + 自适应缩放
"""

from typing import Dict

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .constants import COLORS, button_style, player_panel_style, player_text_style
from .exercise_lib import ExerciseLibrary
from .shell import apply_surface


class ExerciseDetailDialog(QDialog):
    """动作详情弹窗 — QMovie播GIF + 循环控制 + 速度选择 + 自适应缩放"""

    def __init__(self, exercise: Dict, exercise_lib: ExerciseLibrary, parent=None):
        super().__init__(parent)
        self.exercise = exercise
        self.lib = exercise_lib
        self.movie = None
        self._speed = 100  # 百分比, 100=原速
        self._speed_buttons: list = []
        self._build_ui()

    def _build_ui(self):
        name = self.exercise.get("name_cn", "未知动作")
        self.setWindowTitle(f"动作示范 — {name}")
        self.setMinimumSize(780, 620)
        self.setStyleSheet(f"background-color: {COLORS['bg']}; color: {COLORS['text']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel(name)
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 2px 0;")
        layout.addWidget(title)

        # 英文名 + 器材
        en_name = self.exercise.get("name_en", "")
        equip = self.exercise.get("equipment", "")
        target = self.exercise.get("target", "")
        info_parts = [f"English: {en_name}"] if en_name else []
        if equip:
            info_parts.append(f"器材: {equip}")
        if target:
            info_parts.append(f"目标: {target}")
        info = QLabel("    |    ".join(info_parts))
        info.setStyleSheet(f"color: {COLORS['subtext']}; padding: 0 10px; font-size: 11px;")
        layout.addWidget(info)

        # 主体: 左GIF + 右信息
        body = QHBoxLayout()
        body.setSpacing(12)

        # 左侧GIF区域 — 深色"播放器画框"
        gif_frame = QFrame()
        gif_frame.setStyleSheet(player_panel_style())
        gif_frame.setMinimumSize(340, 340)
        gif_layout = QVBoxLayout(gif_frame)
        gif_layout.setContentsMargins(10, 10, 10, 6)
        gif_layout.setSpacing(6)

        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setMinimumSize(320, 280)
        self.gif_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gif_label.setStyleSheet(player_text_style(font_size=13))
        gif_layout.addWidget(self.gif_label)

        # 帧信息标签
        self.frame_info = QLabel("")
        self.frame_info.setAlignment(Qt.AlignCenter)
        self.frame_info.setStyleSheet(player_text_style(font_size=9))
        gif_layout.addWidget(self.frame_info)

        body.addWidget(gif_frame, stretch=4)

        # 右侧信息面板
        info_frame = QFrame()
        apply_surface(info_frame)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(6)

        muscle = self.exercise.get("muscle_group", "")
        secondary = self.exercise.get("secondary_muscles", [])
        sec_str = ", ".join(secondary) if isinstance(secondary, list) else str(secondary)

        musc_title = QLabel("肌群信息")
        musc_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        musc_title.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        info_layout.addWidget(musc_title)

        for label, value, color in [
            ("主肌群", muscle, COLORS["success"]),
            ("协同肌群", sec_str, COLORS["warning"]),
        ]:
            if value:
                row = QLabel(f"{label}: {value}")
                row.setFont(QFont("Microsoft YaHei", 10))
                row.setStyleSheet(f"color: {color}; padding: 2px 4px;")
                row.setWordWrap(True)
                info_layout.addWidget(row)

        # 分隔
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"color: {COLORS['border']}; margin: 4px 0;")
        info_layout.addWidget(sep1)

        # 步骤标题
        steps_title = QLabel("动作步骤")
        steps_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        steps_title.setStyleSheet(f"color: {COLORS['purple']};")
        info_layout.addWidget(steps_title)

        # 步骤列表
        steps = self.exercise.get("instruction_steps_zh", [])
        if not steps:
            instructions = self.exercise.get("instructions_zh", "")
            if instructions:
                steps = [s.strip() for s in instructions.replace("\n", "。").split("。") if s.strip()]

        step_scroll = QScrollArea()
        step_scroll.setWidgetResizable(True)
        step_scroll.setStyleSheet("QScrollArea {{ border: none; background-color: transparent; }}")
        step_widget = QWidget()
        step_layout = QVBoxLayout(step_widget)
        step_layout.setSpacing(4)
        step_layout.setContentsMargins(0, 0, 0, 0)
        for i, step in enumerate(steps, 1):
            sl = QLabel(f"{i}. {step}")
            sl.setWordWrap(True)
            sl.setStyleSheet(f"color: {COLORS['text']}; padding: 2px 4px; font-size: 10px;")
            step_layout.addWidget(sl)
        step_layout.addStretch()
        step_scroll.setWidget(step_widget)
        info_layout.addWidget(step_scroll, stretch=1)

        body.addWidget(info_frame, stretch=3)
        layout.addLayout(body, stretch=1)

        # 底部控制栏
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        # 播放/暂停
        self.btn_play = QPushButton("暂停")
        self.btn_play.setFixedHeight(32)
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_play.setStyleSheet(button_style(COLORS["primary"], padding="6px 22px", font_size=12))
        ctrl.addWidget(self.btn_play)

        # 重新播放
        btn_restart = QPushButton("重播")
        btn_restart.setFixedHeight(32)
        btn_restart.clicked.connect(self._restart)
        btn_restart.setStyleSheet(button_style(COLORS["success"], padding="6px 22px", font_size=12))
        ctrl.addWidget(btn_restart)

        ctrl.addSpacing(16)

        # 速度控制标签
        speed_label = QLabel("速度:")
        speed_label.setStyleSheet(f"color: {COLORS['subtext']}; font-size: 10px;")
        ctrl.addWidget(speed_label)

        for pct, lbl in [(50, "0.5x"), (75, "0.75x"), (100, "1x"), (150, "1.5x"), (200, "2x")]:
            btn = QPushButton(lbl)
            btn.setFixedHeight(28)
            btn.setFixedWidth(44)
            active = pct == 100
            btn.setCheckable(True)
            btn.setChecked(active)
            btn.clicked.connect(lambda checked, s=pct, b=btn: self._set_speed(s, b))
            btn.setStyleSheet(self._speed_btn_style(active))
            btn.setProperty("speed_btn", True)
            self._speed_buttons.append(btn)
            ctrl.addWidget(btn)

        ctrl.addStretch()

        # 帧计数
        self.lbl_frame_count = QLabel("")
        self.lbl_frame_count.setStyleSheet(f"color: {COLORS['subtext']}; font-size: 9px;")
        ctrl.addWidget(self.lbl_frame_count)

        layout.addLayout(ctrl)

        self._load_gif()

    @staticmethod
    def _speed_btn_style(active: bool) -> str:
        """倍速小按钮 — 选中绿色实心 / 未选白底描边"""
        if active:
            return f"""
                QPushButton {{ background-color: {COLORS["success"]}; color: {COLORS["appbar_text"]};
                              border: 1px solid {COLORS["success"]}; border-radius: 6px;
                              padding: 3px 8px; font-size: 10px; font-weight: 700; }}
                QPushButton:hover {{ background-color: {COLORS["success_dark"]}; }}
            """
        return f"""
            QPushButton {{ background-color: {COLORS["card"]}; color: {COLORS["text"]};
                          border: 1px solid {COLORS["border"]}; border-radius: 6px;
                          padding: 3px 8px; font-size: 10px; font-weight: 600; }}
            QPushButton:hover {{ background-color: {COLORS["success_soft"]};
                                border-color: {COLORS["success"]}; }}
            QPushButton:checked {{ background-color: {COLORS["success"]}; color: {COLORS["appbar_text"]};
                                   border-color: {COLORS["success"]}; }}
        """

    def _load_gif(self):
        """加载GIF动画 — 带错误恢复和帧缓存"""
        media_id = self.exercise.get("media_id", "")
        gif_path = self.lib.gif_path(media_id)
        if gif_path is None:
            self.gif_label.setText("无动作示范GIF\n\n(该动作未匹配到示范数据)")
            self.gif_label.setStyleSheet(player_text_style(font_size=13, padding="20px"))
            self.btn_play.setEnabled(False)
            self.lbl_frame_count.setText("")
            return

        from PySide6.QtGui import QMovie

        try:
            self.movie = QMovie(gif_path)
            if not self.movie.isValid():
                raise ValueError("无效GIF文件")

            # 缓存所有帧以提高播放流畅度
            self.movie.setCacheMode(QMovie.CacheAll)
            # 自适应缩放到label大小
            gif_size = self.movie.currentImage().size()
            display_size = min(340, max(280, gif_size.width()))
            self.movie.setScaledSize(QSize(display_size, display_size))

            self.movie.frameChanged.connect(self._on_frame_changed)
            self.movie.finished.connect(self._on_loop_complete)
            self.movie.stateChanged.connect(self._on_state_changed)

            self.gif_label.setMovie(self.movie)
            self.movie.start()

            total = self.movie.frameCount()
            self.lbl_frame_count.setText(f"共 {total} 帧")
            self.frame_info.setText(f"分辨率: {gif_size.width()}x{gif_size.height()}")

        except Exception as e:
            self.gif_label.setText(f"GIF加载失败\n\n(文件可能已损坏)\n\n{str(e)[:80]}")
            self.gif_label.setStyleSheet(player_text_style(error=True, font_size=11, padding="20px"))
            self.btn_play.setEnabled(False)
            self.lbl_frame_count.setText("")
            if self.movie:
                self.movie = None

    def _on_frame_changed(self, frame: int):
        if self.movie:
            total = self.movie.frameCount()
            if total > 0:
                self.frame_info.setText(f"帧: {frame + 1}/{total}")

    def _on_loop_complete(self):
        """循环结束自动重播"""
        if self.movie:
            self.movie.start()

    def _on_state_changed(self, state):
        from PySide6.QtGui import QMovie

        if state == QMovie.Running:
            self.btn_play.setText("暂停")
        elif state == QMovie.NotRunning:
            self.btn_play.setText("播放")

    def _toggle_play(self):
        if self.movie is None:
            return
        from PySide6.QtGui import QMovie

        if self.movie.state() == QMovie.Running:
            self.movie.setPaused(True)
            self.btn_play.setText("播放")
        else:
            self.movie.setPaused(False)
            self.btn_play.setText("暂停")

    def _restart(self):
        if self.movie is None:
            return
        self.movie.stop()
        self.movie.start()

    def _set_speed(self, pct: int, btn: QPushButton):
        """设置播放速度, 并同步速度按钮高亮状态"""
        if self.movie is None:
            return
        self._speed = pct
        self.movie.setSpeed(pct)
        # 更新速度按钮高亮: 仅当前选中的为绿色
        for b in self._speed_buttons:
            active = b is btn
            b.setChecked(active)
            b.setStyleSheet(self._speed_btn_style(active))
        if pct != 100 and self.movie:
            self.frame_info.setText(f"速度: {pct / 100:.2f}x")

    def closeEvent(self, event):
        """关闭窗口时清理QMovie资源"""
        if self.movie:
            self.movie.stop()
            self.gif_label.clear()
            self.movie.deleteLater()
            self.movie = None
        super().closeEvent(event)
