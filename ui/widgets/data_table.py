import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from PySide6.QtCore import Signal


class DataTableWidget(QWidget):
    column_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Data Preview")
        layout.addWidget(label)

        self.table = QTableWidget()
        self.table.cellClicked.connect(self._on_cell_clicked)

        layout.addWidget(self.table)

    def load_dataframe(self, df: pd.DataFrame, limit: int = 1000):
        df = df.head(limit)

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns.tolist())

        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = str(df.iat[row, col])
                self.table.setItem(row, col, QTableWidgetItem(value))

    def _on_cell_clicked(self, row, column):
        column_name = self.table.horizontalHeaderItem(column).text()
        self.column_selected.emit(column_name)