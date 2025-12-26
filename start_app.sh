#!/bin/bash

# Dell G15 Color Control - Installer & Launcher

APP_SCRIPT="./dell_g15_color_control.py"
DEPS_PACMAN=("python-pyqt6" "xorg-xrandr" "bc" "argyllcms" "colord")
DEPS_AUR=("vibrant-cli" "iccxml")

echo "--- Dell G15 Color Control ---"
echo "Checking dependencies..."

# Function to check and install pacman packages
install_pacman_deps() {
    for pkg in "${DEPS_PACMAN[@]}"; do
        if ! pacman -Qi "$pkg" &> /dev/null; then
            echo "Installing missing package: $pkg"
            sudo pacman -S --noconfirm "$pkg"
        else
            echo "  [OK] $pkg"
        fi
    done
}

# Function to check and install AUR packages
install_aur_deps() {
    for pkg in "${DEPS_AUR[@]}"; do
        if ! pacman -Qi "$pkg" &> /dev/null; then
            echo "Installing missing AUR package: $pkg"
            if command -v yay &> /dev/null; then
                yay -S --noconfirm "$pkg"
            elif command -v paru &> /dev/null; then
                paru -S --noconfirm "$pkg"
            else
                echo "Error: Neither 'yay' nor 'paru' found. Cannot install $pkg."
            fi
        else
            echo "  [OK] $pkg"
        fi
    done
}

# Run Checks
install_pacman_deps
install_aur_deps

# Launch App
echo "Dependencies checked. Launching Application..."
if [ -f "$APP_SCRIPT" ]; then
    chmod +x "$APP_SCRIPT"
    python3 "$APP_SCRIPT"
else
    echo "Error: $APP_SCRIPT not found!"
fi
