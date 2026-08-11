"""
ui/widgets/sidebar.py
------------------------
Collapsible left navigation rail with the four top-level modules from
the spec (Dashboard, Transfers, Preparation, Release). Preparation
expands into its seven sub-modules (PTT Approval, Safety Stock, Raw
Material, Pre-check, E2E Follow-up, Applicator/Counter Part, Training).

Emits `navigate(str)` with a page key:
  "dashboard", "transfers", "release", "notifications", "reports", "settings"
  or "prep_<slug>" for a specific Preparation sub-module, or "preparation"
  for the Preparation landing/overview.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QButtonGroup, QWidget, QScrollArea
from PySide6.QtCore import Signal, Qt

TOP_ITEMS = [
    ("dashboard", "🏠", "Dashboard"),
    ("transfers", "📋", "Transfers"),
]

PREPARATION_KEY = "preparation"
PREPARATION_LABEL = ("🧪", "Preparation")

PREPARATION_SUBMODULES = [
    ("prep_ptt", "PTT Approval"),
    ("prep_safety_stock", "Safety Stock"),
    ("prep_raw_material", "Raw Material"),
    ("prep_pre_check", "Pre-check"),
    ("prep_e2e", "E2E Follow-up"),
    ("prep_applicator_cp", "Applicator / Counter Part"),
    ("prep_training", "Training"),
]

BOTTOM_ITEMS = [
    ("release", "🚀", "Release"),
    ("notifications", "🔔", "Notifications"),
    ("reports", "📄", "Reports"),
    ("settings", "⚙️", "Settings"),
]

EXPANDED_WIDTH = 240
COLLAPSED_WIDTH = 60


class Sidebar(QFrame):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.collapsed = False
        self.setFixedWidth(EXPANDED_WIDTH)

        self.buttons: dict[str, QPushButton] = {}
        self._full_text: dict[str, str] = {}
        self._icon_text: dict[str, str] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header_row = QVBoxLayout()
        self.title_label = QLabel("Transfer Management")
        self.title_label.setObjectName("appTitle")
        header_row.addWidget(self.title_label)
        self.subtitle_label = QLabel("System")
        self.subtitle_label.setObjectName("appSubtitle")
        header_row.addWidget(self.subtitle_label)
        outer.addLayout(header_row)

        self.toggle_btn = QPushButton("«  Collapse")
        self.toggle_btn.setObjectName("subNavButton")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_collapsed)
        outer.addWidget(self.toggle_btn)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        for key, icon, label in TOP_ITEMS:
            self._add_nav_button(outer, key, icon, label, sub=False)

        # Preparation (expandable header + sub-items)
        self.prep_toggle_btn = self._add_nav_button(
            outer, PREPARATION_KEY, PREPARATION_LABEL[0], PREPARATION_LABEL[1], sub=False,
            checkable=True, add_to_group=True,
        )
        self.prep_container = QWidget()
        prep_layout = QVBoxLayout(self.prep_container)
        prep_layout.setContentsMargins(0, 0, 0, 0)
        prep_layout.setSpacing(0)
        for key, label in PREPARATION_SUBMODULES:
            self._add_nav_button(prep_layout, key, "•", label, sub=True)
        outer.addWidget(self.prep_container)
        self.prep_container.setVisible(True)

        for key, icon, label in BOTTOM_ITEMS:
            self._add_nav_button(outer, key, icon, label, sub=False)

        outer.addStretch()

        self.notif_badge = QLabel("")
        self.notif_badge.setObjectName("appSubtitle")
        self.notif_badge.setWordWrap(True)
        outer.addWidget(self.notif_badge)

        footer = QLabel("v1.0.0")
        footer.setObjectName("appSubtitle")
        outer.addWidget(footer)

        self.buttons["dashboard"].setChecked(True)

    def _add_nav_button(self, layout, key, icon, label, sub=False, checkable=True, add_to_group=True) -> QPushButton:
        btn = QPushButton(f"{icon}  {label}")
        btn.setObjectName("subNavButton" if sub else "navButton")
        btn.setCheckable(checkable)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked, k=key: self.navigate.emit(k))
        layout.addWidget(btn)
        if add_to_group:
            self.group.addButton(btn)
        self.buttons[key] = btn
        self._full_text[key] = f"{icon}  {label}"
        self._icon_text[key] = icon
        return btn

    # ------------------------------------------------------------------ #
    def set_active(self, key: str):
        if key in self.buttons:
            self.buttons[key].setChecked(True)
        # Auto-expand Preparation group when a sub-module is selected
        is_prep = key == PREPARATION_KEY or key.startswith("prep_")
        if is_prep:
            self.prep_container.setVisible(True)
            self.buttons[PREPARATION_KEY].setChecked(key == PREPARATION_KEY)

    def set_notification_summary(self, text: str):
        self.notif_badge.setText(text)

    def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.setFixedWidth(COLLAPSED_WIDTH if self.collapsed else EXPANDED_WIDTH)
        self.title_label.setVisible(not self.collapsed)
        self.subtitle_label.setVisible(not self.collapsed)
        self.notif_badge.setVisible(not self.collapsed)
        self.toggle_btn.setText("»" if self.collapsed else "«  Collapse")
        for key, btn in self.buttons.items():
            btn.setText(self._icon_text[key] if self.collapsed else self._full_text[key])
        self.prep_container.setVisible(not self.collapsed and self.prep_container.isVisible())
