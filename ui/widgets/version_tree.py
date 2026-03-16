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

    def _on_item_clicked(self, item):
        self.version_selected.emit(item.text(0))