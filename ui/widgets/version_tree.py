from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QLineEdit, QComboBox, QSizePolicy
)
from PySide6.QtCore import Signal
from datetime import datetime


class VersionTreeWidget(QWidget):
    version_selected = Signal(str)

    def __init__(self):
        super().__init__()

        # Enable proper resizing behavior inside splitters/layouts
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setMinimumWidth(150)
        self.setMaximumWidth(600)

        self.version_manager = None
        self.dataset_name = None
        self.version_graph = {}
        self.metadata = {}
        self.all_operations = set()

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Версии")
        layout.addWidget(label)

        controls_layout = QHBoxLayout()

        search_label = QLabel("Поиск:")
        search_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Фильтр версий...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
                padding: 3px 6px;
            }
        """)
        self.search_input.textChanged.connect(self._rebuild_tree)

        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_input, 1)

        operation_label = QLabel("Операция:")
        operation_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")

        self.operation_filter = QComboBox()
        self.operation_filter.setStyleSheet("""
            QComboBox {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; }
        """)
        self.operation_filter.currentTextChanged.connect(self._rebuild_tree)

        controls_layout.addWidget(operation_label)
        controls_layout.addWidget(self.operation_filter, 1)

        sort_label = QLabel("Сортировка:")
        sort_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")

        self.sort_option = QComboBox()
        self.sort_option.addItems([
            "Иерархически",
            "По времени создания (сначала новые)",
            "По времени создания (сначала старые)"
        ])
        self.sort_option.setStyleSheet("""
            QComboBox {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; }
        """)
        self.sort_option.currentTextChanged.connect(self._rebuild_tree)

        controls_layout.addWidget(sort_label)
        controls_layout.addWidget(self.sort_option, 1)

        layout.addLayout(controls_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
            }
            QTreeWidget::item:selected {
                background-color: #5b7cfa;
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self.tree)

    def load_versions(self, version_graph, version_manager=None, dataset_name=None):
        self.version_graph = version_graph
        self.version_manager = version_manager
        self.dataset_name = dataset_name

        self.metadata = {}
        self.all_operations = set()

        if version_manager and dataset_name:
            for version in version_graph.keys():
                try:
                    meta = version_manager.get_version_metadata(dataset_name, version)
                    self.metadata[version] = meta
                    if "operation" in meta:
                        self.all_operations.add(meta["operation"])
                except Exception:
                    self.metadata[version] = {
                        "parent": version_graph[version],
                        "operation": "неизвестно",
                        "timestamp": "",
                        "config": {}
                    }
                    self.all_operations.add("неизвестно")
        else:
            for version, parent in version_graph.items():
                self.metadata[version] = {
                    "parent": parent,
                    "operation": "неизвестно",
                    "timestamp": "",
                    "config": {}
                }
                self.all_operations.add("неизвестно")

        self.operation_filter.blockSignals(True)
        current_operation = self.operation_filter.currentText()
        self.operation_filter.clear()
        self.operation_filter.addItem("Все операции")
        self.operation_filter.addItems(sorted(self.all_operations))

        index = self.operation_filter.findText(current_operation)
        if index >= 0:
            self.operation_filter.setCurrentIndex(index)

        self.operation_filter.blockSignals(False)

        self._rebuild_tree()

    def _rebuild_tree(self):
        self.tree.clear()

        search_text = self.search_input.text().lower()
        selected_operation = self.operation_filter.currentText()
        sort_mode = self.sort_option.currentText()

        filtered_versions = set()
        for version in self.version_graph.keys():
            if search_text and search_text not in version.lower():
                continue

            if selected_operation != "Все операции":
                meta = self.metadata.get(version, {})
                if meta.get("operation") != selected_operation:
                    continue

            filtered_versions.add(version)

        if sort_mode == "Иерархически":
            self._build_hierarchical_tree(filtered_versions)
        else:
            self._build_flat_sorted_tree(filtered_versions, sort_mode)

    def _build_hierarchical_tree(self, filtered_versions):
        created_items = {}
        processed = set()

        def add_version(version):
            if version in processed:
                return
            processed.add(version)

            parent = self.version_graph.get(version)

            if parent is not None and parent in filtered_versions:
                add_version(parent)

            if version not in filtered_versions:
                return

            meta = self.metadata.get(version, {})
            operation = meta.get("operation", "неизвестно")
            display_text = f"{version} ({operation})"

            item = QTreeWidgetItem([display_text])

            if parent is not None and parent in created_items:
                created_items[parent].addChild(item)
            else:
                self.tree.addTopLevelItem(item)

            created_items[version] = item

        for version in filtered_versions:
            add_version(version)

    def _build_flat_sorted_tree(self, filtered_versions, sort_mode):
        versions_with_timestamp = []

        for version in filtered_versions:
            meta = self.metadata.get(version, {})
            timestamp_str = meta.get("timestamp", "")

            try:
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.min
            except Exception:
                timestamp = datetime.min

            versions_with_timestamp.append((version, timestamp))

        if sort_mode == "По времени создания (сначала новые)":
            versions_with_timestamp.sort(key=lambda x: x[1], reverse=True)
        else:
            versions_with_timestamp.sort(key=lambda x: x[1])

        for version, _ in versions_with_timestamp:
            meta = self.metadata.get(version, {})
            operation = meta.get("operation", "неизвестно")
            timestamp_display = meta.get("timestamp", "")

            if timestamp_display:
                try:
                    dt = datetime.fromisoformat(timestamp_display.replace("Z", "+00:00"))
                    timestamp_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            display_text = f"{version} ({operation}) - {timestamp_display}"
            item = QTreeWidgetItem([display_text])
            self.tree.addTopLevelItem(item)

    def select_version(self, version_name):
        def find_item(items):
            for item in items:
                text = item.text(0)
                version = text.split(" (")[0]

                if version == version_name:
                    return item

                found = find_item([item.child(i) for i in range(item.childCount())])
                if found:
                    return found

            return None

        item = find_item([
            self.tree.topLevelItem(i)
            for i in range(self.tree.topLevelItemCount())
        ])

        if item:
            self.tree.setCurrentItem(item)

    def _on_item_clicked(self, item):
        text = item.text(0)
        version_name = text.split(" (")[0]
        self.version_selected.emit(version_name)
