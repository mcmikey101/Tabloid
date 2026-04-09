import pandas as pd
import seaborn as sns
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QTabWidget, QTextEdit, QPushButton, QDialog, QListWidget, QListWidgetItem, QCheckBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import json

from PySide6.QtCore import Signal, Qt


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
                border: 1px solid #3a3d4a;
                background-color: #262738;
            }
            QTabBar::tab {
                background-color: #2b2d42;
                color: #e0e0e0;
                padding: 6px 12px;
                margin-right: 2px;
                border: 1px solid #3a3d4a;
            }
            QTabBar::tab:selected {
                background-color: #5b7cfa;
                color: #1e1f2e;
                border: 1px solid #5b7cfa;
            }
        """)
        
        # Plot tab
        plot_widget = QWidget()
        plot_widget.setStyleSheet("background-color: #262738;")
        plot_layout = QVBoxLayout(plot_widget)
        
        # Header with version info
        header_layout = QHBoxLayout()
        self.version_label = QLabel("Version: None")
        self.version_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #e0e0e0;")
        header_layout.addWidget(self.version_label)
        header_layout.addStretch()
        plot_layout.addLayout(header_layout)
        
        # Plot type selector
        plot_type_layout = QHBoxLayout()
        plot_label = QLabel("Plot Type:")
        plot_label.setStyleSheet("color: #e0e0e0;")
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Histogram", "Box Plot", "Violin Plot", "Count Plot"])
        self.plot_type_combo.currentTextChanged.connect(self._on_plot_type_changed)
        plot_type_layout.addWidget(plot_label)
        plot_type_layout.addWidget(self.plot_type_combo)
        plot_type_layout.addStretch()
        plot_layout.addLayout(plot_type_layout)
        
        # Column info label
        self.column_label = QLabel("Select a column from the table to visualize")
        self.column_label.setStyleSheet("color: #999999; font-size: 10px;")
        plot_layout.addWidget(self.column_label)

        # Figure for plotting
        self.figure = Figure(figsize=(8, 4), dpi=100, facecolor='#262738', edgecolor='#3a3d4a')
        self.figure.patch.set_facecolor('#262738')
        self.canvas = FigureCanvasQTAgg(self.figure)
        plot_layout.addWidget(self.canvas)
        
        self.tabs.addTab(plot_widget, "Distribution")
        
        # Metadata tab
        metadata_widget = QWidget()
        metadata_widget.setStyleSheet("background-color: #262738;")
        metadata_layout = QVBoxLayout(metadata_widget)
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setStyleSheet("""
            QTextEdit {
                font-family: 'JetBrains Mono', 'Courier New', monospace;
                font-size: 12px;
                background-color: #262738;
                color: #e0e0e0;
                padding: 12px;
                border: 1px solid #3a3d4a;
                border-radius: 3px;
            }
        """)
        metadata_layout.addWidget(self.metadata_text)
        
        self.tabs.addTab(metadata_widget, "Version Info")
        
        # Scatter plot tab
        scatter_widget = QWidget()
        scatter_widget.setStyleSheet("background-color: #262738;")
        scatter_layout = QVBoxLayout(scatter_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        select_cols_label = QLabel("Columns:")
        select_cols_label.setStyleSheet("color: #e0e0e0;")
        self.scatter_select_btn = QPushButton("Select 2-3 Features...")
        self.scatter_select_btn.clicked.connect(self._show_column_selection_dialog)
        self.scatter_cols_label = QLabel("None selected")
        self.scatter_cols_label.setStyleSheet("color: #999999; font-size: 10px;")
        
        color_label = QLabel("Color by:")
        color_label.setStyleSheet("color: #e0e0e0;")
        self.scatter_color_combo = QComboBox()
        self.scatter_color_combo.currentTextChanged.connect(self._on_scatter_plot_changed)
        
        controls_layout.addWidget(select_cols_label)
        controls_layout.addWidget(self.scatter_select_btn)
        controls_layout.addWidget(self.scatter_cols_label)
        controls_layout.addStretch()
        controls_layout.addWidget(color_label)
        controls_layout.addWidget(self.scatter_color_combo)
        
        scatter_layout.addLayout(controls_layout)
        
        # Scatter figure
        self.scatter_figure = Figure(figsize=(8, 4), dpi=100, facecolor='#262738', edgecolor='#3a3d4a')
        self.scatter_figure.patch.set_facecolor('#262738')
        self.scatter_canvas = FigureCanvasQTAgg(self.scatter_figure)
        scatter_layout.addWidget(self.scatter_canvas)
        
        self.tabs.addTab(scatter_widget, "Scatter Plot")
        
        layout.addWidget(self.tabs)
        
        # Initialize selected columns for scatter plot
        self.selected_scatter_columns = None

    def load_dataframe(self, df: pd.DataFrame, dataset_name: str = None, version_name: str = None):
        """Load dataframe and optional version info."""
        self.df = df
        self.current_dataset = dataset_name
        self.current_version = version_name
        
        # Update color column options for scatter plot - include ALL columns
        if df is not None:
            all_cols = df.columns.tolist()
            self.scatter_color_combo.blockSignals(True)  # Prevent triggering plot on update
            self.scatter_color_combo.clear()
            self.scatter_color_combo.addItems(all_cols)
            self.scatter_color_combo.blockSignals(False)
        
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
            
            # Apply dark theme styling to axes
            self._apply_dark_theme_styling(ax)
            
            ax.tick_params(axis="x", rotation=45)
            self.figure.tight_layout()
        except Exception as e:
            ax.text(0.5, 0.5, f"Error plotting: {str(e)}",
                ha="center", va="center", transform=ax.transAxes)
        
        self.canvas.draw()

    def _apply_dark_theme_styling(self, ax):
        """Apply dark theme styling to matplotlib axes."""
        # Background colors
        ax.set_facecolor('#262738')
        ax.patch.set_facecolor('#262738')
        
        # Text and spine colors
        ax.spines['bottom'].set_color('#3a3d4a')
        ax.spines['left'].set_color('#3a3d4a')
        ax.spines['top'].set_color('#3a3d4a')
        ax.spines['right'].set_color('#3a3d4a')
        
        # Tick and label colors
        ax.tick_params(colors='#e0e0e0')
        ax.xaxis.label.set_color('#e0e0e0')
        ax.yaxis.label.set_color('#e0e0e0')
        ax.title.set_color('#e0e0e0')
        
        # Grid styling
        ax.grid(True, alpha=0.1, color='#3a3d4a', linestyle='--')

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

    # ===== Scatter Plot Methods =====
    
    def _show_column_selection_dialog(self):
        """Show dialog to select 2-3 numerical columns for scatter plot."""
        if self.df is None:
            return
        
        # Get numerical columns
        numerical_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numerical_cols) < 2:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Error", "Need at least 2 numerical columns for scatter plot.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns for Scatter Plot")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select 2-3 numerical columns for scatter plot:")
        label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #262738;
                color: #e0e0e0;
                border: 1px solid #3a3d4a;
            }
            QListWidget::item:selected {
                background-color: #5b7cfa;
            }
        """)
        
        checkboxes = []
        for col in numerical_cols:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Check if previously selected
            if self.selected_scatter_columns and col in self.selected_scatter_columns:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        
        def on_ok():
            selected = []
            for i in range(list_widget.count()):
                if list_widget.item(i).checkState() == Qt.CheckState.Checked:
                    selected.append(list_widget.item(i).text())
            
            if len(selected) < 2 or len(selected) > 3:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(dialog, "Error", "Select 2 or 3 columns.")
                return
            
            self.selected_scatter_columns = selected
            self.scatter_cols_label.setText(f"{len(selected)}D: {', '.join(selected[:2])}" + 
                                           (f", {selected[2]}" if len(selected) == 3 else ""))
            self._plot_scatter()
            dialog.accept()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _on_scatter_plot_changed(self):
        """Redraw scatter plot when color column changes."""
        if self.selected_scatter_columns:
            self._plot_scatter()
    
    def _plot_scatter(self):
        """Draw scatter plot with selected columns and color column."""
        if self.df is None or not self.selected_scatter_columns:
            return
        
        color_col = self.scatter_color_combo.currentText()
        if not color_col or color_col not in self.df.columns:
            return
        
        df = self.df.copy()
        
        # Remove rows with missing values in selected columns
        cols_to_plot = self.selected_scatter_columns + [color_col]
        df = df[cols_to_plot].dropna()
        
        # Limit data points to prevent performance issues
        max_points = 1500
        if len(df) > max_points:
            df = df.sample(n=max_points, random_state=42)
        
        if df.empty:
            return
        
        self.scatter_figure.clear()
        
        try:
            if len(self.selected_scatter_columns) == 2:
                # 2D scatter plot
                ax = self.scatter_figure.add_subplot(111)
                
                # Get unique classes and create color map
                classes = df[color_col].unique()
                colors = plt.cm.tab10(np.linspace(0, 1, len(classes)))
                color_map = {cls: colors[i] for i, cls in enumerate(classes)}
                
                for cls in classes:
                    mask = df[color_col] == cls
                    ax.scatter(
                        df[mask][self.selected_scatter_columns[0]],
                        df[mask][self.selected_scatter_columns[1]],
                        label=str(cls),
                        alpha=0.6,
                        s=50,
                        color=color_map[cls]
                    )
                
                ax.set_xlabel(self.selected_scatter_columns[0])
                ax.set_ylabel(self.selected_scatter_columns[1])
                ax.set_title(f"Scatter Plot: {self.selected_scatter_columns[0]} vs {self.selected_scatter_columns[1]}")
                ax.legend(title=color_col, loc='best', fontsize=8)
                self._apply_dark_theme_styling(ax)
            
            else:  # 3D scatter plot
                ax = self.scatter_figure.add_subplot(111, projection='3d')
                
                # Get unique classes and create color map
                classes = df[color_col].unique()
                colors = plt.cm.tab10(np.linspace(0, 1, len(classes)))
                color_map = {cls: colors[i] for i, cls in enumerate(classes)}
                
                for cls in classes:
                    mask = df[color_col] == cls
                    ax.scatter(
                        df[mask][self.selected_scatter_columns[0]],
                        df[mask][self.selected_scatter_columns[1]],
                        df[mask][self.selected_scatter_columns[2]],
                        label=str(cls),
                        alpha=0.6,
                        s=50,
                        color=color_map[cls]
                    )
                
                ax.set_xlabel(self.selected_scatter_columns[0])
                ax.set_ylabel(self.selected_scatter_columns[1])
                ax.set_zlabel(self.selected_scatter_columns[2])
                ax.set_title(f"3D Scatter Plot")
                ax.legend(title=color_col, loc='best', fontsize=8)
                
                # Apply dark theme to 3D plot
                ax.xaxis.pane.fill = False
                ax.yaxis.pane.fill = False
                ax.zaxis.pane.fill = False
                ax.xaxis.pane.set_edgecolor('#3a3d4a')
                ax.yaxis.pane.set_edgecolor('#3a3d4a')
                ax.zaxis.pane.set_edgecolor('#3a3d4a')
                ax.xaxis.label.set_color('#e0e0e0')
                ax.yaxis.label.set_color('#e0e0e0')
                ax.zaxis.label.set_color('#e0e0e0')
                ax.title.set_color('#e0e0e0')
                ax.tick_params(colors='#e0e0e0')
            
            self.scatter_figure.tight_layout()
        except Exception as e:
            ax = self.scatter_figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error plotting: {str(e)}",
                ha="center", va="center", transform=ax.transAxes, color='#e0e0e0')
        
        self.scatter_canvas.draw()