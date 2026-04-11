from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout
from PySide6.QtCore import Signal


class DatasetListWidget(QWidget):

    dataset_selected = Signal(str)
    add_dataset_requested = Signal()

    def __init__(self):
        super().__init__()
        self.all_datasets = []  # Store all datasets for filtering
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Datasets")
        layout.addWidget(label)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter datasets...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
                padding: 3px 6px;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
            }
            QListWidget::item:selected {
                background-color: #5b7cfa;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self.list_widget)

        self.add_button = QPushButton("Add Dataset")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        self.add_button.clicked.connect(self.add_dataset_requested.emit)

        layout.addWidget(self.add_button)

    def set_datasets(self, dataset_names):
        self.all_datasets = sorted(dataset_names)
        self._update_filtered_list()

    def _on_search_changed(self):
        """Update the list based on search query."""
        self._update_filtered_list()

    def _update_filtered_list(self):
        """Filter and display datasets based on search query."""
        search_text = self.search_input.text().lower()
        
        self.list_widget.clear()
        filtered = [d for d in self.all_datasets if search_text in d.lower()]
        self.list_widget.addItems(filtered)

    def _on_item_clicked(self, item):
        self.dataset_selected.emit(item.text())