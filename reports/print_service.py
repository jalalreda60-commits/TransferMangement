"""
reports/print_service.py
---------------------------
Native OS printing support (Print dialog + Print Preview) for any
QTableWidget, satisfying the spec's "Printing support" requirement
without an extra PDF dependency - Qt renders an HTML table through
QTextDocument straight to the selected printer.
"""
from datetime import datetime

from PySide6.QtWidgets import QTableWidget, QWidget
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from utils.constants import COLORS


def _table_to_html(table: QTableWidget, title: str) -> str:
    headers = [table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else ""
               for c in range(table.columnCount())]

    rows_html = []
    for r in range(table.rowCount()):
        cells = []
        for c in range(table.columnCount()):
            item = table.item(r, c)
            text = item.text() if item else ""
            if text == "" and table.cellWidget(r, c) is not None:
                widget = table.cellWidget(r, c)
                text = getattr(widget, "text", lambda: "")() if hasattr(widget, "text") else ""
            cells.append(f"<td style='padding:4px 8px;border:1px solid #DCE2EA;'>{text}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    header_html = "".join(
        f"<th style='padding:6px 8px;background:{COLORS['primary']};color:white;border:1px solid #DCE2EA;'>{h}</th>"
        for h in headers
    )

    return f"""
    <html><head><meta charset='utf-8'></head><body style="font-family:Segoe UI, Arial, sans-serif;">
      <h2 style="color:{COLORS['primary']};margin-bottom:2px;">{title}</h2>
      <div style="color:#666;font-size:11px;margin-bottom:12px;">
        Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} - {table.rowCount()} row(s)
      </div>
      <table style="border-collapse:collapse;width:100%;font-size:11px;">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </body></html>
    """


def print_table(parent: QWidget, table: QTableWidget, title: str = "Transfer Management System - Report") -> bool:
    """Opens the OS print dialog and prints the table. Returns True if
    the user went through with printing."""
    document = QTextDocument()
    document.setHtml(_table_to_html(table, title))

    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Print")
    if dialog.exec() == QPrintDialog.Accepted:
        document.print_(printer)
        return True
    return False


def preview_table(parent: QWidget, table: QTableWidget, title: str = "Transfer Management System - Report") -> None:
    """Shows a live print preview (zoom, page navigation) before the
    user commits to a printer - handy for checking layout first."""
    document = QTextDocument()
    document.setHtml(_table_to_html(table, title))

    printer = QPrinter(QPrinter.HighResolution)
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle("Print Preview")
    preview.paintRequested.connect(lambda p: document.print_(p))
    preview.exec()
