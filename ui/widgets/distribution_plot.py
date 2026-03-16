import pandas as pd
import seaborn as sns

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DistributionPlotWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.df = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Distribution")
        layout.addWidget(label)

        self.column_selector = QComboBox()
        self.column_selector.currentTextChanged.connect(self._plot_selected_column)

        layout.addWidget(self.column_selector)

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(self.canvas)

    def load_dataframe(self, df: pd.DataFrame):
        self.df = df
        self.column_selector.clear()
        self.column_selector.addItems(df.columns)

    def _plot_selected_column(self, column_name):

        if self.df is None or column_name not in self.df.columns:
            return

        series = self.df[column_name]

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if pd.api.types.is_numeric_dtype(series):
            sns.histplot(series.dropna(), kde=True, ax=ax)
        else:
            sns.countplot(x=series.astype(str), ax=ax)
            ax.tick_params(axis="x", rotation=45)

        ax.set_title(column_name)

        self.canvas.draw()