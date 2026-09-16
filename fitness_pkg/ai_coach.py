"""
AI 教练页面 (v7.0 模块化拆分)
基于 Lzheng-fitness 知识库的增肌规划: 分层评估/周期生成/训练复盘/停训接回/短版训练。
"""

import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .constants import COLORS

# AI 教练引擎 — 软依赖, 缺失时降级 (原 fitness_modules.py L2816-2826)
try:
    from ai_coach_engine import (
        LEVEL_DESC,
        AthleteProfile,
        TrainingLog,
        assess_overall_level,
        build_weekly_volume_report,
        export_cycle_to_markdown,
        generate_return_plan,
        generate_short_plan,
        generate_short_version,
        generate_strength_cycle,
        load_profile,
        load_reviews,
        review_report,
        review_training,
        save_cycle,
        save_profile,
        save_review,
    )

    AI_COACH_AVAILABLE = True
except Exception:
    AI_COACH_AVAILABLE = False

# 训练科学规则层 (v9.1) — 软依赖, 缺失时页面仍可运行但缺少自动化提示
try:
    from ai_coach_engine import audit_movement_gaps, evaluate_deload_signals

    SCIENCE_UI_AVAILABLE = True
except Exception:
    evaluate_deload_signals = None
    audit_movement_gaps = None
    SCIENCE_UI_AVAILABLE = False


class AICoachPage(QWidget):
    """AI 教练页面 — 5 个子功能: 分层评估/周期生成/训练复盘/停训接回/短版训练"""

    def __init__(self):
        super().__init__()
        self.profile = load_profile() or AthleteProfile()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        if not AI_COACH_AVAILABLE:
            lbl = QLabel("⚠ AI 教练引擎未加载 (ai_coach_engine.py)")
            lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 14px;")
            layout.addWidget(lbl)
            return

        header = QLabel("🤖 AI 教练 — 基于 Lzheng-fitness 知识库")
        header.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['primary']}; padding: 8px;")
        layout.addWidget(header)

        sub = QLabel("P0-L3 分层 · 力量周期化 · 训练复盘 · 停训接回 · 最低执行版本")
        sub.setStyleSheet(f"color: {COLORS['subtext']}; padding-bottom: 8px;")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_profile_tab(), "📋 建档与分层")
        self.tabs.addTab(self._build_cycle_tab(), "📅 力量周期")
        self.tabs.addTab(self._build_review_tab(), "📝 训练复盘")
        self.tabs.addTab(self._build_return_tab(), "↩️ 停训接回")
        self.tabs.addTab(self._build_short_tab(), "⏱ 短版训练")

    # ─── 子页1: 建档与分层评估 ───
    def _build_profile_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea {{ border: none; }}")

        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.in_name = QLineEdit(self.profile.name)
        self.in_age = QSpinBox()
        self.in_age.setRange(10, 80)
        self.in_age.setValue(self.profile.age or 30)
        self.in_height = QDoubleSpinBox()
        self.in_height.setRange(100, 250)
        self.in_height.setValue(self.profile.height_cm or 175)
        self.in_weight = QDoubleSpinBox()
        self.in_weight.setRange(30, 200)
        self.in_weight.setValue(self.profile.weight_kg or 67)
        self.in_bf = QDoubleSpinBox()
        self.in_bf.setRange(3, 60)
        self.in_bf.setValue(self.profile.body_fat_pct or 17)
        self.in_years = QDoubleSpinBox()
        self.in_years.setRange(0, 30)
        self.in_years.setSingleStep(0.5)
        self.in_years.setValue(self.profile.training_years or 0)
        self.in_sessions = QSpinBox()
        self.in_sessions.setRange(1, 7)
        self.in_sessions.setValue(self.profile.weekly_sessions or 4)
        self.in_minutes = QSpinBox()
        self.in_minutes.setRange(10, 180)
        self.in_minutes.setValue(self.profile.session_minutes or 60)
        self.in_goal = QComboBox()
        self.in_goal.addItems(["增肌", "减脂", "力量", "综合"])
        self.in_goal.setCurrentText(self.profile.goal or "增肌")

        form.addRow("姓名", self.in_name)
        form.addRow("年龄", self.in_age)
        form.addRow("身高(cm)", self.in_height)
        form.addRow("体重(kg)", self.in_weight)
        form.addRow("体脂率(%)", self.in_bf)
        form.addRow("训练年限(年)", self.in_years)
        form.addRow("每周训练次数", self.in_sessions)
        form.addRow("单次时长(分钟)", self.in_minutes)
        form.addRow("主要目标", self.in_goal)

        # v9.1: 训练量按等级自动给出起始区间 (Helms: 每肌群/动作模式每周 10–20 组起始区间)
        self.in_weekly_sets = QSpinBox()
        self.in_weekly_sets.setRange(0, 40)
        self.in_weekly_sets.setValue(12)
        self.in_weekly_sets.setToolTip("当前每个肌群的每周总组数, 用于区间校验")
        form.addRow("每肌群周组数", self.in_weekly_sets)

        hint = QLabel(
            "科学依据: Helms 训练金字塔 (周组数 10–20 起始区间 / 组间休息下限) · "
            "Schoenfeld (多数组保留 1–2 RIR, 力竭只在末组) · "
            "Nuckols (训练量是可检验剂量, 用表现而非公式定负荷)"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['subtext']}; padding: 4px;")
        form.addRow(hint)

        btn_save = QPushButton("💾 保存建档并评估分层")
        btn_save.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(self._save_profile)
        form.addRow(btn_save)

        self.lbl_level_result = QTextEdit()
        self.lbl_level_result.setReadOnly(True)
        self.lbl_level_result.setMinimumHeight(280)
        self.lbl_level_result.setStyleSheet(
            f"QTextEdit {{ background-color: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px; }}"
        )
        form.addRow("分层评估结果", self.lbl_level_result)

        scroll.setWidget(w)
        return scroll

    def _save_profile(self):
        self.profile.name = self.in_name.text()
        self.profile.age = self.in_age.value()
        self.profile.height_cm = self.in_height.value()
        self.profile.weight_kg = self.in_weight.value()
        self.profile.body_fat_pct = self.in_bf.value()
        self.profile.training_years = self.in_years.value()
        self.profile.weekly_sessions = self.in_sessions.value()
        self.profile.session_minutes = self.in_minutes.value()
        self.profile.goal = self.in_goal.currentText()
        save_profile(self.profile)

        level = assess_overall_level(self.profile)
        html = f"<h3>整体训练等级: {level}</h3><p>{LEVEL_DESC[level]}</p>"
        html += "<h4>建议:</h4><ul>"
        if level == "P0":
            html += "<li>首要目标: 安全、可重复、建立基准</li><li>使用固定器械或支撑动作</li><li>每次训练记录重量和感觉</li>"
        elif level == "L1":
            html += "<li>可逐次或隔次推进</li><li>使用线性或双重渐进</li><li>一次只改变一个主要变量</li>"
        elif level == "L2":
            html += "<li>按周管理训练量、强度和恢复</li><li>可使用多周周期</li><li>关注疲劳管理</li>"
        else:
            html += "<li>按阶段规划进步</li><li>需要更高专项性</li><li>使用完整积累→强度→实现→减量周期</li>"
        html += "</ul>"

        # v9.1: 周组数区间校验 + 关键原则 (来自训练科学规则层)
        try:
            report = build_weekly_volume_report(level, {"当前计划": self.in_weekly_sets.value()})
            item = report["items"][0]
            low, high = item["band"]
            color = {
                "合适": COLORS["success"],
                "偏少": COLORS["subtext"],
                "偏高": COLORS["warning"],
                "超出验证区间": COLORS["danger"],
            }.get(item["verdict"], COLORS["text"])
            html += (
                f'<h4>周组数校验</h4><p style="color:{color};">'
                f"当前 {item['planned_sets']} 组/周 → <b>{item['verdict']}</b> "
                f"(该等级起始区间 {low}–{high} 组, 上限 {item['ceiling']} 组)</p>"
                f"<p>{item['action']}</p>"
            )
        except Exception:
            pass

        html += (
            "<h4>本工具采用的判断口径</h4><ul>"
            "<li>RPE 10 = 0 RIR, 9 ≈ 1 RIR, 8 ≈ 2 RIR, 7 ≈ 3 RIR</li>"
            "<li>复合主项常规不做力竭; 孤立动作仅末组可接近力竭</li>"
            "<li>复合主项组间休息 ≥2.5 分钟, 孤立动作 ≥1.5 分钟</li>"
            "<li>一次训练只改变重量/次数/组数中的一个主要变量</li>"
            "<li>连续两次同类异常才怀疑周期结构, 单次状态差只维持观察</li>"
            "</ul>"
        )
        self.lbl_level_result.setHtml(html)

    # ─── 子页2: 力量周期生成 ───
    def _build_cycle_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("动作:"))
        self.in_cycle_move = QComboBox()
        self.in_cycle_move.addItems(["卧推", "深蹲", "硬拉", "推举", "引体向上", "划船"])
        ctrl.addWidget(self.in_cycle_move)

        ctrl.addWidget(QLabel("当前1RM(kg):"))
        self.in_cur_1rm = QDoubleSpinBox()
        self.in_cur_1rm.setRange(10, 500)
        self.in_cur_1rm.setValue(80)
        ctrl.addWidget(self.in_cur_1rm)

        ctrl.addWidget(QLabel("目标1RM(kg):"))
        self.in_tgt_1rm = QDoubleSpinBox()
        self.in_tgt_1rm.setRange(10, 500)
        self.in_tgt_1rm.setValue(90)
        ctrl.addWidget(self.in_tgt_1rm)

        ctrl.addWidget(QLabel("每周暴露:"))
        self.in_exposures = QSpinBox()
        self.in_exposures.setRange(1, 4)
        self.in_exposures.setValue(2)
        ctrl.addWidget(self.in_exposures)

        ctrl.addWidget(QLabel("训练等级:"))
        self.in_cycle_level = QComboBox()
        self.in_cycle_level.addItems(["P0", "L1", "L2", "L3"])
        self.in_cycle_level.setCurrentText("L1")
        ctrl.addWidget(self.in_cycle_level)
        layout.addLayout(ctrl)

        self.lbl_cycle_tip = QLabel(
            "周期长度按每周暴露次数与目标决定: 8 周 (目标单一/高频) · 10 周 (一般力量发展) · 12 周 (低频或需完整阶段)"
        )
        self.lbl_cycle_tip.setWordWrap(True)
        self.lbl_cycle_tip.setStyleSheet(f"color: {COLORS['subtext']}; padding: 4px;")
        layout.addWidget(self.lbl_cycle_tip)

        btn = QPushButton("🎯 生成力量周期")
        btn.setStyleSheet(f"background-color: {COLORS['success']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._gen_cycle)
        layout.addWidget(btn)

        self.cycle_result = QTextEdit()
        self.cycle_result.setReadOnly(True)
        layout.addWidget(self.cycle_result)
        return w

    def _gen_cycle(self):
        move = self.in_cycle_move.currentText()
        cur = self.in_cur_1rm.value()
        tgt = self.in_tgt_1rm.value()
        exp = self.in_exposures.value()

        exp = self.in_exposures.value()
        if tgt <= cur:
            self.cycle_result.setHtml(
                f'<p style="color:{COLORS["danger"]};">目标 1RM 需高于当前 1RM, 否则周期没有推进空间</p>'
            )
            return
        cycle = generate_strength_cycle(move, cur, tgt, exp, level=self.in_cycle_level.currentText())
        save_cycle(cycle)
        md_path = export_cycle_to_markdown(cycle)

        html = f"<h3>{move} 力量周期 — {cycle.weeks}周</h3>"
        html += f"<p>当前1RM: {cur}kg → 目标1RM: {tgt}kg (每周暴露 {exp} 次)</p>"
        html += "<h4>阶段分布</h4><ul>"
        for phase, n in cycle.phase_distribution.items():
            html += f"<li><b>{phase}</b>: {n}周</li>"
        html += "</ul>"

        first = cycle.days[0] if cycle.days else None
        if first is not None:
            if first.warmup_sets:
                warm = " / ".join(
                    f"{(w['label'] if w['weight'] <= 0 else str(w['weight']) + 'kg')} × {w['reps']}"
                    for w in first.warmup_sets
                )
                html += f"<h4>热身流程(每周一致)</h4><p>{warm}</p>"
            html += (
                f"<h4>执行口径</h4><ul>"
                f"<li>力竭使用: {first.failure_note}</li>"
                f"<li>组间休息: 复合主项 ≥2.5 分钟, 孤立动作 ≥1.5 分钟</li>"
                f"<li>节奏: 离心 {first.tempo.get('eccentric', '—')}, {first.tempo.get('note', '')}</li>"
                f"<li>回退组是计划内正式训练量, 顶上不去时用它替代, 不另外追加</li>"
                f"</ul>"
            )

        html += '<h4>每周安排</h4><table border="1" cellpadding="4" style="border-collapse:collapse;">'
        html += "<tr><th>周</th><th>阶段</th><th>顶组</th><th>回退组</th><th>RPE 路径</th></tr>"
        for d in cycle.days:
            top = d.sets[0] if d.sets else None
            back = d.sets[1] if len(d.sets) > 1 else None
            top_s = f"{top.weight}kg {top.sets}×{top.reps}" if top else "—"
            back_s = f"{back.weight}kg {back.sets}×{back.reps}" if back else "—"
            path_s = top.rpe_text if top else "—"
            html += f"<tr><td>{d.week}</td><td>{d.phase}</td><td>{top_s}</td><td>{back_s}</td><td>{path_s}</td></tr>"
        html += "</table>"
        html += f'<p style="color:{COLORS["success"]};">✓ 已保存至: {md_path}</p>'
        html += (
            '<p style="color:' + COLORS["subtext"] + ';">验证方式: 成功不等于最终 1RM, '
            "还要看目标负荷下的动作质量、RPE、完成率与恢复</p>"
        )
        self.cycle_result.setHtml(html)

    # ─── 子页3: 训练复盘 ───
    def _build_review_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("动作:"))
        self.in_rev_move = QLineEdit("卧推")
        ctrl.addWidget(self.in_rev_move)
        ctrl.addWidget(QLabel("重量(kg):"))
        self.in_rev_w = QDoubleSpinBox()
        self.in_rev_w.setRange(0, 500)
        self.in_rev_w.setValue(60)
        ctrl.addWidget(self.in_rev_w)
        ctrl.addWidget(QLabel("次数:"))
        self.in_rev_reps = QSpinBox()
        self.in_rev_reps.setRange(1, 30)
        self.in_rev_reps.setValue(8)
        ctrl.addWidget(self.in_rev_reps)
        ctrl.addWidget(QLabel("组数:"))
        self.in_rev_sets = QSpinBox()
        self.in_rev_sets.setRange(1, 10)
        self.in_rev_sets.setValue(4)
        ctrl.addWidget(self.in_rev_sets)
        ctrl.addWidget(QLabel("RPE:"))
        self.in_rev_rpe = QDoubleSpinBox()
        self.in_rev_rpe.setRange(1, 10)
        self.in_rev_rpe.setSingleStep(0.5)
        self.in_rev_rpe.setValue(7.5)
        ctrl.addWidget(self.in_rev_rpe)
        ctrl.addWidget(QLabel("目标次数:"))
        self.in_rev_target = QSpinBox()
        self.in_rev_target.setRange(1, 30)
        self.in_rev_target.setValue(10)
        ctrl.addWidget(self.in_rev_target)
        layout.addLayout(ctrl)

        # v9.1: 反应式减载清单 (Helms: 0–1 项前进, 2+ 项减载一周)
        signals = QHBoxLayout()
        self.chk_reluctance = QCheckBox("不想训练")
        self.chk_sleep = QCheckBox("睡眠变差")
        self.chk_drop = QCheckBox("负荷/次数下降")
        self.chk_stress = QCheckBox("生活压力大")
        self.chk_pain = QCheckBox("疼痛加重")
        for chk in (self.chk_reluctance, self.chk_sleep, self.chk_drop, self.chk_stress, self.chk_pain):
            signals.addWidget(chk)
        layout.addLayout(signals)

        pain_row = QHBoxLayout()
        pain_row.addWidget(QLabel("本次备注 / 疼痛描述:"))
        self.in_rev_note = QLineEdit()
        self.in_rev_note.setPlaceholderText("如: 训练中胸部不适 / 动作稳定, 无疼痛")
        pain_row.addWidget(self.in_rev_note)
        layout.addLayout(pain_row)

        btn = QPushButton("📝 复盘并生成下一次处方")
        btn.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._do_review)
        layout.addWidget(btn)

        self.review_result = QTextEdit()
        self.review_result.setReadOnly(True)
        layout.addWidget(self.review_result)

        hist_btn = QPushButton("📜 查看历史复盘")
        hist_btn.clicked.connect(self._show_history)
        layout.addWidget(hist_btn)
        return w

    def _collect_signals(self):
        return {
            "reluctance": self.chk_reluctance.isChecked(),
            "sleep_worse": self.chk_sleep.isChecked(),
            "performance_drop": self.chk_drop.isChecked(),
            "life_stress": self.chk_stress.isChecked(),
            "pain": self.chk_pain.isChecked(),
            "goal": "增肌",
        }

    def _do_review(self):
        note = self.in_rev_note.text().strip()
        log = TrainingLog(
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
            movement=self.in_rev_move.text(),
            weight=self.in_rev_w.value(),
            reps=self.in_rev_reps.value(),
            sets=self.in_rev_sets.value(),
            rpe=self.in_rev_rpe.value(),
            notes=note,
        )
        level = assess_overall_level(self.profile)
        try:
            detail = review_report(
                log,
                level=level,
                target_reps=self.in_rev_target.value(),
                target_rpe=8.0,
                pain_note=note,
                signals=self._collect_signals(),
            )
        except Exception:
            detail = None

        result = review_training(
            log,
            level=level,
            target_reps=self.in_rev_target.value(),
            target_rpe=8.0,
            pain_note=note,
            signals=self._collect_signals(),
        )
        save_review(log, result)

        color = {
            "合适": COLORS["success"],
            "偏轻": COLORS["warning"],
            "偏重": COLORS["danger"],
            "部分完成": COLORS["warning"],
            "停滞": COLORS["accent"],
            "减载一周": COLORS["accent"],
            "预防性减载": COLORS["accent"],
            "暂停常规处方": COLORS["danger"],
        }.get(result.judgment, COLORS["text"])
        html = f'<h3 style="color:{color};">判断: {result.judgment}</h3>'
        html += "<h4>关键发现</h4><ul>"
        for f in result.key_findings:
            html += f"<li>{f}</li>"
        html += "</ul>"

        rx = result.next_prescription
        html += f"<h4>下一次处方</h4><p><b>{rx.get('movement', '')}</b>: {rx.get('weight', '')}kg × "
        html += f"{rx.get('sets', rx.get('movement_sets', ''))}组 × {rx.get('reps', '')}次</p>"
        if rx.get("rpe_text"):
            html += "<p>逐组 RPE: " + " → ".join(rx["rpe_text"]) + "</p>"
        elif rx.get("rpe"):
            html += f"<p>目标 RPE: {rx['rpe']}</p>"
        if rx.get("rest"):
            lo, hi = rx["rest"]
            html += f"<p>组间休息: {lo // 60}–{hi // 60} 分钟</p>"
        if rx.get("failure"):
            html += f"<p>力竭使用: {rx['failure']['note']}</p>"
        if rx.get("tempo"):
            html += f"<p>节奏/幅度: {rx['tempo']['note']}</p>"
        html += f"<p>渐进类型: <b>{result.progression_type}</b></p>"

        if detail:
            if detail.get("safety"):
                html += f'<p style="color:{COLORS["danger"]};"><b>安全分流</b>: {detail["safety"]}</p>'
            if detail.get("deload") and detail["deload"]["verdict"] != "继续前进":
                d = detail["deload"]
                html += (
                    f"<p><b>减载判定</b>: {d['verdict']} (命中 {d['count']} 项: "
                    f"{'、'.join(d['hit'])}) — {d['action']}</p>"
                )
            if detail.get("stall") and detail["stall"]["is_stall"]:
                html += "<p><b>停滞提示</b>: " + detail["stall"]["hint"] + "</p>"
            if detail.get("volume"):
                v = detail["volume"]
                html += (
                    f"<p><b>周组数</b>: {v['planned_sets']} 组 → <b>{v['verdict']}</b> "
                    f"(起始区间 {v['band'][0]}–{v['band'][1]}) — {v['action']}</p>"
                )

        html += (
            '<p style="color:' + COLORS["subtext"] + ';">一次训练只改变重量/次数/组数中的一个主要变量; '
            "单次状态差不等于平台期</p>"
        )
        self.review_result.setHtml(html)

    def _show_history(self):
        reviews = load_reviews()
        if not reviews:
            self.review_result.setHtml("<p>暂无历史复盘记录</p>")
            return
        html = '<h3>历史复盘</h3><table border="1" cellpadding="4" style="border-collapse:collapse;">'
        html += "<tr><th>时间</th><th>动作</th><th>重量</th><th>组×次</th><th>RPE</th><th>判断</th><th>渐进</th></tr>"
        for r in reviews[-20:]:
            log = r["log"]
            html += f"<tr><td>{r['timestamp']}</td><td>{log['movement']}</td><td>{log['weight']}kg</td>"
            html += f"<td>{log['sets']}×{log['reps']}</td><td>{log['rpe']}</td>"
            html += f"<td>{r['judgment']}</td><td>{r['progression_type']}</td></tr>"
        html += "</table>"
        self.review_result.setHtml(html)

    # ─── 子页4: 停训接回 ───
    def _build_return_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("停训天数:"))
        self.in_days_off = QSpinBox()
        self.in_days_off.setRange(1, 365)
        self.in_days_off.setValue(7)
        ctrl.addWidget(self.in_days_off)
        ctrl.addWidget(QLabel("最近训练重量(kg):"))
        self.in_last_w = QDoubleSpinBox()
        self.in_last_w.setRange(0, 500)
        self.in_last_w.setValue(60)
        ctrl.addWidget(self.in_last_w)
        ctrl.addWidget(QLabel("动作:"))
        self.in_ret_move = QLineEdit("卧推")
        ctrl.addWidget(self.in_ret_move)
        ctrl.addWidget(QLabel("辅项(逗号分隔):"))
        self.in_ret_support = QLineEdit("划船, 深蹲")
        ctrl.addWidget(self.in_ret_support)
        ctrl.addWidget(QLabel("每周次数:"))
        self.in_ret_exposures = QSpinBox()
        self.in_ret_exposures.setRange(1, 7)
        self.in_ret_exposures.setValue(2)
        ctrl.addWidget(self.in_ret_exposures)
        layout.addLayout(ctrl)

        btn = QPushButton("↩️ 生成接回方案")
        btn.setStyleSheet(f"background-color: {COLORS['warning']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._gen_return)
        layout.addWidget(btn)

        self.return_result = QTextEdit()
        self.return_result.setReadOnly(True)
        layout.addWidget(self.return_result)
        return w

    def _gen_return(self):
        support = [x.strip() for x in self.in_ret_support.text().replace("，", ",").split(",") if x.strip()]
        plan = generate_return_plan(
            self.in_days_off.value(),
            self.in_last_w.value(),
            self.in_ret_move.text(),
            support,
            self.in_ret_exposures.value(),
        )
        perm_color = {
            "正常接回": COLORS["success"],
            "降级接回": COLORS["warning"],
            "最低任务": COLORS["accent"],
            "暂停": COLORS["danger"],
        }.get(plan.permission, COLORS["text"])
        html = f'<h3 style="color:{perm_color};">恢复权限: {plan.permission}</h3>'
        html += f"<p>停训天数: {plan.days_off}天</p>"
        html += "<h4>三档方案</h4><ul>"
        html += f"<li><b>正常版</b>: {plan.normal_version}</li>"
        html += f"<li><b>降级版</b>: {plan.degraded_version}</li>"
        html += f"<li><b>最低版</b>: {plan.minimal_version}</li>"
        html += "</ul>"
        if getattr(plan, "return_48h", ""):
            html += f"<h4>48 小时内先完成</h4><p>{plan.return_48h}</p>"
        if getattr(plan, "exit_conditions", None):
            html += "<h4>升级 / 维持 / 暂停条件</h4><ul>"
            for k, label in (("upgrade", "升级"), ("hold", "维持"), ("stop", "暂停")):
                if plan.exit_conditions.get(k):
                    html += f"<li><b>{label}</b>: {plan.exit_conditions[k]}</li>"
            html += "</ul>"
        html += "<h4>未来7天</h4><ol>"
        for d in plan.next_7_days:
            html += f"<li>{d}</li>"
        html += "</ol>"
        if getattr(plan, "no_makeup_note", ""):
            html += f'<p style="color:{COLORS["warning"]};">{plan.no_makeup_note}</p>'
        html += (
            '<p style="color:' + COLORS["subtext"] + ';">接回成功的标准是恢复自主判断与稳定执行, '
            "而不是一周内回到停训前全部重量</p>"
        )
        self.return_result.setHtml(html)

    # ─── 子页5: 最低执行版本 ───
    def _build_short_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        intro = QLabel(
            "时间不足时自动生成短版训练，保留主线动作，不补课、不加倍训练、不用惩罚性有氧。"
            "时间很紧时先减少低优先级附件，不压缩复合主项的组间休息。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {COLORS['subtext']}; padding: 8px;")
        layout.addWidget(intro)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("可用时间(分钟):"))
        self.in_minutes = QSpinBox()
        self.in_minutes.setRange(2, 60)
        self.in_minutes.setValue(20)
        ctrl.addWidget(self.in_minutes)
        layout.addLayout(ctrl)

        time_btns = QHBoxLayout()
        for m in [30, 20, 10, 5, 2]:
            btn = QPushButton(f"{m}分钟版")
            btn.clicked.connect(lambda _, x=m: self._gen_short(x))
            time_btns.addWidget(btn)
        layout.addLayout(time_btns)

        gap_btn = QPushButton("🔍 动作缺口审计 (推/拉/髋铰链/深蹲/负重行走/单腿)")
        gap_btn.clicked.connect(self._audit_gaps)
        layout.addWidget(gap_btn)

        self.short_result = QTextEdit()
        self.short_result.setReadOnly(True)
        layout.addWidget(self.short_result)
        return w

    def _gen_short(self, minutes: int):
        if not hasattr(self, "cycle_result"):
            self.short_result.setHtml('<p>请先在"力量周期"页生成周期</p>')
            return
        move = self.in_cycle_move.currentText() if hasattr(self, "in_cycle_move") else "主项"
        cur = self.in_cur_1rm.value() if hasattr(self, "in_cur_1rm") else 60
        cycle = generate_strength_cycle(move, cur, cur * 1.1, 2)
        if not cycle.days:
            self.short_result.setHtml("<p>无可用训练日</p>")
            return
        day = cycle.days[0]
        short = generate_short_version(day, minutes)
        html = f"<h3>{minutes}分钟短版训练</h3>"
        html += f"<p>动作: {move}</p>"
        html += f"<p><b>{short}</b></p>"
        try:
            detail = generate_short_plan(day, minutes)
            html += "<h4>保留 / 舍弃</h4><ul>"
            html += f"<li><b>保留</b>: {detail['keep']}</li>"
            html += f"<li><b>舍弃</b>: {detail['drop']}</li>"
            html += f"<li><b>休息</b>: {detail['rest']} ({detail['super_set']})</li>"
            html += "</ul>"
        except Exception:
            detail = None
        html += "<h4>原则</h4><ul>"
        if detail:
            for r in detail["rules"]:
                html += f"<li>{r}</li>"
        else:
            html += "<li>优先保留当天主线动作</li>"
            html += "<li>不补课、不加倍训练</li>"
            html += "<li>不用惩罚性有氧</li>"
        html += "</ul>"
        self.short_result.setHtml(html)

    def _audit_gaps(self):
        """动作缺口审计 (Dan John Intervention): 审计表, 不是动作配额表。"""
        if not SCIENCE_UI_AVAILABLE:
            self.short_result.setHtml("<p>训练科学规则层未加载, 无法执行缺口审计</p>")
            return
        try:
            cycles = load_reviews()
        except Exception:
            cycles = []
        names = [self.in_cycle_move.currentText()] if hasattr(self, "in_cycle_move") else []
        result = audit_movement_gaps(names)
        html = "<h3>动作模式缺口审计</h3>"
        html += "<p>审计范围: 推 / 拉 / 髋铰链 / 深蹲 / 负重行走 / 单腿或旋转</p>"
        html += "<h4>已覆盖</h4><ul>"
        if result["covered"]:
            for pattern, hits in result["covered"].items():
                html += f"<li><b>{pattern}</b>: {', '.join(hits)}</li>"
        else:
            html += "<li>当前选中的动作未覆盖任何模式</li>"
        html += "</ul><h4>缺口</h4><ul>"
        if result["gaps"]:
            for gap in result["gaps"]:
                html += f"<li>{gap}</li>"
        else:
            html += "<li>无缺口</li>"
        html += "</ul>"
        html += f"<p>{result['action']}</p>"
        html += (
            f'<p style="color:{COLORS["subtext"]};">缺失记录 {len(cycles)} 条; '
            "缺口审计只提示要检查什么, 不自动加动作, 也不诊断功能或预测受伤</p>"
        )
        self.short_result.setHtml(html)
