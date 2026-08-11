"""
ui/views/dashboard_view.py
-----------------------------
Landing page: KPI cards (Total Transfers, Preparation Progress, Release
Progress, Delayed Activities, Open Actions, Completed Transfers),
charts (Progress by Transfer, Progress by Phase, Weekly Progress,
Transfers by Technology, Transfer Type Distribution), and tables
(Recent Activities, Upcoming Due Dates, Delayed Tasks).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QListWidget, QListWidgetItem, QGridLayout, QPushButton,
)
from PySide6.QtCore import Qt

from database.base import new_session
from services import dashboard_service as dash
from ui.widgets.kpi_card import KpiCard
from ui.widgets.charts import DonutChart, BarChart, HorizontalBarChart, LineChart
from utils.constants import color_for_status


class DashboardView(QWidget):
    def __init__(self, dark_mode: bool = False, parent=None):
        super().__init__(parent)
        self.session = new_session()
        self.dark_mode = dark_mode
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        header = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Overview of all transfer projects")
        subtitle.setObjectName("pageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        header_row.addLayout(header)
        header_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn, alignment=Qt.AlignTop)
        outer.addLayout(header_row)

        self.month_notice = QFrame()
        self.month_notice.setObjectName("card")
        month_notice_layout = QHBoxLayout(self.month_notice)
        month_notice_layout.setContentsMargins(14, 10, 14, 10)
        self.month_notice_stripe = QFrame()
        self.month_notice_stripe.setFixedWidth(4)
        month_notice_layout.addWidget(self.month_notice_stripe)
        month_notice_text_col = QVBoxLayout()
        self.month_notice_title = QLabel("")
        self.month_notice_title.setStyleSheet("font-weight: 600;")
        self.month_notice_detail = QLabel("")
        self.month_notice_detail.setStyleSheet("color: #888; font-size: 11px;")
        self.month_notice_detail.setWordWrap(True)
        month_notice_text_col.addWidget(self.month_notice_title)
        month_notice_text_col.addWidget(self.month_notice_detail)
        month_notice_layout.addLayout(month_notice_text_col, 1)
        outer.addWidget(self.month_notice)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # KPI row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self.kpi_total = KpiCard("Total Transfers", 0, "#0F5FA8")
        self.kpi_prep = KpiCard("Preparation Progress", 0, "#2B88D8", suffix="%")
        self.kpi_release = KpiCard("Release Progress", 0, "#1E8E3E", suffix="%")
        self.kpi_delayed = KpiCard("Delayed Activities", 0, "#D13438")
        self.kpi_open_actions = KpiCard("Open Actions", 0, "#F2A900")
        self.kpi_completed = KpiCard("Completed Transfers", 0, "#1E8E3E")
        for card in (self.kpi_total, self.kpi_prep, self.kpi_release,
                     self.kpi_delayed, self.kpi_open_actions, self.kpi_completed):
            kpi_row.addWidget(card)
        content_layout.addLayout(kpi_row)

        # Charts row 1: Progress by Transfer / Progress by Phase
        charts_row1 = QHBoxLayout()
        charts_row1.setSpacing(14)
        self.progress_by_transfer_chart, card1 = self._chart_card("Progress by Transfer", HorizontalBarChart)
        self.progress_by_phase_chart, card2 = self._chart_card("Progress by Phase", BarChart)
        charts_row1.addWidget(card1, 1)
        charts_row1.addWidget(card2, 1)
        content_layout.addLayout(charts_row1)

        # Charts row 2: Weekly Progress / Transfers by Technology / Transfer Type
        charts_row2 = QHBoxLayout()
        charts_row2.setSpacing(14)
        self.weekly_chart, card3 = self._chart_card("Weekly Progress", LineChart)
        self.technology_chart, card4 = self._chart_card("Transfers by Technology", DonutChart)
        self.type_chart, card5 = self._chart_card("Transfer Type Distribution", DonutChart)
        charts_row2.addWidget(card3, 1)
        charts_row2.addWidget(card4, 1)
        charts_row2.addWidget(card5, 1)
        content_layout.addLayout(charts_row2)

        # Location distribution row
        charts_row3 = QHBoxLayout()
        charts_row3.setSpacing(14)
        self.sender_chart, card6 = self._chart_card("Transfers by Sender Location", BarChart)
        self.receiver_chart, card7 = self._chart_card("Transfers by Receiver Location", BarChart)
        charts_row3.addWidget(card6, 1)
        charts_row3.addWidget(card7, 1)
        content_layout.addLayout(charts_row3)

        # Tables row
        tables_row = QHBoxLayout()
        tables_row.setSpacing(14)
        self.upcoming_list = self._make_list_card("Upcoming Due Dates", tables_row)
        self.delayed_list = self._make_list_card("Delayed Tasks", tables_row)
        self.activity_list = self._make_list_card("Recent Activities", tables_row)
        content_layout.addLayout(tables_row)
        content_layout.addStretch()

    def _chart_card(self, title_text: str, chart_cls):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        chart = chart_cls(dark_mode=self.dark_mode)
        layout.addWidget(chart)
        return chart, card

    def _make_list_card(self, title_text: str, parent_layout: QHBoxLayout) -> QListWidget:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(220)
        layout = QVBoxLayout(card)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.NoFrame)
        layout.addWidget(list_widget)
        parent_layout.addWidget(card, 1)
        return list_widget

    # ------------------------------------------------------------------ #
    def refresh(self):
        self.session.close()
        self.session = new_session()
        s = self.session

        month_transfers = dash.transfers_this_month(s)
        next_this_month = dash.next_transfer_this_month(s)
        if next_this_month:
            days = next_this_month.days_until_transfer()
            when = "today" if days == 0 else f"in {days} day(s)"
            self.month_notice_stripe.setStyleSheet("background-color: #0F5FA8; border-radius: 2px;")
            self.month_notice_title.setText(
                f"Next transfer this month: {next_this_month.trf_number} — "
                f"{next_this_month.planned_transfer_date.isoformat()} ({when})"
            )
            self.month_notice_detail.setText(
                f"{next_this_month.sender_location or '-'} → {next_this_month.receiver_location or '-'}  ·  "
                f"{len(month_transfers)} transfer(s) planned this month in total."
            )
        elif month_transfers:
            self.month_notice_stripe.setStyleSheet("background-color: #F2A900; border-radius: 2px;")
            self.month_notice_title.setText(f"{len(month_transfers)} transfer(s) planned this month — all already past their date")
            self.month_notice_detail.setText("Check the Transfers list to update their status.")
        else:
            self.month_notice_stripe.setStyleSheet("background-color: #8A8886; border-radius: 2px;")
            self.month_notice_title.setText("No transfers planned for this month")
            self.month_notice_detail.setText("")

        kpis = dash.kpis(s)
        self.kpi_total.set_value(kpis["total_transfers"])
        self.kpi_prep.set_value(f"{kpis['preparation_progress']:.0f}")
        self.kpi_release.set_value(f"{kpis['release_progress']:.0f}")
        self.kpi_delayed.set_value(kpis["delayed_activities"])
        self.kpi_open_actions.set_value(kpis["open_actions"])
        self.kpi_completed.set_value(kpis["completed_transfers"])

        labels, values, colors = dash.progress_by_transfer(s)
        self.progress_by_transfer_chart.plot(labels, values, colors)

        phase_data = dash.progress_by_phase(s)
        self.progress_by_phase_chart.plot(list(phase_data.keys()), list(phase_data.values()))

        weekly = dash.weekly_progress_trend(s)
        self.weekly_chart.plot(list(weekly.keys()), list(weekly.values()))

        tech = dash.transfers_by_technology(s)
        self.technology_chart.plot(tech)

        type_dist = dash.transfer_type_distribution(s)
        self.type_chart.plot(type_dist)

        sender = dash.transfers_by_sender_location(s)
        self.sender_chart.plot(list(sender.keys()), list(sender.values()))

        receiver = dash.transfers_by_receiver_location(s)
        self.receiver_chart.plot(list(receiver.keys()), list(receiver.values()))

        self.upcoming_list.clear()
        for t in dash.upcoming_transfer_dates(s):
            days = t.days_until_transfer()
            self.upcoming_list.addItem(f"{t.trf_number}  ·  {t.planned_transfer_date}  ·  in {days} day(s)")
        if self.upcoming_list.count() == 0:
            self.upcoming_list.addItem("No upcoming transfer dates.")

        self.delayed_list.clear()
        for n in dash.delayed_tasks(s):
            self.delayed_list.addItem(f"{n.transfer_trf}  ·  {n.title}")
        if self.delayed_list.count() == 0:
            self.delayed_list.addItem("No delayed tasks.")

        self.activity_list.clear()
        from services import transfer_service as svc
        for a in svc.recent_activity(s):
            self.activity_list.addItem(f"{a.created_at:%Y-%m-%d %H:%M}  ·  {a.action}  ·  {a.details or ''}")
        if self.activity_list.count() == 0:
            self.activity_list.addItem("No recent activity.")

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark
        for chart in (self.progress_by_transfer_chart, self.progress_by_phase_chart,
                      self.weekly_chart, self.technology_chart, self.type_chart,
                      self.sender_chart, self.receiver_chart):
            chart.dark_mode = dark
        self.refresh()
