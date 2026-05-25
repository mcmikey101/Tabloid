# ui/widgets/classification_plots.py

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QFileDialog,
    QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
from io import BytesIO


class ConfusionMatrixWidget(QWidget):
    """Widget for displaying and exporting confusion matrix visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.confusion_matrix = None
        self.classes = None
        self.y_test = None
        self.y_pred = None
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI for the confusion matrix widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Матрица ошибок")
        title.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
        layout.addWidget(title)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: #1a1a25; border: 1px solid #3a3d4a; border-radius: 4px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(250)
        layout.addWidget(self.image_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("Экспорт в PNG")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
            QPushButton:pressed {
                background-color: #3d54c8;
            }
        """)
        self.export_btn.clicked.connect(self._export_as_png)
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)
    
    def set_data(self, confusion_matrix, classes, y_test, y_pred):
        """Set the confusion matrix data and render it."""
        self.confusion_matrix = confusion_matrix
        self.classes = classes
        self.y_test = y_test
        self.y_pred = y_pred
        self._render_matrix()
    
    def _render_matrix(self):
        """Render the confusion matrix as an image."""
        if self.confusion_matrix is None:
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 5), dpi=100)
        fig.patch.set_facecolor('#262738')
        ax.set_facecolor('#1a1a25')
        
        # Create heatmap
        im = ax.imshow(self.confusion_matrix, interpolation='nearest', cmap=plt.cm.Blues)
        
        # Set ticks and labels
        tick_marks = np.arange(len(self.classes))
        ax.set_xticks(tick_marks)
        ax.set_yticks(tick_marks)
        ax.set_xticklabels(self.classes, color='#b0b0b0')
        ax.set_yticklabels(self.classes, color='#b0b0b0')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(colors='#b0b0b0')
        
        # Add text annotations
        cm = self.confusion_matrix
        thresh = cm.max() / 2.
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                color = "white" if cm[i, j] > thresh else "black"
                ax.text(j, i, f'{cm[i, j]}',
                       horizontalalignment="center",
                       color=color, fontsize=12, fontweight='bold')
        
        # Labels
        ax.set_ylabel('Истинная метка', color='#b0b0b0', fontweight='bold')
        ax.set_xlabel('Предсказанная метка', color='#b0b0b0', fontweight='bold')
        ax.set_title('Матрица ошибок', color='#e0e0e0', fontweight='bold', pad=20)
        
        # Tight layout
        plt.tight_layout()
        
        # Convert to QPixmap
        buf = BytesIO()
        fig.savefig(buf, format='png', facecolor='#262738')
        buf.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        
        # Scale to fit widget
        scaled_pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        plt.close(fig)
    
    def _export_as_png(self):
        """Export the confusion matrix as a PNG file."""
        if self.confusion_matrix is None:
            QMessageBox.warning(self, "Предупреждение", "Нет матрицы ошибок для экспорта.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить матрицу ошибок",
            "",
            "PNG-файлы (*.png);;SVG-файлы (*.svg)"
        )
        
        if not file_path:
            return
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 7), dpi=150)
            fig.patch.set_facecolor('#262738')
            ax.set_facecolor('#1a1a25')
            
            # Create heatmap
            im = ax.imshow(self.confusion_matrix, interpolation='nearest', cmap=plt.cm.Blues)
            
            # Set ticks and labels
            tick_marks = np.arange(len(self.classes))
            ax.set_xticks(tick_marks)
            ax.set_yticks(tick_marks)
            ax.set_xticklabels(self.classes, color='#b0b0b0')
            ax.set_yticklabels(self.classes, color='#b0b0b0')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.ax.tick_params(colors='#b0b0b0')
            
            # Add text annotations
            cm = self.confusion_matrix
            thresh = cm.max() / 2.
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    color = "white" if cm[i, j] > thresh else "black"
                    ax.text(j, i, f'{cm[i, j]}',
                           horizontalalignment="center",
                           color=color, fontsize=12, fontweight='bold')
            
            # Labels
            ax.set_ylabel('Истинная метка', color='#b0b0b0', fontweight='bold')
            ax.set_xlabel('Предсказанная метка', color='#b0b0b0', fontweight='bold')
            ax.set_title('Матрица ошибок', color='#e0e0e0', fontweight='bold', pad=20)
            
            # Tight layout
            plt.tight_layout()
            
            # Save file
            fig.savefig(file_path, facecolor='#262738', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            
            QMessageBox.information(self, "Успех", f"Матрица ошибок сохранена в:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать матрицу ошибок:\n{str(e)}")


class ROCCurveWidget(QWidget):
    """Widget for displaying and exporting ROC curve visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roc_data = None
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI for the ROC curve widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("ROC-кривая")
        title.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
        layout.addWidget(title)
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: #1a1a25; border: 1px solid #3a3d4a; border-radius: 4px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(250)
        layout.addWidget(self.image_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("Экспорт в PNG")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #5b7cfa;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4c63d2;
            }
            QPushButton:pressed {
                background-color: #3d54c8;
            }
        """)
        self.export_btn.clicked.connect(self._export_as_png)
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)
    
    def set_data(self, roc_data):
        """Set the ROC curve data and render it."""
        self.roc_data = roc_data
        self._render_curve()
    
    def _render_curve(self):
        """Render the ROC curve as an image."""
        if not self.roc_data:
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 5), dpi=100)
        fig.patch.set_facecolor('#262738')
        ax.set_facecolor('#1a1a25')
        
        # Plot diagonal line
        ax.plot([0, 1], [0, 1], 'k--', color='#666666', linewidth=1.5, label='Случайно')
        
        # Plot ROC curves
        colors = ['#5b7cfa', '#51cf66', '#ff6b6b', '#ffd43b']
        for idx, (key, data) in enumerate(self.roc_data.items()):
            fpr = data['fpr']
            tpr = data['tpr']
            roc_auc = data['auc']
            class_label = data['class']
            
            color = colors[idx % len(colors)]
            ax.plot(fpr, tpr, color=color, linewidth=2.5,
                   label=f'Класс {class_label} (AUC = {roc_auc:.3f})')
        
        # Configure axes
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('Доля ложноположительных', color='#b0b0b0', fontweight='bold')
        ax.set_ylabel('Доля истинноположительных', color='#b0b0b0', fontweight='bold')
        ax.set_title('ROC-кривая', color='#e0e0e0', fontweight='bold', pad=20)
        
        # Configure legend
        ax.legend(loc="lower right", framealpha=0.9, facecolor='#1a1a25', 
                 edgecolor='#3a3d4a', labelcolor='#b0b0b0')
        
        # Tick colors
        ax.tick_params(colors='#b0b0b0')
        
        # Grid
        ax.grid(True, alpha=0.2, color='#666666')
        
        # Tight layout
        plt.tight_layout()
        
        # Convert to QPixmap
        buf = BytesIO()
        fig.savefig(buf, format='png', facecolor='#262738')
        buf.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        
        # Scale to fit widget
        scaled_pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        plt.close(fig)
    
    def _export_as_png(self):
        """Export the ROC curve as a PNG file."""
        if not self.roc_data:
            QMessageBox.warning(self, "Предупреждение", "Нет ROC-кривой для экспорта.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить ROC-кривую",
            "",
            "PNG-файлы (*.png);;SVG-файлы (*.svg)"
        )
        
        if not file_path:
            return
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 7), dpi=150)
            fig.patch.set_facecolor('#262738')
            ax.set_facecolor('#1a1a25')
            
            # Plot diagonal line
            ax.plot([0, 1], [0, 1], 'k--', color='#666666', linewidth=2, label='Случайно')
            
            # Plot ROC curves
            colors = ['#5b7cfa', '#51cf66', '#ff6b6b', '#ffd43b']
            for idx, (key, data) in enumerate(self.roc_data.items()):
                fpr = data['fpr']
                tpr = data['tpr']
                roc_auc = data['auc']
                class_label = data['class']
                
                color = colors[idx % len(colors)]
                ax.plot(fpr, tpr, color=color, linewidth=2.5,
                       label=f'Класс {class_label} (AUC = {roc_auc:.3f})')
            
            # Configure axes
            ax.set_xlim([0.0, 1.0])
            ax.set_ylim([0.0, 1.05])
            ax.set_xlabel('Доля ложноположительных', color='#b0b0b0', fontweight='bold', fontsize=12)
            ax.set_ylabel('Доля истинноположительных', color='#b0b0b0', fontweight='bold', fontsize=12)
            ax.set_title('ROC-кривая', color='#e0e0e0', fontweight='bold', pad=20, fontsize=14)
            
            # Configure legend
            ax.legend(loc="lower right", framealpha=0.9, facecolor='#1a1a25', 
                     edgecolor='#3a3d4a', labelcolor='#b0b0b0', fontsize=10)
            
            # Tick colors and size
            ax.tick_params(colors='#b0b0b0', labelsize=10)
            
            # Grid
            ax.grid(True, alpha=0.2, color='#666666')
            
            # Tight layout
            plt.tight_layout()
            
            # Save file
            fig.savefig(file_path, facecolor='#262738', edgecolor='none', bbox_inches='tight')
            plt.close(fig)
            
            QMessageBox.information(self, "Успех", f"ROC-кривая сохранена в:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать ROC-кривую:\n{str(e)}")
