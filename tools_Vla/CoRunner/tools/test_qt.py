#!/usr/bin/env python3
"""Open a simple Qt6 MessageBox (moved into tools/)."""
import sys
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
except Exception as e:
    print("PyQt6 not installed or import failed:", e)
    print("Install with: pip install PyQt6")
    sys.exit(2)

app = QApplication([])
msg = QMessageBox()
msg.setWindowTitle("CoRunner Test (tools)")
msg.setText("CoRunner tools: Hello from PyQt6 test_qt.py")
msg.setStandardButtons(QMessageBox.StandardButton.Ok)
msg.exec()
sys.exit(0)
