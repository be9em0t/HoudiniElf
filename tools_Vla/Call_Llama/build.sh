#!/bin/bash
# Build script for Ollama Chat (macOS/Linux)

set -e  # Exit on error

echo "======================================"
echo "Ollama Chat - Build Script (macOS/Linux)"
echo "======================================"
echo ""

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Check if icon exists
if [ ! -f "callama512.png" ]; then
    echo "WARNING: callama512.png not found. Building without icon."
    ICON_ARG=""
else
    ICON_ARG="--icon=callama512.png"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Build the application
echo ""
echo "Building application..."
pyinstaller \
    --name="Ollama Chat" \
    --windowed \
    $ICON_ARG \
    --add-data="callama512.png:." \
    --onefile \
    --noconfirm \
    call_lama.py

echo ""
echo "======================================"
echo "Build complete!"
echo "======================================"
echo ""

if [ "$(uname)" == "Darwin" ]; then
    # macOS
    echo "Application created: dist/Ollama Chat.app"
    echo ""
    echo "To run: open 'dist/Ollama Chat.app'"
    echo "To distribute: Share the entire 'Ollama Chat.app' bundle"
else
    # Linux
    echo "Application created: dist/Ollama Chat"
    echo ""
    echo "To run: ./dist/Ollama\ Chat"
    echo "To distribute: Share the 'Ollama Chat' executable"
fi

echo ""
echo "NOTE: Settings will be saved in callama.ini next to the executable"
echo "======================================"
