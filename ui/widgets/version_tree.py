from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QLineEdit, QComboBox
)
from PySide6.QtCore import Signal
from datetime import datetime


class VersionTreeWidget(QWidget):
    version_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.version_manager = None
        self.dataset_name = None
        self.version_graph = {}  # {version: parent}
        self.metadata = {}  # {version: {parent, operation, config, timestamp}}
        self.all_operations = set()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Versions")
        layout.addWidget(label)

        # Controls layout
        controls_layout = QHBoxLayout()

        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter versions...")
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

        # Operation filter
        operation_label = QLabel("Operation:")
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
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        self.operation_filter.currentTextChanged.connect(self._rebuild_tree)
        controls_layout.addWidget(operation_label)
        controls_layout.addWidget(self.operation_filter, 1)

        # Sort option
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        self.sort_option = QComboBox()
        self.sort_option.addItems(["Hierarchical", "By Time Created (Newest First)", "By Time Created (Oldest First)"])
        self.sort_option.setStyleSheet("""
            QComboBox {
                background-color: #2b2d42;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        self.sort_option.currentTextChanged.connect(self._rebuild_tree)
        controls_layout.addWidget(sort_label)
        controls_layout.addWidget(self.sort_option, 1)

        layout.addLayout(controls_layout)

        # Tree widget
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
        """
        Load versions from the version graph and metadata.
        
        Args:
            version_graph: Dict[str, Optional[str]] where key is version and value is parent
            version_manager: Optional VersionManager instance for fetching metadata
            dataset_name: Optional dataset name for metadata fetching
        """
        self.version_graph = version_graph
        self.version_manager = version_manager
        self.dataset_name = dataset_name

        # Fetch metadata for all versions
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
                    # Fallback if metadata fetch fails
                    self.metadata[version] = {
                        "parent": version_graph[version],
                        "operation": "unknown",
                        "timestamp": "",
                        "config": {}
                    }
                    self.all_operations.add("unknown")
        else:
            # Fallback if no version_manager provided
            for version, parent in version_graph.items():
                self.metadata[version] = {
                    "parent": parent,
                    "operation": "unknown",
                    "timestamp": "",
                    "config": {}
                }
                self.all_operations.add("unknown")

        # Update operation filter dropdown
        self.operation_filter.blockSignals(True)
        current_operation = self.operation_filter.currentText()
        self.operation_filter.clear()
        self.operation_filter.addItem("All Operations")
        self.operation_filter.addItems(sorted(self.all_operations))
        # Restore previous selection if it still exists, otherwise select "All Operations"
        index = self.operation_filter.findText(current_operation)
        if index >= 0:
            self.operation_filter.setCurrentIndex(index)
        self.operation_filter.blockSignals(False)

        # Rebuild tree with current filters
        self._rebuild_tree()

    def _rebuild_tree(self):
        """Rebuild the tree based on current filter, search, and sort settings."""
        self.tree.clear()

        search_text = self.search_input.text().lower()
        selected_operation = self.operation_filter.currentText()
        sort_mode = self.sort_option.currentText()

        # Filter versions
        filtered_versions = set()
        for version in self.version_graph.keys():
            # Search filter
            if search_text and search_text not in version.lower():
                continue

            # Operation filter
            if selected_operation != "All Operations":
                meta = self.metadata.get(version, {})
                if meta.get("operation") != selected_operation:
                    continue

            filtered_versions.add(version)

        if sort_mode == "Hierarchical":
            self._build_hierarchical_tree(filtered_versions)
        else:
            self._build_flat_sorted_tree(filtered_versions, sort_mode)

    def _build_hierarchical_tree(self, filtered_versions):
        """Build tree in hierarchical parent-child structure."""
        created_items = {}

        # Process versions in a way that ensures parents are created before children
        processed = set()

        def add_version(version):
            if version in processed:
                return
            processed.add(version)

            parent = self.version_graph.get(version)

            # Ensure parent is added first
            if parent is not None and parent in filtered_versions:
                add_version(parent)

            # Only add version if it wasn't filtered out
            if version not in filtered_versions:
                return

            # Create item
            meta = self.metadata.get(version, {})
            operation = meta.get("operation", "unknown")
            display_text = f"{version} ({operation})"
            item = QTreeWidgetItem([display_text])

            # Add to parent or as top-level
            if parent is not None and parent in created_items:
                created_items[parent].addChild(item)
            else:
                self.tree.addTopLevelItem(item)

            created_items[version] = item

        for version in filtered_versions:
            add_version(version)

    def _build_flat_sorted_tree(self, filtered_versions, sort_mode):
        """Build tree as flat sorted list."""
        # Sort by timestamp
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

        # Sort based on mode
        if sort_mode == "By Time Created (Newest First)":
            versions_with_timestamp.sort(key=lambda x: x[1], reverse=True)
        else:  # Oldest First
            versions_with_timestamp.sort(key=lambda x: x[1])

        # Add to tree
        for version, _ in versions_with_timestamp:
            meta = self.metadata.get(version, {})
            operation = meta.get("operation", "unknown")
            timestamp_display = meta.get("timestamp", "")
            if timestamp_display:
                # Format timestamp for display
                try:
                    dt = datetime.fromisoformat(timestamp_display.replace("Z", "+00:00"))
                    timestamp_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            display_text = f"{version} ({operation}) - {timestamp_display}"
            item = QTreeWidgetItem([display_text])
            self.tree.addTopLevelItem(item)

    def select_version(self, version_name):
        """Select the item with the given version name."""
        def find_item(items):
            for item in items:
                # Extract version name from display text (format: "version_name (operation)" or "version_name (operation) - timestamp")
                text = item.text(0)
                version = text.split(" (")[0]  # Extract before the first "("
                if version == version_name:
                    return item
                # Recursively search children
                found = find_item([item.child(i) for i in range(item.childCount())])
                if found:
                    return found
            return None

        item = find_item([self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())])
        if item:
            self.tree.setCurrentItem(item)

    def _on_item_clicked(self, item):
        # Extract version name from display text
        text = item.text(0)
        version_name = text.split(" (")[0]  # Extract before the first "("
        self.version_selected.emit(version_name)