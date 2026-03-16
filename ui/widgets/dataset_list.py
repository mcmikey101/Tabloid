from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton
from PySide6.QtCore import Signal


class DatasetListWidget(QWidget):

    dataset_selected = Signal(str)
    add_dataset_requested = Signal()

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

        self.add_button = QPushButton("Add Dataset")
        self.add_button.clicked.connect(self.add_dataset_requested.emit)

        layout.addWidget(self.add_button)

    def set_datasets(self, dataset_names):
        self.list_widget.clear()
        self.list_widget.addItems(dataset_names)

    def _on_item_clicked(self, item):
        self.dataset_selected.emit(item.text())