#!/usr/bin/env python3
import sys
import subprocess
import re
import os
import json
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

class SettingsManager:
    CONFIG_DIR = os.path.expanduser("~/.config/dell_g15_color")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

    @classmethod
    def load_settings(cls):
        if not os.path.exists(cls.CONFIG_FILE):
             return {'saturation': 1.0, 'gamma': 1.0}
        try:
            with open(cls.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {'saturation': 1.0, 'gamma': 1.0}

    @classmethod
    def save_settings(cls, sat, gamma):
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump({'saturation': sat, 'gamma': gamma}, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

class DisplayController:
    # ... (existing class)
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

    @staticmethod
    def ensure_colord_device(display_name):
        """Ensures the display is registered in colord. Creates it if missing."""
        try:
            # Check if device exists
            res = subprocess.run(['colormgr', 'get-devices'], capture_output=True, text=True)
            if display_name in res.stdout:
                return True
            
            print(f"Device {display_name} not found in colord. Creating...")
            # Create device: create-device <id> <scope> <kind>
            # kind=display, scope=normal (persistent)
            # colormgr create-device "eDP-1" "normal" "display"
            cmd = ['colormgr', 'create-device', display_name, 'normal', 'display']
            subprocess.run(cmd, check=True)
            print(f"Device {display_name} created in colord.")
            return True
        except Exception as e:
            print(f"Error ensuring colord device: {e}")
            return False

    @staticmethod
    def apply_profile_wayland(display, saturation, gamma):
        """Uses ICC Profile modification to apply Saturation (xyY) and Gamma (TRC) on Wayland."""
        # Ensure colord knows about this device, otherwise KWin ignores the profile!
        DisplayController.ensure_colord_device(display)

        import shutil
        import xml.etree.ElementTree as ET
        
        # 1. Base Profile
        base_profile = "/usr/share/ghostscript/iccprofiles/srgb.icc"
        if not os.path.exists(base_profile):
            # Try fallback
            base_profile = "/usr/share/color/icc/sRGB.icc"
        if not os.path.exists(base_profile):
            print("Base sRGB profile not found!")
            return False, "Base sRGB profile not found"

        # 2. Check Tools
        icc_to_xml = shutil.which("iccToXml") or shutil.which("icc2xml")
        xml_to_icc = shutil.which("iccFromXml") or shutil.which("xml2icc")
        
        if not icc_to_xml or not xml_to_icc:
            print(f"iccxml tools missing. Found: To={icc_to_xml}, From={xml_to_icc}")
            return False, "iccxml tools missing"

        # 3. Paths
        import time
        temp_dir = os.path.expanduser("~/.local/share/icc")
        os.makedirs(temp_dir, exist_ok=True)
        xml_path = os.path.join(temp_dir, "temp_profile.xml")
        # Use timestamp to force KWin to see it as a new profile
        timestamp = int(time.time() * 1000)
        icc_path = os.path.join(temp_dir, f"custom_profile_{timestamp}.icc")

        try:
            # 4. Convert Base to XML
            subprocess.run([icc_to_xml, base_profile, xml_path], check=True)

            target_sat = max(0.01, float(saturation)) # Avoid 0 division
            sat_factor = 1.0 / target_sat
            
            # Gamma Logic:
            # ICC Parametric Curve Type 0 is Y = X ^ Gamma
            # If user wants Gamma 1.2 (Darker), we actually need profile gamma to be HIGHER?
            # Standard sRGB is ~2.2.
            # If we want "Higher Contrast" (Darker Mids), we increase the exponent.
            # If we want "Lower Contrast" (Washed out), we decrease the exponent.
            # Let's try: ProfileGamma = 2.2 * UserGamma
            # Or simplified: The 'Parameter' in Type 0 IS the Gamma.
            # Let's assume standard is 2.2. User control is multiplier.
            # actually usually standard sRGB gamma is ~2.2.
            # If user sets gamma=1.0 (default), we want result 2.2.
            # If user sets gamma=0.8 (brighter), we want effective gamma < 2.2? 
            # xRandr gamma works as: Output = Input ^ (1/Gamma).
            # So if user wants to brighten (Gamma < 1.0 in UI?), xrandr usually inverts.
            # Let's stick to standard Gamma formula: Out = In ^ Gamma.
            # The base profile sRGB curve is approx 2.2.
            # We will REPLACE the curve with a parametric curve of g = 2.2 / user_gamma (to match xrandr behavior usually).
            
            # Let's try standard xrandr-like logic: 
            # If user wants "1.0" (Normal). Effective Gamma 2.2.
            # If user wants "0.8" (Brighter). Effective Gamma should be lower?
            # Let's use: target_gamma_val = 2.2 / gamma
            
            target_gamma_val = 2.2 / float(gamma)

            print(f"DEBUG: Saturation={target_sat}, Gamma Input={gamma}, Calc Param={target_gamma_val:.4f}")

            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # --- SATURATION (xyY Math) ---
            
            # Helper to access XYZ dict/attribs
            def get_xyz(node_or_dict):
                if isinstance(node_or_dict, dict):
                     return float(node_or_dict['X']), float(node_or_dict['Y']), float(node_or_dict['Z'])
                return float(node_or_dict.attrib['X']), float(node_or_dict.attrib['Y']), float(node_or_dict.attrib['Z'])

            # XYY conversion helpers
            def xyz_to_xyy(X, Y, Z):
                s = X + Y + Z
                if s == 0: return 0.3127, 0.3290, Y # Fallback D65
                return X/s, Y/s, Y

            def xyy_to_xyz(x, y, Y):
                if y == 0: return 0, 0, 0
                X = (Y / y) * x
                Z = (Y / y) * (1 - x - y)
                return X, Y, Z
            
            tags_map = {}
            for param_tag in root.findall(".//XYZType"):
                sig = param_tag.find("TagSignature")
                xyz = param_tag.find("XYZNumber")
                if sig is not None and xyz is not None:
                    tags_map[sig.text] = xyz

            # White Point (D50 PCS)
            wtpt_xyz = {'X': 0.9642, 'Y': 1.0, 'Z': 0.8249}
            wx, wy, wY = get_xyz(wtpt_xyz)
            white_x, white_y, white_Y = xyz_to_xyy(wx, wy, wY)
            
            if 'rXYZ' in tags_map and 'gXYZ' in tags_map and 'bXYZ' in tags_map:
                for prim in ['rXYZ', 'gXYZ', 'bXYZ']:
                    node = tags_map[prim]
                    original_attrib = dict(node.attrib)
                    
                    old_X, old_Y, old_Z = get_xyz(node)
                    old_x, old_y, old_Y_lum = xyz_to_xyy(old_X, old_Y, old_Z)
                    
                    new_x = white_x + (old_x - white_x) * sat_factor
                    new_y = white_y + (old_y - white_y) * sat_factor
                    
                    new_X, new_Y, new_Z = xyy_to_xyz(new_x, new_y, old_Y_lum)
                    
                    node.attrib['X'] = f"{new_X:.6f}"
                    node.attrib['Y'] = f"{new_Y:.6f}"
                    node.attrib['Z'] = f"{new_Z:.6f}"
            
            # --- GAMMA (TRC Replacement) ---
            # 1. Find the Tags container
            tags_node = root.find("Tags")
            if tags_node is None:
                # Fallback if structure is flat (unlikely with iccxml)
                tags_node = root
            
            # 2. Remove existing curveType that contains TRCs
            # Note: findall returns a list, so it's safe to iterate and remove
            for curve_node in tags_node.findall("curveType"):
                sigs = [s.text for s in curve_node.findall("TagSignature")]
                if 'rTRC' in sigs or 'gTRC' in sigs or 'bTRC' in sigs:
                    print("DEBUG: Removing existing sampled TRC curve.")
                    tags_node.remove(curve_node)
            
            # 3. Create new curveType (Sampled LUT)
            # ParametricCurveType caused parsing errors with installed iccxml version.
            # Fallback to 256-point LUT (Standard sRGB style).
            # Range: 0-65535
            
            curve_node = ET.SubElement(tags_node, "curveType")
            ET.SubElement(curve_node, "TagSignature").text = "rTRC"
            ET.SubElement(curve_node, "TagSignature").text = "gTRC"
            ET.SubElement(curve_node, "TagSignature").text = "bTRC"
            
            # Calculate LUT
            # Formula: Y = X ^ (2.2 / UserGamma)
            # Standard sRGB is approx 2.2. If User Gamma=1.0, we want 2.2 results.
            exponent = 2.2 / float(gamma)
            
            lut_values = []
            for i in range(256):
                norm_x = i / 255.0
                norm_y = norm_x ** exponent
                val_int = int(norm_y * 65535.0 + 0.5)
                val_int = max(0, min(65535, val_int)) # Clamp
                lut_values.append(str(val_int))
            
            lut_str = " ".join(lut_values)
            
            ET.SubElement(curve_node, "Curve").text = lut_str
            
            print(f"DEBUG: Injected Sampled Gamma Curve (Exponent={exponent:.4f})")

            # Modify Header: Change Class from 'spac' (ColorSpace) to 'mntr' (Monitor)
            header = root.find("Header")
            if header is not None:
                device_class = header.find("ProfileDeviceClass")
                if device_class is not None:
                    device_class.text = "mntr"
            
            # update Description
            desc_tag_node = None
            for desc_type in ['textDescriptionType', 'textType', 'multiLocalizedUnicodeType']:
                for node in root.findall(f".//{desc_type}"):
                    sig = node.find("TagSignature")
                    if sig is not None and sig.text == 'desc':
                        desc_tag_node = node
                        break
                if desc_tag_node is not None: break

            if desc_tag_node is not None:
                 new_desc = f"Sat{target_sat}_Gam{gamma}_{timestamp}"
                 for text_tag in ['ASCII', 'String', 'Unicode']:
                     t_node = desc_tag_node.find(text_tag)
                     if t_node is not None:
                         t_node.text = new_desc
            
            # Helper to pretty print XML (iccxml parsing can be finicky about structure/whitespace)
            def indent(elem, level=0):
                i = "\n" + level*"  "
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + "  "
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                    for elem in elem:
                        indent(elem, level+1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                else:
                    if level and (not elem.tail or not elem.tail.strip()):
                        elem.tail = i

            # Clean and Indent
            indent(root)
            
            tree.write(xml_path, encoding='UTF-8', xml_declaration=True)

            # 6. Convert XML to ICC
            subprocess.run([xml_to_icc, xml_path, icc_path], check=True)

            # 7. Apply with kscreen-doctor to the TARGET display only
            cmd = ['kscreen-doctor', f'output.{display}.iccprofile.{icc_path}']
            subprocess.run(cmd, check=True)
            
            # 8. Cleanup Old Profiles (Keep last 5)
            try:
                files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
                         if f.startswith("custom_profile_") and f.endswith(".icc")]
                files.sort(key=os.path.getmtime) # Oldest first
                
                # If we have more than 2, delete the oldest ones
                while len(files) > 2:
                    oldest = files.pop(0)
                    try:
                        os.remove(oldest)
                        print(f"DEBUG: Cleaned up old profile: {oldest}")
                    except OSError:
                        pass
            except Exception as e:
                print(f"Cleanup Check Failed: {e}")

            return True, "Success"

        except Exception as e:
            print(f"ICC Error: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dell G15 Color Control")
        self.resize(500, 500)
        
        # Apply Theme
        self.setStyleSheet(DesignSystem.STYLESHEET)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("DISPLAY CALIBRATION")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {DesignSystem.COLOR_TEXT}; letter-spacing: 2px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Wayland Check
        is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        if is_wayland:
            warn_msg = QLabel("✓ WAYLAND DETECTED: Experimental Saturation Support Active.")
            warn_msg.setStyleSheet(f"color: white; background-color: {DesignSystem.COLOR_SUCCESS}; padding: 10px; border-radius: 4px; font-weight: bold;")
            warn_msg.setWordWrap(True)
            self.layout.addWidget(warn_msg)
            
            btn_kcm = QPushButton("OPEN SYSTEM DISPLAY SETTINGS (KDE)")
            btn_kcm.setStyleSheet(f"background-color: {DesignSystem.COLOR_ACCENT}; color: white;")
            def open_kcm():
                print("Attempting to open KDE System Settings...")
                # Try opening directly to screen settings using systemsettings first (more robust)
                cmds = [
                    ["systemsettings", "kcm_kscreen"],
                    ["systemsettings5", "kcm_kscreen"],
                    ["kcmshell6", "kcm_kscreen"], # Fallback to shell if app fails
                    ["systemsettings"] # Fallback to just opening settings main menu
                ]
                
                success = False
                for cmd in cmds:
                    try:
                        subprocess.Popen(cmd)
                        print(f"Executed: {' '.join(cmd)}")
                        success = True
                        break
                    except FileNotFoundError:
                        continue
                
                if not success:
                    QMessageBox.warning(self, "Error", "Could not find 'systemsettings' or 'kcmshell6'.\nPlease open Display Settings manually.")
            btn_kcm.clicked.connect(open_kcm)
            self.layout.addWidget(btn_kcm)

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
        
        if is_wayland:
            self.sat_group.setTitle(self.sat_group.title() + " [Experimental]")
            # self.sat_group.setEnabled(False) # Re-enabled for experimental support
            
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
        
        # Load Saved Settings
        saved_settings = SettingsManager.load_settings()
        if saved_settings:
            saved_sat = saved_settings.get('saturation', 1.0)
            saved_gamma = saved_settings.get('gamma', 1.0)
            self.sat_spin.setValue(float(saved_sat))
            self.gamma_spin.setValue(float(saved_gamma))
            print(f"DEBUG: Loaded settings: Sat={saved_sat}, Gam={saved_gamma}")

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
        
        is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        
        errors = []

        if is_wayland:
             # On Wayland, we apply BOTH Saturation and Gamma via the single ICC profile interaction
             success, msg = DisplayController.apply_profile_wayland(display, sat_val, gamma_val)
             if not success:
                 errors.append(f"Profile Error: {msg}")
        else:
             # Legacy X11/Fallback: Apply separately
             if self.sat_group.isEnabled():
                 if not DisplayController.set_saturation(display, sat_val):
                      errors.append("Saturation Failed (vibrant-cli error)")
             
             # Apply Gamma (X11 only)
             if not DisplayController.set_gamma(display, gamma_val):
                  errors.append("Gamma Failed (xrandr error)")

        if errors:
            self.status_bar.showMessage(" | ".join(errors), 5000)
            QMessageBox.critical(self, "Application Error", "\n".join(errors))
        else:
            self.status_bar.showMessage("Settings Applied Successfully", 5000)
            # Save settings on success
            SettingsManager.save_settings(sat_val, gamma_val)

    def reset_defaults(self):
        self.sat_spin.setValue(1.0)
        self.gamma_spin.setValue(1.0)
        self.apply_settings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check dependencies before showing window
    import shutil
    import os # Ensure os is imported
    if not shutil.which("vibrant-cli") and "wayland" not in os.environ.get("XDG_SESSION_TYPE", "").lower():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Dependency Missing: vibrant-cli")
        msg.setInformativeText("This tool is required for saturation control.\nPlease run the installer script again.")
        msg.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
