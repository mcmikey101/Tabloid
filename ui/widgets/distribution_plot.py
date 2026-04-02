import pandas as pd
import seaborn as sns
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTabWidget, QTextEdit
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import json

from PySide6.QtCore import Signal


class DistributionPlotWidget(QWidget):

    column_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.df = None
        self.version_meta = None
        self.current_dataset = None
        self.current_version = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 6px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d4;
            }
        """)
        
        # Plot tab
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        
        # Header with version info
        header_layout = QHBoxLayout()
        self.version_label = QLabel("Version: None")
        self.version_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.version_label)
        header_layout.addStretch()
        plot_layout.addLayout(header_layout)
        
        # Plot type selector
        plot_type_layout = QHBoxLayout()
        plot_label = QLabel("Plot Type:")
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Histogram", "Box Plot", "Violin Plot", "Count Plot"])
        self.plot_type_combo.currentTextChanged.connect(self._on_plot_type_changed)
        plot_type_layout.addWidget(plot_label)
        plot_type_layout.addWidget(self.plot_type_combo)
        plot_type_layout.addStretch()
        plot_layout.addLayout(plot_type_layout)
        
        # Column info label
        self.column_label = QLabel("Select a column from the table to visualize")
        self.column_label.setStyleSheet("color: gray; font-size: 10px;")
        plot_layout.addWidget(self.column_label)

        # Figure for plotting
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        plot_layout.addWidget(self.canvas)
        
        self.tabs.addTab(plot_widget, "Distribution")
        
        # Metadata tab
        metadata_widget = QWidget()
        metadata_layout = QVBoxLayout(metadata_widget)
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 14px;
                background-color: #fafafa;
                color: #333333;
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                line-height: 1.6;
            }
        """)
        metadata_layout.addWidget(self.metadata_text)
        
        self.tabs.addTab(metadata_widget, "Version Info")
        
        layout.addWidget(self.tabs)

    def load_dataframe(self, df: pd.DataFrame, dataset_name: str = None, version_name: str = None):
        """Load dataframe and optional version info."""
        self.df = df
        self.current_dataset = dataset_name
        self.current_version = version_name
        
        if version_name:
            self.version_label.setText(f"Version: {version_name}")
            self._load_version_metadata(dataset_name, version_name)

    def _load_version_metadata(self, dataset_name: str, version_name: str):
        """Load and display version metadata from versions_meta.json."""
        try:
            meta_path = Path("data") / dataset_name / "versions_meta.json"
            
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    all_versions = json.load(f)
                
                if version_name in all_versions:
                    self.version_meta = all_versions[version_name]
                    self._display_metadata()
            else:
                self.metadata_text.setText("No version metadata found.")
        except Exception as e:
            self.metadata_text.setText(f"Error loading metadata: {str(e)}")

    def _display_metadata(self):
        """Display metadata in a formatted way."""
        if not self.version_meta:
            return
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"VERSION: {self.current_version}")
        lines.append("=" * 60)
        
        # Parent
        parent = self.version_meta.get("parent", "None")
        lines.append(f"\nParent Version: {parent}")
        
        # Operation
        operation = self.version_meta.get("operation", "Unknown")
        lines.append(f"Operation: {operation}")
        
        # Config
        config = self.version_meta.get("config", {})
        if config:
            lines.append("\n" + "-" * 60)
            lines.append("CONFIGURATION:")
            lines.append("-" * 60)
            self._format_config(config, lines, indent=0)
        
        lines.append("\n" + "=" * 60)
        self.metadata_text.setText("\n".join(lines))

    def _format_config(self, obj, lines, indent=0):
        """Recursively format configuration object."""
        indent_str = "  " * indent
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{indent_str}{key}:")
                    self._format_config(value, lines, indent + 1)
                else:
                    lines.append(f"{indent_str}{key}: {value}")
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:10]):  # Limit to first 10 items
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent_str}[{i}]:")
                    self._format_config(item, lines, indent + 1)
                else:
                    lines.append(f"{indent_str}[{i}] {item}")
            if len(obj) > 10:
                lines.append(f"{indent_str}... and {len(obj) - 10} more items")

    def plot_column(self, column_name: str):
        """Plot the selected column."""
        if self.df is None or column_name not in self.df.columns:
            return
        
        self.column_label.setText(f"Column: {column_name} | Type: {self.df[column_name].dtype}")
        self._plot_selected_column(column_name)

    def _on_plot_type_changed(self):
        """Redraw plot when type changes."""
        column_text = self.column_label.text()
        if "Column:" in column_text:
            column_name = column_text.split("|")[0].replace("Column:", "").strip()
            if column_name in self.df.columns:
                self._plot_selected_column(column_name)

    def _plot_selected_column(self, column_name: str):
        """Plot column with selected plot type."""
        if self.df is None or column_name not in self.df.columns:
            return
        
        series = self.df[column_name]
        plot_type = self.plot_type_combo.currentText()
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Sample data if too large
        max_samples = 10000
        if len(series) > max_samples:
            series = series.sample(n=max_samples, random_state=42)
        
        is_numeric = pd.api.types.is_numeric_dtype(series)
        
        try:
            if plot_type == "Histogram":
                if is_numeric:
                    use_kde = len(series) <= 5000
                    sns.histplot(series.dropna(), kde=use_kde, ax=ax, bins=30)
                    ax.set_title(f"Distribution of {column_name}")
                else:
                    self._plot_count(series, ax, column_name)
            
            elif plot_type == "Box Plot":
                if is_numeric:
                    sns.boxplot(y=series.dropna(), ax=ax)
                    ax.set_title(f"Box Plot of {column_name}")
                    ax.set_ylabel(column_name)
                else:
                    ax.text(0.5, 0.5, "Box plot only for numeric columns",
                        ha="center", va="center", transform=ax.transAxes)
                    ax.set_title(f"{column_name} (Non-numeric)")
            
            elif plot_type == "Violin Plot":
                if is_numeric:
                    sns.violinplot(y=series.dropna(), ax=ax)
                    ax.set_title(f"Violin Plot of {column_name}")
                    ax.set_ylabel(column_name)
                else:
                    ax.text(0.5, 0.5, "Violin plot only for numeric columns",
                        ha="center", va="center", transform=ax.transAxes)
                    ax.set_title(f"{column_name} (Non-numeric)")
            
            elif plot_type == "Count Plot":
                self._plot_count(series, ax, column_name)
            
            ax.tick_params(axis="x", rotation=45)
            self.figure.tight_layout()
        except Exception as e:
            ax.text(0.5, 0.5, f"Error plotting: {str(e)}",
                ha="center", va="center", transform=ax.transAxes)
        
        self.canvas.draw()

    def _plot_count(self, series, ax, column_name):
        """Plot count plot for categorical data."""
        unique_count = series.nunique()
        if unique_count > 50:
            top_categories = series.value_counts().head(20).index
            series_filtered = series[series.isin(top_categories)]
            sns.countplot(x=series_filtered.astype(str), ax=ax)
            ax.set_xlabel(f"{column_name} (Top 20 categories)")
        else:
            sns.countplot(x=series.astype(str), ax=ax)
            ax.set_xlabel(column_name)
        ax.set_title(f"Count Plot of {column_name}")