from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt
import pandas as pd

from core import synthesis

class SynthesisDialog(QDialog):
    """Dialog for configuring data synthesis parameters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Synthesis")
        self.setModal(True)
        self.setGeometry(100, 100, 400, 250)
        self.current_df = None
        self.result_df = None
        self.result_config = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Synthesis mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Synthesis Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Gaussian Copula", "CTGAN", "TVAE"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
        # Rows to generate
        rows_layout = QHBoxLayout()
        rows_label = QLabel("Number of Rows:")
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setMaximum(100000)
        self.rows_spinbox.setValue(1000)
        rows_layout.addWidget(rows_label)
        rows_layout.addWidget(self.rows_spinbox)
        layout.addLayout(rows_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.synthesize_btn = QPushButton("Synthesize")
        self.cancel_btn = QPushButton("Cancel")
        self.synthesize_btn.clicked.connect(self._on_synthesize)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.synthesize_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Set the dataframe to synthesize."""
        self.current_df = df

    def _on_synthesize(self) -> None:
        """Handle synthesis button click."""
        if self.current_df is None:
            QMessageBox.warning(self, "Error", "No dataframe loaded.")
            return
        
        try:
            self.synthesize_btn.setEnabled(False)
            self.synthesize_btn.setText("Synthesizing...")
            
            mode = self.mode_combo.currentText()
            num_rows = self.rows_spinbox.value()
            
            # Map UI text to model type
            model_map = {
                "Gaussian Copula": "gaussian_copula",
                "CTGAN": "ctgan",
                "TVAE": "tvae"
            }
            model_type = model_map[mode]
            
            # Run synthesis
            self.result_df, self.result_config = synthesis.synthesize(
                df=self.current_df,
                num_rows=num_rows,
                model_type=model_type,
                evaluate=True
            )
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Synthesis Error",
                f"Failed to synthesize data: {str(e)}"
            )
        finally:
            self.synthesize_btn.setEnabled(True)
            self.synthesize_btn.setText("Synthesize")

    def get_results(self) -> tuple:
        """Return synthesized dataframe and config."""
        return self.result_df, self.result_config

    def get_parameters(self):
        """Return selected parameters."""
        return {
            "mode": self.mode_combo.currentText(),
            "rows": self.rows_spinbox.value()
        }