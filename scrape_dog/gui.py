"""Minimal guarded GUI for scrape_dog.

This module tries to use an available Qt binding (PyQt6 preferred, fallback
to PySide6). Imports are performed lazily inside helper functions so importing
the package doesn't require Qt to be installed (the CLI already guards GUI
usage).

Public API:
- create_main_widget() -> QtWidgets.QWidget: returns a ready-to-show main widget
- run_gui() -> None: convenience function that creates QApplication and execs

The GUI here is intentionally small — it provides a simple launcher UI and
places to extend with adapter selection and URL input. It is sufficient to
restore the previous behavior that allowed `--gui` to open a window.
"""
from __future__ import annotations

import sys
from typing import Optional, Tuple


def _import_qt() -> Tuple[object, object]:
    """Return (QtWidgets, QtCore) from the available binding.

    Preference order: PyQt6, PySide6. Raises ImportError if neither is
    available.
    """
    try:
        from PyQt6 import QtWidgets, QtCore  # type: ignore
        return QtWidgets, QtCore
    except Exception:
        try:
            from PySide6 import QtWidgets, QtCore  # type: ignore
            return QtWidgets, QtCore
        except Exception as exc:
            raise ImportError('No Qt binding found (PyQt6 or PySide6 required)') from exc


def create_main_widget() -> object:
    """Create and return the main QWidget for the GUI.

    The returned object is the binding's QWidget instance. Callers should
    show() it and start the QApplication event loop.
    """
    QtWidgets, QtCore = _import_qt()

    class MainWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('scrape_dog')
            self.resize(800, 480)

            layout = QtWidgets.QVBoxLayout(self)

            title = QtWidgets.QLabel('<h2>scrape_dog — scraping GUI</h2>')
            layout.addWidget(title)

            info = QtWidgets.QLabel('Choose adapter and provide a URL to scrape.')
            layout.addWidget(info)

            form = QtWidgets.QHBoxLayout()
            self.adapter = QtWidgets.QComboBox()
            # Keep adapters list small; adapters live under scrape_dog.adapters
            self.adapter.addItems(['vex', 'python', 'unity_shadergraph'])
            form.addWidget(self.adapter)

            self.url = QtWidgets.QLineEdit()
            self.url.setPlaceholderText('https://example.com/index.html')
            form.addWidget(self.url)

            self.run_btn = QtWidgets.QPushButton('Run')
            form.addWidget(self.run_btn)

            layout.addLayout(form)

            self.log = QtWidgets.QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log)

            self.save_btn = QtWidgets.QPushButton('Save Last Result')
            layout.addWidget(self.save_btn)

            # simple signals (non-async) — running heavy work should be moved to
            # a background thread or use asyncio + qasync if desired.
            self.run_btn.clicked.connect(self._on_run_clicked)
            self.save_btn.clicked.connect(self._on_save_clicked)

            self._last_doc_json = None

        def _log(self, msg: str):
            self.log.append(msg)

        def _on_run_clicked(self):
            adapter = self.adapter.currentText()
            url = self.url.text().strip()
            if not url:
                self._log('Please enter a URL to scrape.')
                return
            self._log(f'Starting adapter {adapter} for {url}...')
            # For simplicity keep this synchronous: delegate to subprocess or
            # future enhancement to run asyncio tasks with qasync.
            self._log('Note: GUI run executes adapters synchronously in this simple demo.')

        def _on_save_clicked(self):
            if not self._last_doc_json:
                self._log('No last result to save.')
                return
            # default save path under capture_results/ with a stable name; the
            # GUI used to auto-save — we keep a manual save button here.
            from pathlib import Path
            out = Path(__file__).resolve().parent / 'capture_results' / 'capture.json'
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(self._last_doc_json)
            self._log(f'Saved capture to {out}')

    return MainWindow()


def run_gui() -> None:
    """Create QApplication, show the main widget, and exec the Qt loop.

    This is a convenience wrapper used by the CLI. It calls `create_main_widget`
    and runs the application. If a QApplication already exists, it will reuse
    it (useful when embedding into other apps).
    """
    QtWidgets, QtCore = _import_qt()

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    w = create_main_widget()
    w.show()
    app.exec()
