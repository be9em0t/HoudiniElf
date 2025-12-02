#!/usr/bin/env python3
"""
Quick Start Script for Script Launcher GUI

Run this to launch the GUI with instructions.
"""

import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("🚀 SCRIPT LAUNCHER GUI - Quick Start")
    print("=" * 70)
    print()
    print("This launcher provides a graphical interface for Python scripts.")
    print()
    print("📋 What you need:")
    print("  ✓ Python 3.7+")
    print("  ✓ PyQt6 (install: pip install PyQt6)")
    print()
    print("📝 To add your own scripts:")
    print("  1. Create a Python script in the ./tools directory")
    print("  2. Add a build_parser() function that returns an ArgumentParser")
    print("  3. The GUI will automatically detect and create a form for it")
    print()
    print("📖 Example scripts included:")
    print("  • simple_calculator.py - Basic arithmetic with various widget types")
    print("  • sample_text_processor.py - Comprehensive example with all features")
    print()
    print("=" * 70)
    print()
    
    # Check if PyQt6 is installed
    try:
        import PyQt6
        print("✓ PyQt6 is installed")
    except ImportError:
        print("✗ PyQt6 is NOT installed")
        print()
        install = input("Would you like to install PyQt6 now? (y/n): ")
        if install.lower() == 'y':
            print("Installing PyQt6...")
            subprocess.run([sys.executable, "-m", "pip", "install", "PyQt6"])
            print()
    
    print()
    print("Starting the launcher...")
    print("=" * 70)
    print()
    
    # Launch the GUI
    launcher_path = Path(__file__).parent / "lcc_GUI.py"
    subprocess.run([sys.executable, str(launcher_path)])

if __name__ == "__main__":
    main()
