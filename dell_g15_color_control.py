#!/usr/bin/env python3
import sys
import subprocess
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QSlider, QDoubleSpinBox, QPushButton, 
                             QGroupBox, QMessageBox, QStatusBar)
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

class DesignSystem:
    # Color Palette - Dell Gaming / Alienware inspired
    COLOR_BACKGROUND = "#121212"
    COLOR_SURFACE = "#1E1E1E"
    COLOR_PRIMARY = "#007BFF" # Intel Blue-ish
    COLOR_ACCENT = "#9146FF"  # Slight purple/gaming accent
    COLOR_TEXT = "#E0E0E0"
    COLOR_TEXT_DIM = "#A0A0A0"
    COLOR_SUCCESS = "#00C853"
    COLOR_DANGER = "#D50000"

    STYLESHEET = f"""
        QMainWindow {{
            background-color: {COLOR_BACKGROUND};
            color: {COLOR_TEXT};
        }}
        QWidget {{
            background-color: {COLOR_BACKGROUND};
            color: {COLOR_TEXT};
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-size: 14px;
        }}
        QGroupBox {{
            border: 1px solid #333;
            border-radius: 8px;
            margin-top: 20px;
            background-color: {COLOR_SURFACE};
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 5px 10px;
            background-color: {COLOR_BACKGROUND}; 
            border-radius: 4px;
            color: {COLOR_ACCENT};
        }}
        QPushButton {{
            background-color: {COLOR_PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #298DFF;
        }}
        QPushButton:pressed {{
            background-color: #0056B3;
        }}
        QSlider::groove:horizontal {{
            border: 1px solid #333;
            height: 8px;
            background: #2A2A2A;
            margin: 2px 0;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {COLOR_ACCENT};
            border: 1px solid {COLOR_ACCENT};
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #A665FF;
        }}
        QComboBox {{
            background-color: {COLOR_SURFACE};
            border: 1px solid #333;
            border-radius: 4px;
            padding: 5px;
            color: {COLOR_TEXT};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QDoubleSpinBox {{
            background-color: {COLOR_SURFACE};
            border: 1px solid #333;
            border-radius: 4px;
            padding: 5px;
            color: {COLOR_TEXT};
        }}
    """

class DisplayController:
    @staticmethod
    def get_connected_displays():
        """Returns a list of connected display names (e.g., eDP-1)."""
        displays = []
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if ' connected' in line:
                    parts = line.split()
                    displays.append(parts[0])
        except Exception as e:
            print(f"Error checking displays: {e}")
        return displays

    @staticmethod
    def set_saturation(display, value):
        """Uses vibrant-cli to set saturation."""
        # Value is float, typically 1.0 is default.
        try:
            cmd = ['vibrant-cli', display, str(value)]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def set_gamma(display, value):
        """Uses xrandr to set gamma."""
        # Value is float, e.g., 1.0. Format for xrandr is R:G:B
        try:
            val_str = f"{value}:{value}:{value}"
            cmd = ['xrandr', '--output', display, '--gamma', val_str]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dell G15 Color Control")
        self.resize(500, 450)
        
        # Apply Theme
        self.setStyleSheet(DesignSystem.STYLESHEET)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("DISPLAY CALIBRATION")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {DesignSystem.COLOR_TEXT}; letter-spacing: 2px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Display Selector
        self.display_combo = QComboBox()
        self.refresh_displays()
        self.layout.addWidget(QLabel("Target Display:"))
        self.layout.addWidget(self.display_combo)

        # Controls Container
        controls_layout = QVBoxLayout()
        
        # Saturation Control
        self.sat_group = QGroupBox("DIGITAL VIBRANCE (Saturation)")
        sat_layout = QVBoxLayout()
        
        self.sat_slider = QSlider(Qt.Orientation.Horizontal)
        self.sat_slider.setRange(0, 400) # 0.0 to 4.0
        self.sat_slider.setValue(100)    # Default 1.0
        self.sat_slider.valueChanged.connect(self.sync_sat_spin)
        
        self.sat_spin = QDoubleSpinBox()
        self.sat_spin.setRange(0.0, 4.0)
        self.sat_spin.setSingleStep(0.1)
        self.sat_spin.setValue(1.0)
        self.sat_spin.valueChanged.connect(self.sync_sat_slider)
        
        h_sat = QHBoxLayout()
        h_sat.addWidget(self.sat_slider)
        h_sat.addWidget(self.sat_spin)
        sat_layout.addLayout(h_sat)
        self.sat_group.setLayout(sat_layout)
        controls_layout.addWidget(self.sat_group)

        # Gamma Control
        self.gamma_group = QGroupBox("CONTRAST (Gamma)")
        gamma_layout = QVBoxLayout()
        
        self.gamma_slider = QSlider(Qt.Orientation.Horizontal)
        self.gamma_slider.setRange(10, 300) # 0.1 to 3.0
        self.gamma_slider.setValue(100)     # Default 1.0
        self.gamma_slider.valueChanged.connect(self.sync_gamma_spin)
        
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 3.0)
        self.gamma_spin.setSingleStep(0.05)
        self.gamma_spin.setValue(1.0)
        self.gamma_spin.valueChanged.connect(self.sync_gamma_slider)
        
        h_gamma = QHBoxLayout()
        h_gamma.addWidget(self.gamma_slider)
        h_gamma.addWidget(self.gamma_spin)
        gamma_layout.addLayout(h_gamma)
        self.gamma_group.setLayout(gamma_layout)
        controls_layout.addWidget(self.gamma_group)
        
        self.layout.addLayout(controls_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton("RESET DEFAULTS")
        self.btn_reset.setStyleSheet(f"background-color: #333; color: {DesignSystem.COLOR_TEXT};")
        self.btn_reset.clicked.connect(self.reset_defaults)
        
        self.btn_apply = QPushButton("APPLY SETTINGS")
        self.btn_apply.setStyleSheet(f"background-color: {DesignSystem.COLOR_SUCCESS}; color: white;")
        self.btn_apply.clicked.connect(self.apply_settings)
        
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_apply)
        self.layout.addLayout(btn_layout)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def refresh_displays(self):
        self.display_combo.clear()
        displays = DisplayController.get_connected_displays()
        if displays:
            self.display_combo.addItems(displays)
            # Try to select eDP-1 by default
            index = self.display_combo.findText("eDP-1", Qt.MatchFlag.MatchContains)
            if index >= 0:
                self.display_combo.setCurrentIndex(index)
        else:
            self.display_combo.addItem("No displays found")

    def sync_sat_spin(self, value):
        self.sat_spin.setValue(value / 100.0)

    def sync_sat_slider(self, value):
        self.sat_slider.setValue(int(value * 100))

    def sync_gamma_spin(self, value):
        self.gamma_spin.setValue(value / 100.0)

    def sync_gamma_slider(self, value):
        self.gamma_slider.setValue(int(value * 100))

    def apply_settings(self):
        display = self.display_combo.currentText()
        if not display or display == "No displays found":
            self.status_bar.showMessage("Error: No display selected", 5000)
            return

        sat_val = self.sat_spin.value()
        gamma_val = self.gamma_spin.value()

        # Apply Saturation
        if DisplayController.set_saturation(display, sat_val):
            sat_msg = "Saturation Applied"
        else:
            sat_msg = "Saturation Failed (is vibrant-cli installed?)"

        # Apply Gamma
        if DisplayController.set_gamma(display, gamma_val):
            gamma_msg = "Gamma Applied"
        else:
            gamma_msg = "Gamma Failed"

        self.status_bar.showMessage(f"{sat_msg} | {gamma_msg}", 5000)

    def reset_defaults(self):
        self.sat_spin.setValue(1.0)
        self.gamma_spin.setValue(1.0)
        self.apply_settings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check dependencies before showing window
    # We assume helper script handled installations, but we check vibrant-cli
    import shutil
    if not shutil.which("vibrant-cli"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Dependency Missing: vibrant-cli")
        msg.setInformativeText("This tool is required for saturation control.\nPlease run the installer script again.")
        msg.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
