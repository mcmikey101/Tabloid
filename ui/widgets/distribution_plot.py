import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DistributionPlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        label = QLabel("Distribution")
        layout.addWidget(label)

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(self.canvas)

    def plot_column(self, series: pd.Series):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if pd.api.types.is_numeric_dtype(series):
            ax.hist(series.dropna(), bins=30)
        else:
            counts = series.value_counts().head(20)
            ax.bar(counts.index.astype(str), counts.values)
            ax.tick_params(axis="x", rotation=45)

        ax.set_title(series.name)

        self.canvas.draw()