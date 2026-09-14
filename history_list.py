from PyQt6.QtWidgets import (QWidget, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal


class NumberedRowWidget(QWidget):
    """A clean, individual row container that visually binds a fixed number to text."""
    def __init__(self, number: int, text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Store text variable for extraction later
        self.raw_text = text
        
        self.num_label = QLabel(str(number))
        self.num_label.setFixedWidth(40)
        self.num_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.num_label)
        layout.addWidget(self.text_label)
        
        # NOTE: Background-color is removed here so the parent QListWidget item selection highlight passes through
        self.setStyleSheet("""
            QWidget { background-color: transparent; }
            QLabel { padding: 10px; border-bottom: 1px solid #e0e0e0; }
            QLabel:first-child {
                color: #888888; background-color: #f7f7f7; font-family: monospace;
                border-right: 1px solid #e0e0e0; padding-right: 12px;
            }
            QLabel:last-child { padding-left: 15px; color: #222222; }
        """)

    def update_number(self, new_number: int):
        self.num_label.setText(str(new_number))


class NumberedListWidget(QListWidget):
    """A single view QListWidget with individual row clicking actions enabled."""
    
    # Custom signal that sends the text of the clicked item
    item_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. ALLOW INTERACTION: Change selection mode back to single click
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Modern hover & selection styling
        self.setStyleSheet("""
            QListWidget { border: 1px solid #dcdcdc; outline: none; }
            QListWidget::item { background: transparent; }
            QListWidget::item:hover { background-color: #f2f7ff; }
            QListWidget::item:selected { background-color: #e2eeff; }
        """)
        
        # 2. CONNECT CLICK SIGNAL: Listen to individual row clicks
        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem):
        """Intercepts native clicks to extract the underlying text string."""
        row_ui = self.itemWidget(item)
        if row_ui and isinstance(row_ui, NumberedRowWidget):
            # Emit the text payload via our custom signal
            self.item_selected.emit(row_ui.raw_text)

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

    def clear(self):
        super().clear()

    def _sync_numbers(self):
        for i in range(self.count()):
            item = self.item(i)
            row_ui = self.itemWidget(item)
            if row_ui:
                row_ui.update_number(i + 1)