from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QGroupBox, QScrollArea


class ColumnStatsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        box = QGroupBox("Column Statistics")
        box_layout = QVBoxLayout(box)
        
        # Scroll area for stats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
        """)
        
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("""
            QTextEdit {
                border: none;
                font-family: 'Courier New';
                font-size: 14px;
                background-color: #f9f9f9;
                padding: 8px;
            }
        """)
        scroll.setWidget(self.text)
        
        box_layout.addWidget(scroll)
        layout.addWidget(box)

    def display_stats(self, stats: dict):
        """Display statistics with better formatting."""
        lines = []
        lines.append("=" * 50)
        
        for key, value in stats.items():
            # Format key nicely
            formatted_key = key.replace("_", " ").title()
            
            # Format value
            if isinstance(value, float):
                formatted_value = f"{value:.4f}"
            elif isinstance(value, (list, dict)):
                formatted_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            else:
                formatted_value = str(value)
            
            lines.append(f"{formatted_key:<30} {formatted_value}")
    
            lines.append("=" * 50)
            self.text.setText("\n".join(lines))