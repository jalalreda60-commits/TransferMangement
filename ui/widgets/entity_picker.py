"""
ui/widgets/entity_picker.py
------------------------------
A QTreeWidget showing the Transfer -> Tool -> Part Number hierarchy.
Used by the Preparation sub-modules to pick which record a form is
editing. `scope` controls which level is actually selectable:
  * "transfer"    - only Transfer rows are selectable (PTT, E2E)
  * "tool"        - only Tool rows are selectable (Safety Stock, Training)
  * "part_number" - only Part Number rows are selectable (RM, Pre-check,
                     Applicator/Counter Part)
Non-selectable rows are still shown for navigation context, and a small
status-coloured dot ICON (not the row's text colour) is drawn next to
each row using the relevant sub-module's computed status where
available - this keeps the label itself always legible regardless of
status or theme, since a "Not Started"/"NA" status maps to a pale grey
that would otherwise make the whole label hard to read.
"""
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QLineEdit
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QBrush, QIcon, QPixmap, QPainter

from models.transfer import Transfer
from utils.constants import color_for_status

ROLE_KIND = Qt.UserRole
ROLE_ID = Qt.UserRole + 1

SCOPE_LEVEL = {"transfer": 0, "tool": 1, "part_number": 2}

# Moderate, theme-aware grey for de-emphasised (non-selectable context)
# rows - chosen to keep at least ~4.5:1 contrast on a white background
# while still reading as muted, and to stay legible on a dark surface too.
_CONTEXT_GREY = {"light": "#5F6368", "dark": "#B5B5B5"}


def _dot_icon(color: str, size: int = 10) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pixmap)


class EntityPicker(QWidget):
    selection_changed = Signal(object, object, object)  # transfer_id, tool_id, part_number_id

    def __init__(self, scope: str, status_fn=None, dark_mode: bool = False, parent=None):
        """status_fn(transfer, tool, part_number) -> str | None, used to
        colour a small status-indicator dot next to that row with the
        relevant sub-module's current status for that row."""
        super().__init__(parent)
        self.scope = scope
        self.status_fn = status_fn
        self.dark_mode = dark_mode
        self._transfers: list[Transfer] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter...")
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(10, 10))
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree)

    def set_dark_mode(self, dark: bool):
        self.dark_mode = dark
        self.load(self._transfers)

    def load(self, transfers: list[Transfer], select_transfer_id: int | None = None):
        self._transfers = transfers
        self.tree.clear()
        target_item = None

        for t in transfers:
            t_status = self.status_fn(t, None, None) if self.status_fn else None
            t_item = self._make_item(f"{t.trf_number}", "transfer", t.id, t_status,
                                      selectable=(self.scope == "transfer"))
            self.tree.addTopLevelItem(t_item)
            if select_transfer_id and t.id == select_transfer_id and self.scope == "transfer":
                target_item = t_item

            for tool in t.tools:
                tool_status = self.status_fn(t, tool, None) if self.status_fn else None
                tool_item = self._make_item(f"🔧 {tool.tool_number}", "tool", tool.id, tool_status,
                                             selectable=(self.scope == "tool"))
                t_item.addChild(tool_item)
                if select_transfer_id and t.id == select_transfer_id and self.scope == "tool" and target_item is None:
                    target_item = tool_item

                for pn in tool.part_numbers:
                    pn_status = self.status_fn(t, tool, pn) if self.status_fn else None
                    pn_item = self._make_item(f"▫ {pn.part_number}", "part_number", pn.id, pn_status,
                                               selectable=(self.scope == "part_number"))
                    tool_item.addChild(pn_item)
                    if select_transfer_id and t.id == select_transfer_id and self.scope == "part_number" and target_item is None:
                        target_item = pn_item

        self.tree.expandAll()
        if target_item:
            self.tree.setCurrentItem(target_item)
        elif self.tree.topLevelItemCount() > 0 and self.scope == "transfer":
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _make_item(self, text: str, kind: str, obj_id: int, status: str | None, selectable: bool) -> QTreeWidgetItem:
        item = QTreeWidgetItem([text])
        item.setData(0, ROLE_KIND, kind)
        item.setData(0, ROLE_ID, obj_id)

        # Status is conveyed via a small coloured dot icon, never by
        # recolouring the label text itself - a "Not Started"/"NA"
        # status must not make the row's identifier hard to read.
        if status:
            item.setIcon(0, _dot_icon(color_for_status(status)))

        if not selectable:
            flags = item.flags()
            item.setFlags(flags & ~Qt.ItemIsSelectable)
            grey = _CONTEXT_GREY["dark" if self.dark_mode else "light"]
            item.setForeground(0, QBrush(QColor(grey)))
        return item

    def _on_selection_changed(self):
        items = self.tree.selectedItems()
        if not items:
            self.selection_changed.emit(None, None, None)
            return
        item = items[0]
        kind = item.data(0, ROLE_KIND)
        obj_id = item.data(0, ROLE_ID)

        transfer_id = tool_id = pn_id = None
        if kind == "transfer":
            transfer_id = obj_id
        elif kind == "tool":
            tool_id = obj_id
            transfer_id = item.parent().data(0, ROLE_ID)
        elif kind == "part_number":
            pn_id = obj_id
            tool_id = item.parent().data(0, ROLE_ID)
            transfer_id = item.parent().parent().data(0, ROLE_ID)

        self.selection_changed.emit(transfer_id, tool_id, pn_id)

    def _apply_filter(self, text: str):
        text = text.lower().strip()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            self._filter_item(top, text)

    def _filter_item(self, item: QTreeWidgetItem, text: str) -> bool:
        self_match = text in item.text(0).lower()
        child_match = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), text):
                child_match = True
        visible = self_match or child_match or not text
        item.setHidden(not visible)
        return visible
