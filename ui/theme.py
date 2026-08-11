"""
ui/theme.py
-----------
Generates a Qt stylesheet (QSS) for the "professional blue industrial"
ERP-style theme requested in the spec, with light/dark variants.
"""
from utils.constants import COLORS


def build_stylesheet(mode: str = "light") -> str:
    dark = mode == "dark"
    bg = COLORS["bg_dark"] if dark else COLORS["bg_light"]
    surface = COLORS["surface_dark"] if dark else COLORS["surface_light"]
    text = COLORS["text_dark"] if dark else COLORS["text_light"]
    border = COLORS["border_dark"] if dark else COLORS["border_light"]
    primary = COLORS["primary"]
    primary_dark = COLORS["primary_dark"]
    accent = COLORS["accent"]
    hover_row = "#333844" if dark else "#EAF1FA"
    sidebar_bg = "#151922" if dark else "#0B4578"
    sidebar_hover = "#26314A" if dark else "#0F5FA8"
    input_bg = "#20242C" if dark else "#FFFFFF"

    return f"""
    * {{
        font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
        color: {text};
    }}
    QMainWindow, QWidget#centralWidget {{ background-color: {bg}; }}
    QWidget {{ background-color: transparent; }}
    QDialog {{ background-color: {bg}; }}

    /* Sidebar */
    QFrame#sidebar {{ background-color: {sidebar_bg}; border: none; }}
    QLabel#appTitle {{ color: white; font-size: 15px; font-weight: 700; padding: 18px 16px 2px 16px; }}
    QLabel#appSubtitle {{ color: rgba(255,255,255,0.6); font-size: 10px; padding: 0 16px 14px 16px; }}
    QPushButton#navButton {{
        background-color: transparent; color: #E6E6E6; text-align: left;
        padding: 11px 18px; border: none; font-size: 13px;
    }}
    QPushButton#navButton:hover {{ background-color: {sidebar_hover}; }}
    QPushButton#navButton:checked {{
        background-color: {primary if not dark else '#0B4578'};
        border-left: 3px solid {accent}; font-weight: 600;
    }}
    QPushButton#subNavButton {{
        background-color: transparent; color: rgba(255,255,255,0.85); text-align: left;
        padding: 8px 18px 8px 34px; border: none; font-size: 12px;
    }}
    QPushButton#subNavButton:hover {{ background-color: {sidebar_hover}; }}
    QPushButton#subNavButton:checked {{ color: {accent}; font-weight: 600; }}

    /* Cards */
    QFrame#card {{ background-color: {surface}; border: 1px solid {border}; border-radius: 10px; }}
    QFrame#kpiCard {{ background-color: {surface}; border: 1px solid {border}; border-radius: 12px; }}
    QLabel#kpiValue {{ font-size: 24px; font-weight: 700; }}
    QLabel#kpiLabel {{ font-size: 10px; color: {'#B5B5B5' if dark else '#5F6368'}; font-weight: 600; }}
    QLabel#pageTitle {{ font-size: 20px; font-weight: 700; }}
    QLabel#pageSubtitle {{ font-size: 12px; color: {'#B5B5B5' if dark else '#5F6368'}; }}
    QLabel#sectionTitle {{ font-size: 14px; font-weight: 600; }}

    /* Buttons */
    QPushButton {{ background-color: {surface}; border: 1px solid {border}; border-radius: 6px; padding: 7px 14px; }}
    QPushButton:hover {{ background-color: {hover_row}; }}
    QPushButton#primaryButton {{ background-color: {primary}; color: white; border: none; font-weight: 600; padding: 8px 18px; border-radius: 6px; }}
    QPushButton#primaryButton:hover {{ background-color: {primary_dark}; }}
    QPushButton#dangerButton {{ background-color: {COLORS['danger']}; color: white; border: none; font-weight: 600; border-radius: 6px; padding: 8px 18px; }}
    QPushButton#dangerButton:hover {{ background-color: #A82A2E; }}

    /* Inputs */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
        background-color: {input_bg}; border: 1px solid {border}; border-radius: 6px;
        padding: 6px 10px; selection-background-color: {primary};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {primary};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{ background-color: {surface}; border: 1px solid {border}; selection-background-color: {primary}; selection-color: white; }}
    QCheckBox {{ spacing: 8px; }}

    /* Tables */
    QTableWidget, QTableView {{
        background-color: {surface}; alternate-background-color: {'#262A32' if dark else '#FAFBFD'};
        gridline-color: {border}; border: 1px solid {border}; border-radius: 8px;
        selection-background-color: {primary}; selection-color: white;
    }}
    QHeaderView::section {{
        background-color: {'#262A32' if dark else '#EEF2F8'}; color: {text}; padding: 8px;
        border: none; border-bottom: 2px solid {border}; font-weight: 600;
    }}
    QTableWidget::item {{ padding: 6px; }}
    QTreeWidget {{
        background-color: {surface}; border: 1px solid {border}; border-radius: 8px;
        alternate-background-color: {'#262A32' if dark else '#FAFBFD'};
    }}
    QTreeWidget::item {{ padding: 4px; }}

    /* Scrollbars */
    QScrollBar:vertical {{ background: transparent; width: 10px; }}
    QScrollBar::handle:vertical {{ background: {'#4A4F5A' if dark else '#C7CFDA'}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: {'#4A4F5A' if dark else '#C7CFDA'}; border-radius: 5px; min-width: 24px; }}

    /* Tabs */
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px; top: -1px; }}
    QTabBar::tab {{ background: transparent; padding: 8px 16px; border: none; color: {'#B5B5B5' if dark else '#5F6368'}; }}
    QTabBar::tab:selected {{ color: {primary}; font-weight: 600; border-bottom: 2px solid {primary}; }}

    QLabel[badge="true"] {{ border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 600; color: white; }}

    QProgressBar {{ background-color: {'#3A3F4A' if dark else '#E7ECF3'}; border: none; border-radius: 5px; text-align: center; height: 10px; }}
    QProgressBar::chunk {{ background-color: {primary}; border-radius: 5px; }}

    QToolTip {{ background-color: {surface}; color: {text}; border: 1px solid {border}; padding: 4px; }}
    QSplitter::handle {{ background-color: {border}; }}
    QGroupBox {{
        border: 1px solid {border}; border-radius: 8px; margin-top: 10px; padding-top: 12px; font-weight: 600;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}

    QMenu {{ background-color: {surface}; border: 1px solid {border}; }}
    QMenu::item:selected {{ background-color: {primary}; color: white; }}
    """


def apply_theme(app, mode: str = "light"):
    app.setStyleSheet(build_stylesheet(mode))
