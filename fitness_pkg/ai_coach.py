# -*- coding: utf-8 -*-
"""
AI 教练页面 (v7.0 模块化拆分)
基于 Lzheng-fitness 知识库的增肌规划: 分层评估/周期生成/训练复盘/停训接回/短版训练。
"""
import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QPushButton, QTextEdit, QTabWidget,
    QScrollArea, QFormLayout, QFrame, QCheckBox,
)

from .constants import COLORS

# AI 教练引擎 — 软依赖, 缺失时降级 (原 fitness_modules.py L2816-2826)
try:
    from ai_coach_engine import (
        AthleteProfile, assess_overall_level, LEVEL_DESC, determine_cycle_length,
        generate_strength_cycle, export_cycle_to_markdown,
        TrainingLog, review_training, save_review, load_reviews,
        generate_return_plan, generate_short_version,
        save_profile, load_profile, save_cycle,
    )
    AI_COACH_AVAILABLE = True
except Exception:
    AI_COACH_AVAILABLE = False


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
            lbl = QLabel('⚠ AI 教练引擎未加载 (ai_coach_engine.py)')
            lbl.setStyleSheet(f"color: {COLORS['danger']}; font-size: 14px;")
            layout.addWidget(lbl)
            return

        header = QLabel('🤖 AI 教练 — 基于 Lzheng-fitness 知识库')
        header.setFont(QFont('Microsoft YaHei', 14, QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['primary']}; padding: 8px;")
        layout.addWidget(header)

        sub = QLabel('P0-L3 分层 · 力量周期化 · 训练复盘 · 停训接回 · 最低执行版本')
        sub.setStyleSheet(f"color: {COLORS['subtext']}; padding-bottom: 8px;")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_profile_tab(), '📋 建档与分层')
        self.tabs.addTab(self._build_cycle_tab(), '📅 力量周期')
        self.tabs.addTab(self._build_review_tab(), '📝 训练复盘')
        self.tabs.addTab(self._build_return_tab(), '↩️ 停训接回')
        self.tabs.addTab(self._build_short_tab(), '⏱ 短版训练')

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
        self.in_age = QSpinBox(); self.in_age.setRange(10, 80); self.in_age.setValue(self.profile.age or 30)
        self.in_height = QDoubleSpinBox(); self.in_height.setRange(100, 250); self.in_height.setValue(self.profile.height_cm or 175)
        self.in_weight = QDoubleSpinBox(); self.in_weight.setRange(30, 200); self.in_weight.setValue(self.profile.weight_kg or 67)
        self.in_bf = QDoubleSpinBox(); self.in_bf.setRange(3, 60); self.in_bf.setValue(self.profile.body_fat_pct or 17)
        self.in_years = QDoubleSpinBox(); self.in_years.setRange(0, 30); self.in_years.setSingleStep(0.5); self.in_years.setValue(self.profile.training_years or 0)
        self.in_sessions = QSpinBox(); self.in_sessions.setRange(1, 7); self.in_sessions.setValue(self.profile.weekly_sessions or 4)
        self.in_minutes = QSpinBox(); self.in_minutes.setRange(10, 180); self.in_minutes.setValue(self.profile.session_minutes or 60)
        self.in_goal = QComboBox(); self.in_goal.addItems(['增肌', '减脂', '力量', '综合']); self.in_goal.setCurrentText(self.profile.goal or '增肌')

        form.addRow('姓名', self.in_name)
        form.addRow('年龄', self.in_age)
        form.addRow('身高(cm)', self.in_height)
        form.addRow('体重(kg)', self.in_weight)
        form.addRow('体脂率(%)', self.in_bf)
        form.addRow('训练年限(年)', self.in_years)
        form.addRow('每周训练次数', self.in_sessions)
        form.addRow('单次时长(分钟)', self.in_minutes)
        form.addRow('主要目标', self.in_goal)

        btn_save = QPushButton('💾 保存建档并评估分层')
        btn_save.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(self._save_profile)
        form.addRow(btn_save)

        self.lbl_level_result = QTextEdit()
        self.lbl_level_result.setReadOnly(True)
        self.lbl_level_result.setMinimumHeight(280)
        self.lbl_level_result.setStyleSheet(f"QTextEdit {{ background-color: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 8px; }}")
        form.addRow('分层评估结果', self.lbl_level_result)

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
        html = f'<h3>整体训练等级: {level}</h3><p>{LEVEL_DESC[level]}</p>'
        html += self._cycle_selfcheck_html()
        html += '<h4>建议:</h4><ul>'
        if level == 'P0':
            html += '<li>首要目标: 安全、可重复、建立基准</li><li>使用固定器械或支撑动作</li><li>每次训练记录重量和感觉</li>'
        elif level == 'L1':
            html += '<li>可逐次或隔次推进</li><li>使用线性或双重渐进</li><li>一次只改变一个主要变量</li>'
        elif level == 'L2':
            html += '<li>按周管理训练量、强度和恢复</li><li>可使用多周周期</li><li>关注疲劳管理</li>'
        else:
            html += '<li>按阶段规划进步</li><li>需要更高专项性</li><li>使用完整积累→强度→实现→减量周期</li>'
        html += '</ul>'
        self.lbl_level_result.setHtml(html)

    # ─── 自检: 周期时长与周组数是否与「频率先匹配可执行时间」一致 ───
    def _cycle_share(self) -> float:
        """单动作每周平均训练次数(由每周训练日数推导, 至少 1)"""
        return max(1.0, max(1, int(self.profile.weekly_sessions or 4)) / 2.0)

    def _cycle_weeks(self) -> int:
        """按约定频率推导建议周期长度"""
        return determine_cycle_length(int(round(self._cycle_share())), self.profile.goal)

    def _cycle_selfcheck_html(self) -> str:
        """生成周期时长/周组数自检结论"""
        try:
            share = self._cycle_share()
            weeks = self._cycle_weeks()
        except Exception:
            return ''
        sessions = max(1, int(self.profile.weekly_sessions or 4))
        sets_low, sets_high = 10 * sessions, 20 * sessions
        html = '<h4>周期自检 (频率优先于目标)</h4><ul>'
        html += (f'<li>每周 {sessions} 练 → 起始周组数参考区间 '
                 f'<b>{sets_low}-{sets_high} 组</b>, 先用区间下限, 按恢复与完成率再加</li>')
        html += (f'<li>按此频率单动作约训 {share:.1f} 次/周 → '
                 f'建议周期 <b>{weeks} 周</b> (暴露越频繁周期越短)</li>')
        html += '<li>训练量是起点假设, 不机械追求最大组数</li></ul>'
        return html

    # ─── 子页2: 力量周期生成 ───
    def _build_cycle_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel('动作:'))
        self.in_cycle_move = QComboBox()
        self.in_cycle_move.addItems(['卧推', '深蹲', '硬拉', '推举', '引体向上', '划船'])
        ctrl.addWidget(self.in_cycle_move)

        ctrl.addWidget(QLabel('当前1RM(kg):'))
        self.in_cur_1rm = QDoubleSpinBox(); self.in_cur_1rm.setRange(10, 500); self.in_cur_1rm.setValue(80)
        ctrl.addWidget(self.in_cur_1rm)

        ctrl.addWidget(QLabel('目标1RM(kg):'))
        self.in_tgt_1rm = QDoubleSpinBox(); self.in_tgt_1rm.setRange(10, 500); self.in_tgt_1rm.setValue(90)
        ctrl.addWidget(self.in_tgt_1rm)

        ctrl.addWidget(QLabel('每周暴露:'))
        self.in_exposures = QSpinBox(); self.in_exposures.setRange(1, 4); self.in_exposures.setValue(2)
        ctrl.addWidget(self.in_exposures)
        layout.addLayout(ctrl)

        self.lbl_cycle_hint = QLabel()
        self.lbl_cycle_hint.setWordWrap(True)
        self.lbl_cycle_hint.setStyleSheet(f"color: {COLORS['subtext']}; padding: 2px 0 6px 0;")
        layout.addWidget(self.lbl_cycle_hint)
        self._refresh_cycle_hint()

        btn = QPushButton('🎯 生成力量周期')
        btn.setStyleSheet(f"background-color: {COLORS['success']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._gen_cycle)
        layout.addWidget(btn)

        self.cycle_result = QTextEdit()
        self.cycle_result.setReadOnly(True)
        layout.addWidget(self.cycle_result)
        return w

    def _refresh_cycle_hint(self):
        """提示本周期采用的频率假设, 避免默认值(每周2次)悄悄改变周期长度"""
        try:
            sessions = max(1, int(self.profile.weekly_sessions or 4))
            sets_low, sets_high = 10 * sessions, 20 * sessions
            self.lbl_cycle_hint.setText(
                f'本周期按建档「每周 {sessions} 练」推导: 单动作约 {self._cycle_share():.1f} 次/周 '
                f'→ 建议 {self._cycle_weeks()} 周; 起始周组数 {sets_low}-{sets_high} 组 (先用下限)。'
                '若实际每周只练 1 次, 请把建档的「每周训练次数」调低后重新生成。')
        except Exception:
            self.lbl_cycle_hint.setText('')

    def _gen_cycle(self):
        move = self.in_cycle_move.currentText()
        cur = self.in_cur_1rm.value()
        tgt = self.in_tgt_1rm.value()
        exp = self.in_exposures.value()

        cycle = generate_strength_cycle(move, cur, tgt, exp)
        save_cycle(cycle)
        md_path = export_cycle_to_markdown(cycle)

        html = f'<h3>{move} 力量周期 — {cycle.weeks}周</h3>'
        html += f'<p>当前1RM: {cur}kg → 目标1RM: {tgt}kg</p>'
        html += '<h4>阶段分布</h4><ul>'
        for phase, n in cycle.phase_distribution.items():
            html += f'<li><b>{phase}</b>: {n}周</li>'
        html += '</ul><h4>每周安排</h4><table border="1" cellpadding="4" style="border-collapse:collapse;">'
        html += '<tr><th>周</th><th>阶段</th><th>顶组</th><th>回退组</th></tr>'
        for d in cycle.days:
            top = d.sets[0] if d.sets else None
            back = d.sets[1] if len(d.sets) > 1 else None
            top_s = f'{top.weight}kg {top.sets}×{top.reps}' if top else '—'
            back_s = f'{back.weight}kg {back.sets}×{back.reps}' if back else '—'
            html += f'<tr><td>{d.week}</td><td>{d.phase}</td><td>{top_s}</td><td>{back_s}</td></tr>'
        html += f'</table><p style="color:{COLORS["success"]};">✓ 已保存至: {md_path}</p>'
        html += self._cycle_selfcheck_html()
        self.cycle_result.setHtml(html)

    # ─── 子页3: 训练复盘 ───
    def _build_review_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel('动作:'))
        self.in_rev_move = QLineEdit('卧推')
        ctrl.addWidget(self.in_rev_move)
        ctrl.addWidget(QLabel('重量(kg):'))
        self.in_rev_w = QDoubleSpinBox(); self.in_rev_w.setRange(0, 500); self.in_rev_w.setValue(60)
        ctrl.addWidget(self.in_rev_w)
        ctrl.addWidget(QLabel('次数:'))
        self.in_rev_reps = QSpinBox(); self.in_rev_reps.setRange(1, 30); self.in_rev_reps.setValue(8)
        ctrl.addWidget(self.in_rev_reps)
        ctrl.addWidget(QLabel('组数:'))
        self.in_rev_sets = QSpinBox(); self.in_rev_sets.setRange(1, 10); self.in_rev_sets.setValue(4)
        ctrl.addWidget(self.in_rev_sets)
        ctrl.addWidget(QLabel('RPE:'))
        self.in_rev_rpe = QDoubleSpinBox(); self.in_rev_rpe.setRange(1, 10); self.in_rev_rpe.setSingleStep(0.5); self.in_rev_rpe.setValue(7.5)
        ctrl.addWidget(self.in_rev_rpe)
        layout.addLayout(ctrl)

        # 体感与状态: 命中 2 项信号即建议减载一周
        flags = QHBoxLayout()
        self.chk_completed = QCheckBox('完成计划组次'); self.chk_completed.setChecked(True)
        self.chk_fatigue = QCheckBox('睡眠/恢复差')
        self.chk_pain = QCheckBox('疼痛')
        self.chk_form = QCheckBox('动作失控')
        for c in (self.chk_completed, self.chk_fatigue, self.chk_pain, self.chk_form):
            flags.addWidget(c)
        flags.addWidget(QLabel('疼痛位置/表现:'))
        self.in_pain_desc = QLineEdit(); self.in_pain_desc.setPlaceholderText('如: 左肩前侧, 推起时刺痛')
        flags.addWidget(self.in_pain_desc)
        layout.addLayout(flags)

        btn = QPushButton('📝 复盘并生成下一次处方')
        btn.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._do_review)
        layout.addWidget(btn)

        self.review_result = QTextEdit()
        self.review_result.setReadOnly(True)
        layout.addWidget(self.review_result)

        hist_btn = QPushButton('📜 查看历史复盘')
        hist_btn.clicked.connect(self._show_history)
        layout.addWidget(hist_btn)
        return w

    def _do_review(self):
        if not AI_COACH_AVAILABLE:
            return
        log = TrainingLog(
            date=datetime.datetime.now().strftime('%Y-%m-%d'),
            movement=self.in_rev_move.text(),
            weight=self.in_rev_w.value(),
            reps=self.in_rev_reps.value(),
            sets=self.in_rev_sets.value(),
            rpe=self.in_rev_rpe.value(),
            completed=self.chk_completed.isChecked(),
            abnormal_fatigue=self.chk_fatigue.isChecked(),
            pain=self.chk_pain.isChecked(),
            form_broken=self.chk_form.isChecked(),
            pain_desc=self.in_pain_desc.text().strip(),
        )
        reviews = load_reviews()
        prev = None
        for r in reversed(reviews):
            d = r.get('log') or {}
            if d.get('movement') == log.movement:
                try:
                    prev = TrainingLog(**d)
                    break
                except Exception:
                    continue
        result = review_training(log, prev)
        save_review(log, result)

        color = {'合适': COLORS['success'], '偏轻': COLORS['warning'],
                 '偏重': COLORS['danger'], '部分完成': COLORS['warning'],
                 '需要观察': COLORS['accent'], '暂停训练': COLORS['danger']}.get(
                     result.judgment, COLORS['text'])
        html = f'<h3 style="color:{color};">判断: {result.judgment}</h3>'
        if result.safety_hold:
            html += (f'<p style="color:{COLORS["danger"]};"><b>⚠ 危险信号: 暂停常规训练处方, '
                     '先获得合适的专业评估。本工具不作诊断。</b></p>')
        if result.deload_recommended and not result.safety_hold:
            html += (f'<p style="color:{COLORS["warning"]};"><b>⚖ 建议减载一周</b> — '
                     f'命中信号: {"、".join(result.deload_reasons)}</p>')
        html += '<h4>关键发现</h4><ul>'
        for f in result.key_findings:
            html += f'<li>{f}</li>'
        html += '</ul>'
        rx = result.next_prescription
        if 'weight' in rx:
            html += (f'<h4>下一次处方</h4><p><b>{rx.get("movement","")}</b>: '
                     f'{rx.get("weight","")}kg × {rx.get("sets","")}组{rx.get("reps","")}次 '
                     f'@ RPE {rx.get("rpe","")} · 组间休息 ≥{int(rx.get("rest_seconds", 150)) // 60} 分钟</p>')
        else:
            html += f'<h4>下一步</h4><p><b>{rx.get("action", "暂停")}</b> — {rx.get("note", "")}</p>'
        html += f'<p>渐进类型: <b>{result.progression_type}</b></p>'
        html += f'<p style="color:{COLORS["subtext"]};">可比记录: {"已找到上一次同动作记录" if prev else "暂无同动作历史, 先按基准模式建立第二个可比样本"}</p>'
        self.review_result.setHtml(html)

    def _show_history(self):
        reviews = load_reviews()
        if not reviews:
            self.review_result.setHtml('<p>暂无历史复盘记录</p>')
            return
        html = '<h3>历史复盘</h3><table border="1" cellpadding="4" style="border-collapse:collapse;">'
        html += '<tr><th>时间</th><th>动作</th><th>重量</th><th>组×次</th><th>RPE</th><th>判断</th><th>渐进</th><th>减载信号</th></tr>'
        for r in reviews[-20:]:
            l = r.get('log') or {}
            reasons = r.get('deload_reasons') or []
            mark = f'⚖ {len(reasons)} 项' if r.get('deload_recommended') else '—'
            if reasons:
                mark += f' ({ "、".join(reasons) })'
            html += f'<tr><td>{r.get("timestamp","")}</td><td>{l.get("movement","")}</td><td>{l.get("weight","")}kg</td>'
            html += f'<td>{l.get("sets","")}×{l.get("reps","")}</td><td>{l.get("rpe","")}</td>'
            html += f'<td>{r.get("judgment","")}</td><td>{r.get("progression_type","")}</td><td>{mark}</td></tr>'
        html += '</table>'
        self.review_result.setHtml(html)

    # ─── 子页4: 停训接回 ───
    def _build_return_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel('停训天数:'))
        self.in_days_off = QSpinBox(); self.in_days_off.setRange(1, 365); self.in_days_off.setValue(7)
        ctrl.addWidget(self.in_days_off)
        ctrl.addWidget(QLabel('最近训练重量(kg):'))
        self.in_last_w = QDoubleSpinBox(); self.in_last_w.setRange(0, 500); self.in_last_w.setValue(60)
        ctrl.addWidget(self.in_last_w)
        ctrl.addWidget(QLabel('动作:'))
        self.in_ret_move = QLineEdit('卧推')
        ctrl.addWidget(self.in_ret_move)
        ctrl.addWidget(QLabel('连续漏练次数:'))
        self.in_missed = QSpinBox(); self.in_missed.setRange(0, 10); self.in_missed.setValue(0)
        ctrl.addWidget(self.in_missed)
        layout.addLayout(ctrl)

        btn = QPushButton('↩️ 生成接回方案')
        btn.setStyleSheet(f"background-color: {COLORS['warning']}; color: white; padding: 8px; font-weight: bold;")
        btn.clicked.connect(self._gen_return)
        layout.addWidget(btn)

        self.return_result = QTextEdit()
        self.return_result.setReadOnly(True)
        layout.addWidget(self.return_result)
        return w

    def _gen_return(self):
        plan = generate_return_plan(
            self.in_days_off.value(),
            self.in_last_w.value(),
            self.in_ret_move.text(),
            missed_sessions=self.in_missed.value(),
        )
        perm_color = {'正常接回': COLORS['success'], '降级接回': COLORS['warning'],
                      '最低任务': COLORS['accent'], '暂停': COLORS['danger']}.get(plan.permission, COLORS['text'])
        html = f'<h3 style="color:{perm_color};">恢复权限: {plan.permission}</h3>'
        html += f'<p>停训天数: {plan.days_off}天</p>'
        html += '<h4>三档方案</h4><ul>'
        html += f'<li><b>正常版</b>: {plan.normal_version}</li>'
        html += f'<li><b>降级版</b>: {plan.degraded_version}</li>'
        html += f'<li><b>最低版</b>: {plan.minimal_version}</li>'
        html += '</ul>'
        if plan.first_step_48h:
            html += f'<h4>48 小时内第一件事</h4><p><b>{plan.first_step_48h}</b></p>'
        html += '<h4>第一周只验证这些</h4><ul>'
        for f in plan.first_week_focus:
            html += f'<li>{f}</li>'
        html += '</ul><h4>升级 / 维持 / 暂停条件</h4><ul>'
        html += f'<li>✅ <b>升级</b>: {plan.upgrade_condition}</li>'
        html += f'<li>➖ <b>维持</b>: {plan.hold_condition}</li>'
        html += f'<li>⛔ <b>暂停或继续降级</b>: {plan.pause_condition}</li>'
        html += '</ul>'
        html += f'<p style="color:{COLORS["subtext"]};">接回成功标准: {plan.success_criteria}</p>'
        html += '<h4>未来7天</h4><ol>'
        for d in plan.next_7_days:
            html += f'<li>{d}</li>'
        html += '</ol>'
        self.return_result.setHtml(html)

    # ─── 子页5: 最低执行版本 ───
    def _build_short_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        intro = QLabel('时间不足时自动生成短版训练 (30/20/10/5/2 分钟)，保留主线动作，不补课、不加倍训练、不用惩罚性有氧。'
                       '漏一次按原顺序继续，漏两次用短版接回。')
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {COLORS['subtext']}; padding: 8px;")
        layout.addWidget(intro)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel('可用时间(分钟):'))
        self.in_minutes = QSpinBox(); self.in_minutes.setRange(5, 60); self.in_minutes.setValue(20)
        ctrl.addWidget(self.in_minutes)
        layout.addLayout(ctrl)

        time_btns = QHBoxLayout()
        for m in [30, 20, 10, 5, 2]:
            btn = QPushButton(f'{m}分钟版')
            btn.clicked.connect(lambda _, x=m: self._gen_short(x))
            time_btns.addWidget(btn)
        layout.addLayout(time_btns)

        self.short_result = QTextEdit()
        self.short_result.setReadOnly(True)
        layout.addWidget(self.short_result)
        return w

    def _gen_short(self, minutes: int):
        if not hasattr(self, 'cycle_result'):
            self.short_result.setHtml('<p>请先在"力量周期"页生成周期</p>')
            return
        move = self.in_cycle_move.currentText() if hasattr(self, 'in_cycle_move') else '主项'
        cur = self.in_cur_1rm.value() if hasattr(self, 'in_cur_1rm') else 60
        # 短版重量沿用建档频率推导的周期, 避免重量与频率口径脱节
        cycle = generate_strength_cycle(move, cur, cur * 1.1, int(round(self._cycle_share())))
        if not cycle.days:
            self.short_result.setHtml('<p>无可用训练日</p>')
            return
        day = cycle.days[0]
        short = generate_short_version(day, minutes)
        html = f'<h3>{minutes}分钟短版训练</h3>'
        html += f'<p>动作: {move}</p>'
        html += f'<p><b>{short}</b></p>'
        html += '<h4>原则</h4><ul>'
        html += '<li>优先保留当天主线动作</li>'
        html += '<li>不补课、不加倍训练</li>'
        html += '<li>不用惩罚性有氧</li>'
        html += '<li>漏一次按原顺序继续，漏两次用短版接回</li>'
        html += '</ul>'
        self.short_result.setHtml(html)
