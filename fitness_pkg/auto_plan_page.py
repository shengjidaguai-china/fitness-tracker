"""
自动方案页 (v9.2 新增, Issue #5)

「体测 → 训练计划 + 动作」与「月度伙食费 → 每日饮食 + 补剂」的图形入口。
只做参数收集与文本渲染, 规则全部在 `fitness_pkg/auto_plan.py` 里, 保证 GUI 与 CLI 同源。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .constants import COLORS

try:
    from .auto_plan import (
        generate_diet_markdown,
        generate_diet_plan,
        generate_training_markdown,
        generate_training_plan,
        validate_body_inputs,
        validate_budget,
    )

    AUTO_PLAN_AVAILABLE = True
except Exception:  # 依赖缺失时页面降级, 不阻断整个应用
    AUTO_PLAN_AVAILABLE = False


class AutoPlanPage(QWidget):
    """输入当前/目标体测与预算, 一键生成训练计划 + 饮食与补剂方案"""

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        if not AUTO_PLAN_AVAILABLE:
            lbl = QLabel("⚠ 自动方案模块未加载 (fitness_pkg/auto_plan.py)")
            lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 14px;")
            outer.addWidget(lbl)
            return

        header = QLabel("🧭 自动方案 — 体测 + 预算 一键生成")
        header.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['primary']}; padding: 8px;")
        outer.addWidget(header)

        sub = QLabel("体测输入 → 训练计划与动作 · 预算输入 → 每日饮食与补剂 (先保蛋白, 再到补剂)")
        sub.setStyleSheet(f"color: {COLORS['subtext']}; padding: 0 0 8px;")
        outer.addWidget(sub)

        body = QHBoxLayout()
        body.setSpacing(12)

        # ── 左: 输入区 ──
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFixedWidth(340)
        left.setStyleSheet("QScrollArea { border: none; }")
        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.in_weight = self._spin(30, 250, 70, " kg")
        self.in_bodyfat = self._spin(3, 60, 22, " %")
        self.in_target_weight = self._spin(30, 250, 65, " kg")
        self.in_target_bodyfat = self._spin(3, 60, 15, " %")
        self.in_height = self._spin(140, 220, 175, " cm")
        self.in_age = QSpinBox()
        self.in_age.setRange(16, 80)
        self.in_age.setValue(28)
        self.in_sex = QComboBox()
        self.in_sex.addItems(["male", "female"])
        self.in_training_age = QSpinBox()
        self.in_training_age.setRange(0, 400)
        self.in_training_age.setValue(0)
        self.in_training_age.setToolTip("训练年限 (月), 影响 P0–L3 分层")
        self.in_budget = self._spin(300, 20000, 1500, " 元/月")

        form.addRow("当前体重", self.in_weight)
        form.addRow("当前体脂率", self.in_bodyfat)
        form.addRow("目标体重", self.in_target_weight)
        form.addRow("目标体脂率", self.in_target_bodyfat)
        form.addRow("身高", self.in_height)
        form.addRow("年龄", self.in_age)
        form.addRow("性别", self.in_sex)
        form.addRow("训练年限(月)", self.in_training_age)
        form.addRow("月度伙食费", self.in_budget)

        hint = QLabel(
            "口径: 减脂周速度上限 1% 体重 / 增肌 0.25%; 周组数按 P0–L3 起始区间; 热量只是起点, 2 周后按体重趋势校准"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['subtext']}; padding: 4px;")
        form.addRow(hint)

        self.btn_generate = QPushButton("⚙ 生成方案")
        self.btn_generate.setStyleSheet(
            f"background-color: {COLORS['primary']}; color: white; padding: 9px; font-weight: bold;"
        )
        self.btn_generate.clicked.connect(self._generate)
        form.addRow(self.btn_generate)

        left.setWidget(form_host)
        body.addWidget(left)

        # ── 右: 输出区 ──
        right = QVBoxLayout()
        self.out_training = QTextEdit()
        self.out_training.setReadOnly(True)
        self.out_training.setPlaceholderText("点「生成方案」后, 这里显示本次周期的训练计划与每日动作")
        self.out_training.setStyleSheet(self._box_style())

        self.out_diet = QTextEdit()
        self.out_diet.setReadOnly(True)
        self.out_diet.setPlaceholderText("填写月度伙食费后, 这里显示每日饮食计划与补剂方案")
        self.out_diet.setStyleSheet(self._box_style())

        right.addWidget(QLabel("训练计划与动作"))
        right.addWidget(self.out_training, 1)
        right.addWidget(QLabel("每日饮食与补剂"))
        right.addWidget(self.out_diet, 1)
        body.addLayout(right, 1)

        outer.addLayout(body, 1)
        self._generate()

    @staticmethod
    def _spin(low: float, high: float, value: float, suffix: str) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(low, high)
        box.setDecimals(1)
        box.setValue(value)
        box.setSuffix(suffix)
        return box

    @staticmethod
    def _box_style() -> str:
        return (
            f"background-color: {COLORS['card']}; border: 1px solid {COLORS['border']}; "
            "border-radius: 6px; padding: 8px;"
        )

    def _generate(self):
        check = validate_body_inputs(
            self.in_weight.value(),
            self.in_bodyfat.value(),
            self.in_target_weight.value(),
            self.in_target_bodyfat.value(),
            self.in_height.value(),
            self.in_age.value(),
            self.in_sex.currentText(),
        )
        if not check["ok"]:
            self.out_training.setPlainText("\n".join(f"⚠ {e}" for e in check["errors"]))
            self.out_diet.setPlainText("")
            return

        training = generate_training_plan(
            current_weight=check["current_weight"],
            current_bodyfat=check["current_bodyfat"],
            target_weight=check["target_weight"],
            target_bodyfat=check["target_bodyfat"],
            height_cm=check["height_cm"],
            sex=check["sex"],
            training_age_months=self.in_training_age.value(),
        )
        warn = "\n".join(f"⚠ {w}" for w in check["warnings"])
        self.out_training.setPlainText((warn + "\n\n" if warn else "") + generate_training_markdown(training))

        budget = validate_budget(self.in_budget.value())
        if not budget["ok"]:
            self.out_diet.setPlainText("\n".join(f"⚠ {e}" for e in budget["errors"]))
            return
        diet = generate_diet_plan(
            budget["monthly_budget"],
            check["current_weight"],
            check["current_bodyfat"],
            check["target_weight"],
            check["sex"],
        )
        self.out_diet.setPlainText(generate_diet_markdown(diet))
