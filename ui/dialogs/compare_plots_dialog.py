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
        self.setGeometry(100, 100, 1200, 700)
        self.version_manager = version_manager
        self.file_store = file_store
        self.dataset_name = dataset_name
        
        self.df1 = None
        self.df2 = None
        self.selected_scatter_cols_v1 = None
        self.selected_scatter_cols_v2 = None
        self.current_figure = None
        self.current_canvas = None
        
        self._init_ui()
        self._load_versions()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Version selection for column 1
        version1_layout = QHBoxLayout()
        version1_label = QLabel("Version 1:")
        version1_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.version1_combo = QComboBox()
        self.version1_combo.currentTextChanged.connect(self._on_version1_changed)
        version1_layout.addWidget(version1_label)
        version1_layout.addWidget(self.version1_combo)
        version1_layout.addStretch()
        layout.addLayout(version1_layout)
        
        # Column 1 selection
        col1_layout = QHBoxLayout()
        col1_label = QLabel("Column 1:")
        col1_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.col1_combo = QComboBox()
        col1_layout.addWidget(col1_label)
        col1_layout.addWidget(self.col1_combo)
        col1_layout.addStretch()
        layout.addLayout(col1_layout)
        
        # Version selection for column 2
        version2_layout = QHBoxLayout()
        version2_label = QLabel("Version 2:")
        version2_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.version2_combo = QComboBox()
        self.version2_combo.currentTextChanged.connect(self._on_version2_changed)
        version2_layout.addWidget(version2_label)
        version2_layout.addWidget(self.version2_combo)
        version2_layout.addStretch()
        layout.addLayout(version2_layout)
        
        # Column 2 selection
        col2_layout = QHBoxLayout()
        col2_label = QLabel("Column 2:")
        col2_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.col2_combo = QComboBox()
        col2_layout.addWidget(col2_label)
        col2_layout.addWidget(self.col2_combo)
        col2_layout.addStretch()
        layout.addLayout(col2_layout)
        
        # Plot type selection
        plot_type_layout = QHBoxLayout()
        plot_type_label = QLabel("Plot Type:")
        plot_type_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Histogram", "Box Plot", "Violin Plot", "KDE Plot"])
        plot_type_layout.addWidget(plot_type_label)
        plot_type_layout.addWidget(self.plot_type_combo)
        plot_type_layout.addStretch()
        layout.addLayout(plot_type_layout)
        
        # Scatter plot options
        self.scatter_option_label = QLabel("Scatter Plot:")
        self.scatter_option_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.scatter_checkbox = QCheckBox("Compare Scatter Plots")
        self.scatter_checkbox.setStyleSheet("color: #e0e0e0;")
        self.scatter_checkbox.stateChanged.connect(self._on_scatter_option_changed)
        
        scatter_layout = QHBoxLayout()
        scatter_layout.addWidget(self.scatter_option_label)
        scatter_layout.addWidget(self.scatter_checkbox)
        scatter_layout.addStretch()
        layout.addLayout(scatter_layout)
        
        # Scatter column selection widgets
        scatter_cols_layout = QHBoxLayout()
        
        scatter1_label = QLabel("Select 2-3 columns for Version 1:")
        scatter1_label.setStyleSheet("color: #e0e0e0;")
        self.scatter1_select_btn = QPushButton("Select...")
        self.scatter1_select_btn.setStyleSheet("background-color: #5b7cfa; color: white; border: none; padding: 4px 8px; border-radius: 3px;")
        self.scatter1_select_btn.clicked.connect(self._show_scatter1_column_selection)
        self.scatter1_cols_label = QLabel("None selected")
        self.scatter1_cols_label.setStyleSheet("color: #999999; font-size: 10px;")
        
        scatter_cols_layout.addWidget(scatter1_label)
        scatter_cols_layout.addWidget(self.scatter1_select_btn)
        scatter_cols_layout.addWidget(self.scatter1_cols_label)
        scatter_cols_layout.addStretch()
        
        scatter2_label = QLabel("Select 2-3 columns for Version 2:")
        scatter2_label.setStyleSheet("color: #e0e0e0;")
        self.scatter2_select_btn = QPushButton("Select...")
        self.scatter2_select_btn.setStyleSheet("background-color: #5b7cfa; color: white; border: none; padding: 4px 8px; border-radius: 3px;")
        self.scatter2_select_btn.clicked.connect(self._show_scatter2_column_selection)
        self.scatter2_cols_label = QLabel("None selected")
        self.scatter2_cols_label.setStyleSheet("color: #999999; font-size: 10px;")
        
        scatter_cols_layout.addWidget(scatter2_label)
        scatter_cols_layout.addWidget(self.scatter2_select_btn)
        scatter_cols_layout.addWidget(self.scatter2_cols_label)
        
        self.scatter_cols_widget = QWidget()
        self.scatter_cols_widget.setLayout(scatter_cols_layout)
        self.scatter_cols_widget.setVisible(False)
        layout.addWidget(self.scatter_cols_widget)
        
        # Color by selection (for scatter plots)
        color_layout = QHBoxLayout()
        color_label = QLabel("Color by:")
        color_label.setStyleSheet("color: #e0e0e0;")
        self.color_combo = QComboBox()
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_combo)
        color_layout.addStretch()
        self.color_layout_widget = QWidget()
        self.color_layout_widget.setLayout(color_layout)
        self.color_layout_widget.setVisible(False)
        layout.addWidget(self.color_layout_widget)
        
        # Plot canvas
        self.figure = Figure(figsize=(10, 5), dpi=100, facecolor='#262738', edgecolor='#3a3d4a')
        self.figure.patch.set_facecolor('#262738')
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_plot)
        
        export_btn = QPushButton("Export Image")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #51cf66;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #40c057;
            }
        """)
        export_btn.clicked.connect(self._export_plot)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #868e96;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #748089;
            }
        """)
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
        self.color_combo.currentTextChanged.connect(self._refresh_plot)
    
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
        """Update color selection options from both versions."""
        self.color_combo.blockSignals(True)
        current_text = self.color_combo.currentText()
        self.color_combo.clear()
        
        # Combine columns from both dataframes
        all_cols = set()
        if self.df1 is not None:
            all_cols.update(self.df1.columns.tolist())
        if self.df2 is not None:
            all_cols.update(self.df2.columns.tolist())
        
        self.color_combo.addItems(sorted(list(all_cols)))
        
        # Try to restore previous selection
        if current_text and self.color_combo.findText(current_text) >= 0:
            self.color_combo.setCurrentText(current_text)
        
        self.color_combo.blockSignals(False)
    
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
        """Create two side-by-side scatter plots for comparison."""
        if not self.selected_scatter_cols_v1 or not self.selected_scatter_cols_v2:
            QMessageBox.warning(self, "Warning", "Please select columns for both versions.")
            return
        
        ax1, ax2 = self.figure.subplots(1, 2)
        
        # Version 1 scatter plot
        ax1.set_facecolor('#262738')
        for spine in ax1.spines.values():
            spine.set_color('#3a3d4a')
        ax1.tick_params(colors='#e0e0e0')
        ax1.xaxis.label.set_color('#e0e0e0')
        ax1.yaxis.label.set_color('#e0e0e0')
        
        version1 = self.version1_combo.currentText()
        cols_v1 = [c for c in self.selected_scatter_cols_v1 if c in self.df1.columns]
        
        if len(cols_v1) >= 2:
            data_v1 = self.df1[cols_v1].dropna()
            
            if len(cols_v1) == 2:
                scatter1 = ax1.scatter(data_v1[cols_v1[0]], data_v1[cols_v1[1]], 
                                      alpha=0.6, s=50, color='#5b7cfa', edgecolors='#3a3d4a')
                ax1.set_xlabel(cols_v1[0], color='#e0e0e0')
                ax1.set_ylabel(cols_v1[1], color='#e0e0e0')
            elif len(cols_v1) == 3:
                # 3D-like plot using color for third dimension
                scatter1 = ax1.scatter(data_v1[cols_v1[0]], data_v1[cols_v1[1]], 
                                      c=data_v1[cols_v1[2]], cmap='viridis', 
                                      alpha=0.6, s=50, edgecolors='#3a3d4a')
                ax1.set_xlabel(cols_v1[0], color='#e0e0e0')
                ax1.set_ylabel(cols_v1[1], color='#e0e0e0')
                cbar1 = self.figure.colorbar(scatter1, ax=ax1)
                cbar1.set_label(cols_v1[2], color='#e0e0e0')
                cbar1.ax.tick_params(colors='#e0e0e0')
        
        ax1.set_title(f"Version: {version1}", color='#e0e0e0', fontsize=12, fontweight='bold')
        
        # Version 2 scatter plot
        ax2.set_facecolor('#262738')
        for spine in ax2.spines.values():
            spine.set_color('#3a3d4a')
        ax2.tick_params(colors='#e0e0e0')
        ax2.xaxis.label.set_color('#e0e0e0')
        ax2.yaxis.label.set_color('#e0e0e0')
        
        version2 = self.version2_combo.currentText()
        cols_v2 = [c for c in self.selected_scatter_cols_v2 if c in self.df2.columns]
        
        if len(cols_v2) >= 2:
            data_v2 = self.df2[cols_v2].dropna()
            
            if len(cols_v2) == 2:
                scatter2 = ax2.scatter(data_v2[cols_v2[0]], data_v2[cols_v2[1]], 
                                      alpha=0.6, s=50, color='#ff6b6b', edgecolors='#3a3d4a')
                ax2.set_xlabel(cols_v2[0], color='#e0e0e0')
                ax2.set_ylabel(cols_v2[1], color='#e0e0e0')
            elif len(cols_v2) == 3:
                # 3D-like plot using color for third dimension
                scatter2 = ax2.scatter(data_v2[cols_v2[0]], data_v2[cols_v2[1]], 
                                      c=data_v2[cols_v2[2]], cmap='plasma', 
                                      alpha=0.6, s=50, edgecolors='#3a3d4a')
                ax2.set_xlabel(cols_v2[0], color='#e0e0e0')
                ax2.set_ylabel(cols_v2[1], color='#e0e0e0')
                cbar2 = self.figure.colorbar(scatter2, ax=ax2)
                cbar2.set_label(cols_v2[2], color='#e0e0e0')
                cbar2.ax.tick_params(colors='#e0e0e0')
        
        ax2.set_title(f"Version: {version2}", color='#e0e0e0', fontsize=12, fontweight='bold')
    
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
