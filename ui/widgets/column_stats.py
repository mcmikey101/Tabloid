from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit


class ColumnStatsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Column Statistics")
        layout.addWidget(label)

        self.text = QTextEdit()
        self.text.setReadOnly(True)

        layout.addWidget(self.text)

    def display_stats(self, stats: dict):
        lines = []

        for key, value in stats.items():
            lines.append(f"{key}: {value}")

        self.text.setText("\n".join(lines))