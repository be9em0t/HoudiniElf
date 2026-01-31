#!/usr/bin/env python3
"""Open a simple Qt6 MessageBox to confirm GUI tasks work."""
import sys
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except Exception as e:
    print("PyQt6 not installed or import failed:", e)
    print("Install with: pip install PyQt6")
    sys.exit(2)

app = QApplication([])
msg = QMessageBox()
msg.setWindowTitle("CoRunner Test")
msg.setText("CoRunner: Hello from PyQt6 test_qt.py")
msg.setStandardButtons(QMessageBox.StandardButton.Ok)
msg.exec()
sys.exit(0)
