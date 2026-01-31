#!/usr/bin/env python3
"""Open a simple Qt6 MessageBox to confirm GUI tasks work.

Added verbose logging and a --verbose flag for easier debugging.
"""
import sys
import argparse
import logging


def main():
    parser = argparse.ArgumentParser(description="Run a simple PyQt6 message box test")
    parser.add_argument("--verbose", "-v", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    logging.info("Starting Qt direct test (verbose=%s)", args.verbose)

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
    except Exception as e:
        logging.error("PyQt6 import failed: %s", e)
        logging.info("Install with: pip install PyQt6")
        return 2

    try:
        logging.debug("Creating QApplication")
        app = QApplication([])

        logging.debug("Preparing QMessageBox")
        msg = QMessageBox()
        msg.setWindowTitle("CoRunner Test")
        msg.setText("CoRunner: Hello from PyQt6 test_qt.py")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        logging.info("Showing message box...")
        ret = msg.exec()
        logging.info("Message box returned: %s", ret)

        logging.debug("Exiting application")
        return 0

    except Exception as e:
        logging.exception("Unexpected error during Qt test: %s", e)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
