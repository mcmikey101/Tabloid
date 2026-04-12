import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import seaborn as sns
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QMessageBox, 
    QFileDialog, QListWidget, QListWidgetItem, QWidget, QCheckBox
)
from PySide6.QtCore import Qt


class ComparisonPlotsDialog(QDialog):
    """Dialog for comparing two columns from different versions."""
    
    def __init__(self, version_manager, file_store, dataset_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Plots")
        self.setModal(True)
        # Responsive sizing: use 80% of screen or min 900x600
        screen_geometry = self.screen().geometry()
        width = max(900, int(screen_geometry.width() * 0.8))
        height = max(600, int(screen_geometry.height() * 0.85))
        self.setGeometry(100, 100, width, height)
        self.version_manager = version_manager
        self.file_store = file_store
        self.dataset_name = dataset_name
        
        self.df1 = None
        self.df2 = None
        self.selected_scatter_cols_v1 = None
        self.selected_scatter_cols_v2 = None
        self.color_col_v1 = None
        self.color_col_v2 = None
        self.current_figure = None
        self.current_canvas = None
        
        self._init_ui()
        self._load_versions()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Reduce margins
        layout.setSpacing(4)  # Reduce spacing between items
        
        # First row: Version 1 and Column 1
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)
        version1_label = QLabel("V1:")
        version1_label.setStyleSheet("color: #e0e0e0;")
        self.version1_combo = QComboBox()
        self.version1_combo.currentTextChanged.connect(self._on_version1_changed)
        self.version1_combo.setMaximumWidth(200)
        col1_label = QLabel("Col1:")
        col1_label.setStyleSheet("color: #e0e0e0;")
        self.col1_combo = QComboBox()
        self.col1_combo.setMaximumWidth(200)
        row1_layout.addWidget(version1_label)
        row1_layout.addWidget(self.version1_combo)
        row1_layout.addWidget(col1_label)
        row1_layout.addWidget(self.col1_combo)
        row1_layout.addStretch()
        layout.addLayout(row1_layout)
        
        # Second row: Version 2 and Column 2
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)
        version2_label = QLabel("V2:")
        version2_label.setStyleSheet("color: #e0e0e0;")
        self.version2_combo = QComboBox()
        self.version2_combo.currentTextChanged.connect(self._on_version2_changed)
        self.version2_combo.setMaximumWidth(200)
        col2_label = QLabel("Col2:")
        col2_label.setStyleSheet("color: #e0e0e0;")
        self.col2_combo = QComboBox()
        self.col2_combo.setMaximumWidth(200)
        row2_layout.addWidget(version2_label)
        row2_layout.addWidget(self.version2_combo)
        row2_layout.addWidget(col2_label)
        row2_layout.addWidget(self.col2_combo)
        row2_layout.addStretch()
        layout.addLayout(row2_layout)
        
        # Third row: Plot Type and Scatter option
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(4)
        plot_type_label = QLabel("Type:")
        plot_type_label.setStyleSheet("color: #e0e0e0;")
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Histogram", "Box Plot", "Violin Plot", "KDE Plot"])
        self.plot_type_combo.setMaximumWidth(150)
        self.scatter_checkbox = QCheckBox("Scatter")
        self.scatter_checkbox.setStyleSheet("color: #e0e0e0;")
        self.scatter_checkbox.stateChanged.connect(self._on_scatter_option_changed)
        row3_layout.addWidget(plot_type_label)
        row3_layout.addWidget(self.plot_type_combo)
        row3_layout.addSpacing(20)
        row3_layout.addWidget(self.scatter_checkbox)
        row3_layout.addStretch()
        layout.addLayout(row3_layout)
        
        # Scatter column selection widgets - wrappable layout
        scatter_cols_layout = QHBoxLayout()
        scatter_cols_layout.setSpacing(3)
        
        # Version 1 scatter controls
        self.scatter1_select_btn = QPushButton("V1 Select")
        self.scatter1_select_btn.setStyleSheet("background-color: #5b7cfa; color: white; border: none; padding: 2px 6px; border-radius: 3px; font-size: 9px;")
        self.scatter1_select_btn.setMaximumWidth(80)
        self.scatter1_select_btn.clicked.connect(self._show_scatter1_column_selection)
        self.scatter1_cols_label = QLabel("-")
        self.scatter1_cols_label.setStyleSheet("color: #999999; font-size: 9px;")
        self.scatter1_cols_label.setMaximumWidth(80)
        
        self.color_combo_v1 = QComboBox()
        self.color_combo_v1.addItem("None")
        self.color_combo_v1.currentTextChanged.connect(self._on_color_v1_changed)
        self.color_combo_v1.setMaximumWidth(100)
        
        scatter_cols_layout.addWidget(self.scatter1_select_btn)
        scatter_cols_layout.addWidget(self.scatter1_cols_label)
        scatter_cols_layout.addWidget(self.color_combo_v1)
        scatter_cols_layout.addSpacing(8)
        
        # Version 2 scatter controls
        self.scatter2_select_btn = QPushButton("V2 Select")
        self.scatter2_select_btn.setStyleSheet("background-color: #5b7cfa; color: white; border: none; padding: 2px 6px; border-radius: 3px; font-size: 9px;")
        self.scatter2_select_btn.setMaximumWidth(80)
        self.scatter2_select_btn.clicked.connect(self._show_scatter2_column_selection)
        self.scatter2_cols_label = QLabel("-")
        self.scatter2_cols_label.setStyleSheet("color: #999999; font-size: 9px;")
        self.scatter2_cols_label.setMaximumWidth(80)
        
        self.color_combo_v2 = QComboBox()
        self.color_combo_v2.addItem("None")
        self.color_combo_v2.currentTextChanged.connect(self._on_color_v2_changed)
        self.color_combo_v2.setMaximumWidth(100)
        
        scatter_cols_layout.addWidget(self.scatter2_select_btn)
        scatter_cols_layout.addWidget(self.scatter2_cols_label)
        scatter_cols_layout.addWidget(self.color_combo_v2)
        scatter_cols_layout.addStretch()
        
        self.scatter_cols_widget = QWidget()
        self.scatter_cols_widget.setLayout(scatter_cols_layout)
        self.scatter_cols_widget.setVisible(False)
        layout.addWidget(self.scatter_cols_widget)
        
        # Plot canvas - add to layout with proper stretch
        self.figure = Figure(figsize=(10, 5), dpi=80, facecolor='#262738', edgecolor='#3a3d4a')
        self.figure.patch.set_facecolor('#262738')
        self.figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.1)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)  # Give plot area high stretch factor
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(3)
        button_layout.setContentsMargins(0, 4, 0, 0)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        refresh_btn.setMaximumWidth(80)
        refresh_btn.clicked.connect(self._refresh_plot)
        
        export_btn = QPushButton("Export")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #51cf66;
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #40c057;
            }
        """)
        export_btn.setMaximumWidth(80)
        export_btn.clicked.connect(self._export_plot)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #868e96;
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #748089;
            }
        """)
        close_btn.setMaximumWidth(80)
        close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setStyleSheet("background-color: #262738;")
        
        # Connect signals
        self.col1_combo.currentTextChanged.connect(self._refresh_plot)
        self.col2_combo.currentTextChanged.connect(self._refresh_plot)
        self.plot_type_combo.currentTextChanged.connect(self._refresh_plot)
    
    def _load_versions(self):
        """Load versions into version combo boxes."""
        try:
            versions = self.version_manager.list_versions(self.dataset_name)
            self.version1_combo.addItems(versions)
            self.version2_combo.addItems(versions)
            
            if len(versions) > 1:
                self.version2_combo.setCurrentIndex(1)
            else:
                self.version2_combo.setCurrentIndex(0)
                
            # Load initial columns
            self._on_version1_changed()
            self._on_version2_changed()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load versions: {str(e)}")
    
    def _on_version1_changed(self):
        """Handle version 1 change."""
        version = self.version1_combo.currentText()
        if not version:
            return
        
        try:
            self.df1 = self.file_store.load_version(self.dataset_name, version)
            self._update_color_options()
            self._populate_col1_options()
            self._refresh_plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load version: {str(e)}")
    
    def _on_version2_changed(self):
        """Handle version 2 change."""
        version = self.version2_combo.currentText()
        if not version:
            return
        
        try:
            self.df2 = self.file_store.load_version(self.dataset_name, version)
            self._update_color_options()
            self._populate_col2_options()
            self._refresh_plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load version: {str(e)}")
    
    def _populate_col1_options(self):
        """Populate column 1 options from version 1."""
        if self.df1 is None:
            return
        
        self.col1_combo.blockSignals(True)
        current_text = self.col1_combo.currentText()
        self.col1_combo.clear()
        
        numeric_cols = self.df1.select_dtypes(include=['number']).columns.tolist()
        self.col1_combo.addItems(numeric_cols)
        
        # Try to restore previous selection
        if current_text and current_text in numeric_cols:
            self.col1_combo.setCurrentText(current_text)
        
        self.col1_combo.blockSignals(False)
    
    def _populate_col2_options(self):
        """Populate column 2 options from version 2."""
        if self.df2 is None:
            return
        
        self.col2_combo.blockSignals(True)
        current_text = self.col2_combo.currentText()
        self.col2_combo.clear()
        
        numeric_cols = self.df2.select_dtypes(include=['number']).columns.tolist()
        self.col2_combo.addItems(numeric_cols)
        
        # Try to restore previous selection  
        if current_text and current_text in numeric_cols:
            self.col2_combo.setCurrentText(current_text)
        elif len(numeric_cols) > 1:
            self.col2_combo.setCurrentIndex(1)
        
        self.col2_combo.blockSignals(False)
    
    def _update_color_options(self):
        """Update color selection options for both versions separately."""
        # Update Version 1 color options
        self.color_combo_v1.blockSignals(True)
        current_text_v1 = self.color_combo_v1.currentText()
        self.color_combo_v1.clear()
        self.color_combo_v1.addItem("None")
        
        if self.df1 is not None:
            categorical_cols = []
            numeric_cols = []
            
            for col in sorted(self.df1.columns.tolist()):
                dtype = self.df1[col].dtype
                if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_categorical_dtype(dtype):
                    categorical_cols.append(col)
                elif pd.api.types.is_numeric_dtype(dtype):
                    numeric_cols.append(col)
            
            for col in categorical_cols:
                self.color_combo_v1.addItem(col)
            for col in numeric_cols:
                self.color_combo_v1.addItem(col)
            
            # Try to restore previous selection
            if current_text_v1 and current_text_v1 != "None" and self.color_combo_v1.findText(current_text_v1) >= 0:
                self.color_combo_v1.setCurrentText(current_text_v1)
        
        self.color_combo_v1.blockSignals(False)
        
        # Update Version 2 color options
        self.color_combo_v2.blockSignals(True)
        current_text_v2 = self.color_combo_v2.currentText()
        self.color_combo_v2.clear()
        self.color_combo_v2.addItem("None")
        
        if self.df2 is not None:
            categorical_cols = []
            numeric_cols = []
            
            for col in sorted(self.df2.columns.tolist()):
                dtype = self.df2[col].dtype
                if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_categorical_dtype(dtype):
                    categorical_cols.append(col)
                elif pd.api.types.is_numeric_dtype(dtype):
                    numeric_cols.append(col)
            
            for col in categorical_cols:
                self.color_combo_v2.addItem(col)
            for col in numeric_cols:
                self.color_combo_v2.addItem(col)
            
            # Try to restore previous selection
            if current_text_v2 and current_text_v2 != "None" and self.color_combo_v2.findText(current_text_v2) >= 0:
                self.color_combo_v2.setCurrentText(current_text_v2)
        
        self.color_combo_v2.blockSignals(False)
    
    def _on_color_v1_changed(self):
        """Handle color column change for Version 1."""
        self.color_col_v1 = self.color_combo_v1.currentText()
        if self.color_col_v1 == "None":
            self.color_col_v1 = None
        if self.scatter_checkbox.isChecked():
            self._refresh_plot()
    
    def _on_color_v2_changed(self):
        """Handle color column change for Version 2."""
        self.color_col_v2 = self.color_combo_v2.currentText()
        if self.color_col_v2 == "None":
            self.color_col_v2 = None
        if self.scatter_checkbox.isChecked():
            self._refresh_plot()
    
    def _on_scatter_option_changed(self):
        """Handle scatter plot checkbox change."""
        is_scatter = self.scatter_checkbox.isChecked()
        self.scatter_cols_widget.setVisible(is_scatter)
        self.plot_type_combo.setEnabled(not is_scatter)
        self._refresh_plot()
    
    def _refresh_plot(self):
        """Refresh the comparison plot."""
        try:
            if self.df1 is None or self.df2 is None:
                return
            
            col1 = self.col1_combo.currentText()
            col2 = self.col2_combo.currentText()
            
            if not col1 or not col2:
                return
            
            self.figure.clear()
            
            if self.scatter_checkbox.isChecked():
                self._plot_scatter_comparison()
            else:
                plot_type = self.plot_type_combo.currentText()
                self._plot_side_by_side(col1, col2, plot_type)
            
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create plot: {str(e)}")
    
    def _plot_side_by_side(self, col1: str, col2: str, plot_type: str):
        """Create side-by-side plots from two versions."""
        ax1, ax2 = self.figure.subplots(1, 2)
        
        # Left plot - from version 1
        ax1.set_facecolor('#262738')
        for spine in ax1.spines.values():
            spine.set_color('#3a3d4a')
        ax1.tick_params(colors='#e0e0e0')
        ax1.xaxis.label.set_color('#e0e0e0')
        ax1.yaxis.label.set_color('#e0e0e0')
        
        data1 = self.df1[col1].dropna() if col1 in self.df1.columns else pd.Series()
        version1 = self.version1_combo.currentText()
        
        if not data1.empty:
            if plot_type == "Histogram":
                ax1.hist(data1, bins=30, color='#5b7cfa', edgecolor='#3a3d4a', alpha=0.7)
            elif plot_type == "Box Plot":
                ax1.boxplot(data1, vert=True)
            elif plot_type == "Violin Plot":
                sns.violinplot(y=data1, ax=ax1, color='#5b7cfa')
            elif plot_type == "KDE Plot":
                data1.plot(kind='kde', ax=ax1, color='#5b7cfa', linewidth=2)
        
        ax1.set_title(f"{col1}\n({version1})", color='#e0e0e0', fontsize=12, fontweight='bold')
        
        # Right plot - from version 2
        ax2.set_facecolor('#262738')
        for spine in ax2.spines.values():
            spine.set_color('#3a3d4a')
        ax2.tick_params(colors='#e0e0e0')
        ax2.xaxis.label.set_color('#e0e0e0')
        ax2.yaxis.label.set_color('#e0e0e0')
        
        data2 = self.df2[col2].dropna() if col2 in self.df2.columns else pd.Series()
        version2 = self.version2_combo.currentText()
        
        if not data2.empty:
            if plot_type == "Histogram":
                ax2.hist(data2, bins=30, color='#ff6b6b', edgecolor='#3a3d4a', alpha=0.7)
            elif plot_type == "Box Plot":
                ax2.boxplot(data2, vert=True)
            elif plot_type == "Violin Plot":
                sns.violinplot(y=data2, ax=ax2, color='#ff6b6b')
            elif plot_type == "KDE Plot":
                data2.plot(kind='kde', ax=ax2, color='#ff6b6b', linewidth=2)
        
        ax2.set_title(f"{col2}\n({version2})", color='#e0e0e0', fontsize=12, fontweight='bold')
    
    def _plot_scatter_comparison(self):
        """Create two side-by-side scatter plots for comparison with optional coloring by class."""
        if not self.selected_scatter_cols_v1 or not self.selected_scatter_cols_v2:
            return
        
        ax1, ax2 = self.figure.subplots(1, 2)
        
        # Version 1 scatter plot
        self._create_scatter_subplot(
            ax=ax1,
            df=self.df1,
            cols=self.selected_scatter_cols_v1,
            version_name=self.version1_combo.currentText(),
            color_col=self.color_col_v1,
            default_color='#5b7cfa'
        )
        
        # Version 2 scatter plot
        self._create_scatter_subplot(
            ax=ax2,
            df=self.df2,
            cols=self.selected_scatter_cols_v2,
            version_name=self.version2_combo.currentText(),
            color_col=self.color_col_v2,
            default_color='#ff6b6b'
        )
    
    def _create_scatter_subplot(self, ax, df, cols, version_name, color_col=None, default_color='#5b7cfa'):
        """Create a single scatter subplot with optional color by column."""
        ax.set_facecolor('#262738')
        for spine in ax.spines.values():
            spine.set_color('#3a3d4a')
        ax.tick_params(colors='#e0e0e0')
        ax.xaxis.label.set_color('#e0e0e0')
        ax.yaxis.label.set_color('#e0e0e0')
        
        cols_available = [c for c in cols if c in df.columns]
        
        if len(cols_available) < 2:
            ax.text(0.5, 0.5, 'Insufficient columns selected', 
                   ha='center', va='center', color='#999999', transform=ax.transAxes)
            ax.set_title(f"Version: {version_name}", color='#e0e0e0', fontsize=12, fontweight='bold')
            return
        
        # Prepare data - use only first 2 columns for scatter plot coordinates
        x_col, y_col = cols_available[0], cols_available[1]
        plot_data = df[[x_col, y_col]].dropna()
        
        # Handle the third column (if selected) or color_col
        if color_col and color_col in df.columns and color_col != y_col and color_col != x_col:
            # Filter to rows that have both scatter and color data
            color_data_all = df[color_col]
            plot_data = plot_data[color_data_all.index.isin(plot_data.index)]
            color_data = color_data_all.loc[plot_data.index]
            
            scatter = self._scatter_with_coloring(
                ax, plot_data[x_col], plot_data[y_col], color_data
            )
            cbar = self.figure.colorbar(scatter, ax=ax)
            cbar.set_label(color_col, color='#e0e0e0')
            cbar.ax.tick_params(colors='#e0e0e0')
        elif len(cols_available) >= 3:
            # Use third selected column for coloring (if available)
            z_col = cols_available[2]
            color_data = df.loc[plot_data.index, z_col]
            
            scatter = self._scatter_with_coloring(
                ax, plot_data[x_col], plot_data[y_col], color_data
            )
            cbar = self.figure.colorbar(scatter, ax=ax)
            cbar.set_label(z_col, color='#e0e0e0')
            cbar.ax.tick_params(colors='#e0e0e0')
        else:
            # No coloring, use default color
            ax.scatter(plot_data[x_col], plot_data[y_col], 
                      alpha=0.6, s=50, color=default_color, edgecolors='#3a3d4a')
        
        ax.set_xlabel(x_col, color='#e0e0e0')
        ax.set_ylabel(y_col, color='#e0e0e0')
        ax.set_title(f"Version: {version_name}", color='#e0e0e0', fontsize=12, fontweight='bold')
    
    def _scatter_with_coloring(self, ax, x, y, c):
        """Create scatter plot with intelligent coloring based on data type."""
        import numpy as np
        
        # Check if color data is numeric or categorical
        if pd.api.types.is_numeric_dtype(c):
            # Numeric: use colormap
            scatter = ax.scatter(x, y, c=c, cmap='viridis', 
                               alpha=0.6, s=50, edgecolors='#3a3d4a')
        else:
            # Categorical: use discrete colors
            unique_classes = c.unique()
            colors = plt.cm.get_cmap('tab10')(np.linspace(0, 1, len(unique_classes)))
            
            scatter_list = []
            for idx, cls in enumerate(unique_classes):
                mask = c == cls
                scatter_list.append(ax.scatter(x[mask], y[mask], 
                                              color=colors[idx], label=str(cls),
                                              alpha=0.6, s=50, edgecolors='#3a3d4a'))
            
            ax.legend(loc='upper right', framealpha=0.9, 
                     facecolor='#262738', edgecolor='#3a3d4a',
                     labelcolor='#e0e0e0')
            
            # Return first scatter object for consistency, though legend is the main info
            scatter = scatter_list[0] if scatter_list else None
        
        return scatter
    
    def _show_scatter1_column_selection(self):
        """Show column selection dialog for version 1 scatter plot."""
        if self.df1 is None:
            QMessageBox.warning(self, "Warning", "Version 1 data not loaded.")
            return
        
        all_cols = self.df1.columns.tolist()
        self._show_column_selection_dialog("Version 1", all_cols, "scatter1")
    
    def _show_scatter2_column_selection(self):
        """Show column selection dialog for version 2 scatter plot."""
        if self.df2 is None:
            QMessageBox.warning(self, "Warning", "Version 2 data not loaded.")
            return
        
        all_cols = self.df2.columns.tolist()
        self._show_column_selection_dialog("Version 2", all_cols, "scatter2")
    
    def _show_column_selection_dialog(self, version_label: str, columns: list, target: str):
        """Show dialog to select columns for scatter plot."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select Columns - {version_label}")
        dialog.resize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel(f"Select 2-3 columns for {version_label}:\n(Uncheck to exclude a column)")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        selected_cols = self.selected_scatter_cols_v1 if target == "scatter1" else self.selected_scatter_cols_v2
        
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Check if it was previously selected
            if selected_cols and col in selected_cols:
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
                item = list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected.append(item.text())
            
            if len(selected) < 2:
                QMessageBox.warning(self, "Warning", "Please select at least 2 columns.")
                return
            
            if len(selected) > 3:
                QMessageBox.warning(self, "Warning", "Please select at most 3 columns.")
                return
            
            if target == "scatter1":
                self.selected_scatter_cols_v1 = selected
                self.scatter1_cols_label.setText(", ".join(selected))
            else:
                self.selected_scatter_cols_v2 = selected
                self.scatter2_cols_label.setText(", ".join(selected))
            
            self._refresh_plot()
            dialog.accept()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _export_plot(self):
        """Export the current plot as an image."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "comparison_plot",
            "PNG files (*.png);;JPG files (*.jpg);;PDF files (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            self.figure.savefig(file_path, facecolor='#262738', edgecolor='#3a3d4a', dpi=150)
            QMessageBox.information(self, "Success", f"Plot exported successfully to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export plot: {str(e)}")
