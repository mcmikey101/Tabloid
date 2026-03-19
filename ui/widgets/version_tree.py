from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal


class VersionTreeWidget(QWidget):
    version_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Versions")
        layout.addWidget(label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self.tree)

    def load_versions(self, version_graph):
        """
        version_graph format example:
        {
            "raw": None,
            "cleaned_v1": "raw",
            "encoded_v1": "cleaned_v1"
        }
        """
        self.tree.clear()
        nodes = {}

        for version, parent in version_graph.items():
            item = QTreeWidgetItem([version])
            nodes[version] = item

            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                nodes[parent].addChild(item)

    def select_version(self, version_name):
        """Select the item with the given version name."""
        def find_item(items):
            for item in items:
                if item.text(0) == version_name:
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
        self.version_selected.emit(item.text(0))