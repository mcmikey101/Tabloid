from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel
from PySide6.QtCore import Signal


class DatasetListWidget(QWidget):
    dataset_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Datasets")
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self.list_widget)

    def set_datasets(self, dataset_names):
        self.list_widget.clear()
        self.list_widget.addItems(dataset_names)

    def _on_item_clicked(self, item):
        self.dataset_selected.emit(item.text())