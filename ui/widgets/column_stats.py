from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, 
    QScrollArea, QProgressBar, QTableWidget, QTableWidgetItem, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QBrush


class ColumnStatsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        box = QGroupBox("Статистика столбца")
        box_layout = QVBoxLayout(box)
        
        # Scroll area for stats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3a3d4a;
                border-radius: 4px;
                background-color: #262738;
            }
        """)
        
        # Container for the stat card
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #262738;")
        self.card_layout = QVBoxLayout(scroll_content)
        self.card_layout.setContentsMargins(12, 12, 12, 12)
        self.card_layout.setSpacing(12)
        
        scroll.setWidget(scroll_content)
        box_layout.addWidget(scroll)
        layout.addWidget(box)

    def display_stats(self, stats: dict):
        """Display statistics in a structured stat card with dtype badge, count/missing bar, and statistics table."""
        # Clear previous content
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not stats:
            empty_label = QLabel("Статистика недоступна")
            empty_label.setStyleSheet("color: #999999;")
            self.card_layout.addWidget(empty_label)
            return
        
        # ===== Header with Column Name Only =====
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        column_name = stats.get("name", "Неизвестно")
        column_label = QLabel(column_name)
        column_font = QFont()
        column_font.setBold(True)
        column_font.setPointSize(12)
        column_label.setFont(column_font)
        column_label.setStyleSheet("color: #e0e0e0;")
        header_layout.addWidget(column_label)
        header_layout.addStretch()
        
        self.card_layout.addLayout(header_layout)
        
        # ===== Count / Missing Bar =====
        count = stats.get("count", 0)
        missing = stats.get("missing", 0)
        total = count + missing
        
        # Datatype as text
        dtype = stats.get("dtype", "unknown")
        dtype_label = QLabel(f"Тип: {dtype}")
        dtype_label.setStyleSheet("color: #b0b0b0; font-size: 10px;")
        self.card_layout.addWidget(dtype_label)
        
        if total > 0:
            count_layout = QHBoxLayout()
            
            count_label = QLabel(f"Количество: {count} / {total}")
            count_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")
            count_layout.addWidget(count_label)
            
            # Progress bar showing fill vs missing
            progress = QProgressBar()
            progress.setMaximumHeight(12)
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #3a3d4a;
                    border-radius: 2px;
                    background-color: #1a1a25;
                    padding: 0px;
                }
                QProgressBar::chunk {
                    background-color: #51cf66;
                    border-radius: 1px;
                }
            """)
            progress.setMaximum(100)
            progress.setValue(int((count / total) * 100) if total > 0 else 0)
            progress.setTextVisible(False)
            count_layout.addWidget(progress)
            
            if missing > 0:
                missing_label = QLabel(f"Пропущено: {missing} ({100 * missing / total:.1f}%)")
                missing_label.setStyleSheet("color: #ff6b6b; font-size: 10px;")
                count_layout.addWidget(missing_label)
            
            self.card_layout.addLayout(count_layout)
        
        # ===== Statistics Table / Info =====
        # Extract numeric statistics
        stat_keys = ["mean", "std", "min", "25%", "50%", "75%", "max"]
        numeric_stats = {k: stats.get(k) for k in stat_keys if k in stats and stats[k] is not None}
        
        # For numeric columns, show numeric stats
        if numeric_stats:
            table = QTableWidget()
            table.setMaximumHeight(120)
            table.setColumnCount(2)
            table.setRowCount(len(numeric_stats))
            table.setHorizontalHeaderLabels(["Статистика", "Значение"])
            table.setStyleSheet("""
                QTableWidget {
                    background-color: #1a1a25;
                    color: #e0e0e0;
                    border: 1px solid #3a3d4a;
                    border-radius: 3px;
                    gridline-color: #3a3d4a;
                }
                QHeaderView::section {
                    background-color: #2b2d42;
                    color: #e0e0e0;
                    padding: 4px;
                    border: none;
                    font-weight: bold;
                    font-size: 10px;
                }
                QTableWidget::item {
                    padding: 4px;
                    font-size: 10px;
                }
            """)
            
            row = 0
            for stat_name, stat_value in numeric_stats.items():
                # Stat name
                name_item = QTableWidgetItem(stat_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                name_item.setForeground(QBrush(QColor("#b0b0b0")))
                table.setItem(row, 0, name_item)
                
                # Stat value
                if isinstance(stat_value, float):
                    formatted_value = f"{stat_value:.4f}"
                else:
                    formatted_value = str(stat_value)
                value_item = QTableWidgetItem(formatted_value)
                value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                value_item.setForeground(QBrush(QColor("#51cf66")))
                table.setItem(row, 1, value_item)
                
                row += 1
            
            table.resizeColumnsToContents()
            table.setSelectionMode(table.SelectionMode.NoSelection)
            self.card_layout.addWidget(table)
        
        # For categorical columns, show unique values and top categories
        elif "top_values" in stats and stats["top_values"]:
            unique_label = QLabel(f"Уникальные значения: {stats.get('unique', 0)}")
            unique_label.setStyleSheet("color: #e0e0e0; font-size: 10px; font-weight: bold;")
            self.card_layout.addWidget(unique_label)
            
            top_values = stats.get("top_values", {})
            if top_values:
                top_label = QLabel("Частые категории:")
                top_label.setStyleSheet("color: #b0b0b0; font-size: 10px; margin-top: 6px;")
                self.card_layout.addWidget(top_label)
                
                # Create a table for top values
                top_table = QTableWidget()
                top_table.setMaximumHeight(120)
                top_table.setColumnCount(2)
                top_table.setRowCount(len(top_values))
                top_table.setHorizontalHeaderLabels(["Категория", "Количество"])
                top_table.setStyleSheet("""
                    QTableWidget {
                        background-color: #1a1a25;
                        color: #e0e0e0;
                        border: 1px solid #3a3d4a;
                        border-radius: 3px;
                        gridline-color: #3a3d4a;
                    }
                    QHeaderView::section {
                        background-color: #2b2d42;
                        color: #e0e0e0;
                        padding: 4px;
                        border: none;
                        font-weight: bold;
                        font-size: 10px;
                    }
                    QTableWidget::item {
                        padding: 4px;
                        font-size: 10px;
                    }
                """)
                
                row = 0
                for category, count in top_values.items():
                    # Category name
                    cat_item = QTableWidgetItem(str(category)[:30])  # Truncate long values
                    cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    cat_item.setForeground(QBrush(QColor("#b0b0b0")))
                    top_table.setItem(row, 0, cat_item)
                    
                    # Count
                    count_item = QTableWidgetItem(str(count))
                    count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    count_item.setForeground(QBrush(QColor("#51cf66")))
                    top_table.setItem(row, 1, count_item)
                    
                    row += 1
                
                top_table.resizeColumnsToContents()
                top_table.setSelectionMode(top_table.SelectionMode.NoSelection)
                self.card_layout.addWidget(top_table)
        
        self.card_layout.addStretch()
