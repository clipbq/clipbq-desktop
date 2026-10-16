import re
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent


def parse_clipboard_text(text: str) -> str:
    url_pattern = r'(?:https?://[^\s<>"]+|www\.[^\s<>"]+|(?<![\w.=])(?<!\.)[a-zA-Z0-9.-]+\.[a-z]{2,6}(?![A-Z\w(])(?:/[^\s<>"]*)?)'

    def replace_with_link(match):
        url = match.group(0)
        if url.startswith("http://") or url.startswith("https://"):
            href = url
        elif url.startswith("www."):
            href = f"http://{url}"
        else:
            href = f"https://{url}"
        return f'<a href="{href}">{url}</a>'

    linked_text = re.sub(url_pattern, replace_with_link, text)
    return linked_text.replace("\n", "<br>")


class LinkAwareLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.press_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        self.press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)
        if self.hasSelectedText():
            return
        if (
            self.press_pos
            and (event.position().toPoint() - self.press_pos).manhattanLength() < 4
        ):
            widget = self.parentWidget()
            while widget and not isinstance(widget, QListWidget):
                widget = widget.parentWidget()
            if widget:
                for i in range(widget.count()):
                    item = widget.item(i)
                    if widget.itemWidget(item) == self.parentWidget():
                        widget.setCurrentItem(item)
                        widget.itemClicked.emit(item)
                        break


class NumberedRowWidget(QWidget):
    def __init__(self, number: int, text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.raw_text = text

        self.num_label = QLabel(str(number))
        self.num_label.setObjectName("numLabel")
        self.num_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        self.num_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.text_label = LinkAwareLabel(self)
        self.text_label.setObjectName("textLabel")
        self.text_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.text_label.setOpenExternalLinks(True)
        self.text_label.setText(parse_clipboard_text(text))
        layout.addWidget(self.num_label)
        layout.addWidget(self.text_label)
        self.setStyleSheet(
            """
            QWidget { 
                background-color: transparent; 
                border-bottom: 1px solid #e0e0e0;
            }
            #numLabel {
                color: #b8b8b8;
                font-family: monospace;
                font-size: 11px;
                padding: 10px;
                min-width: 15px;
            }
            #textLabel { 
                padding: 10px; 
                color: #222222;
            }
            """
        )

    def update_number(self, new_number: int):
        self.num_label.setText(str(new_number))


class NumberedListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(
            """
            QListWidget { border: 1px solid #dcdcdc; outline: none; }
            QListWidget::item { background: transparent; padding: 0px; }
            QListWidget::item:hover { background-color: #f2f7ff; }
            QListWidget::item:selected { background-color: #e2eeff; }
            """
        )

    def prepend_item(self, text: str):
        item = QListWidgetItem()
        self.insertItem(0, item)
        row_ui = NumberedRowWidget(1, text)
        self.setItemWidget(item, row_ui)
        item.setSizeHint(row_ui.sizeHint())
        self._sync_numbers()
        self.scrollToTop()

    def append_item(self, text: str):
        item = QListWidgetItem()
        self.addItem(item)
        row_ui = NumberedRowWidget(self.count(), text)
        self.setItemWidget(item, row_ui)
        item.setSizeHint(row_ui.sizeHint())

    def remove_item_at(self, row_index: int):
        self.takeItem(row_index)
        self._sync_numbers()

    def clear(self):
        super().clear()

    def _sync_numbers(self):
        for i in range(self.count()):
            item = self.item(i)
            row_ui = self.itemWidget(item)
            if row_ui:
                row_ui.update_number(i + 1)
