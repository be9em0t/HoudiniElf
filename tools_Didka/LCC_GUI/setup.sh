#!/bin/bash
# Setup script for Script Launcher GUI

echo "=============================================="
echo "Script Launcher GUI - Setup"
echo "=============================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

echo "✓ Python 3 is available"
echo ""

# Check if PyQt6 is installed
echo "Checking for PyQt6..."
python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "PyQt6 is not installed."
    echo ""
    read -p "Would you like to install PyQt6 now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing PyQt6..."
        python3 -m pip install PyQt6
        if [ $? -eq 0 ]; then
            echo "✓ PyQt6 installed successfully"
        else
            echo "❌ Failed to install PyQt6"
            exit 1
        fi
    else
        echo "Please install PyQt6 manually: pip install PyQt6"
        exit 1
    fi
else
    echo "✓ PyQt6 is already installed"
fi

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""
echo "To launch the GUI, run:"
echo "  python3 launch.py"
echo "or"
echo "  python3 lcc_GUI.py"
echo ""
echo "To add your own scripts:"
echo "  1. Create a .py file in the ./tools directory"
echo "  2. Add a build_parser() function"
echo "  3. Refresh the script list in the GUI"
echo ""
echo "See SCRIPT_TEMPLATE.md for detailed instructions."
echo ""
