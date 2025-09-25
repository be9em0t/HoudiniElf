"""Qt6-backed GUI for scrape_dog.

This module prefers PyQt6 and falls back to PySide6. The GUI is intentionally
minimal: it lets the user pick a capture mode, enter a URL, optional
software/version metadata and a max-results value. The Run button executes
the adapter synchronously using asyncio.run (this blocks the GUI thread but
is the simplest reliable behavior). Settings are read/written using
`scrape_dog.settings` and results are autosaved to
`scrape_dog/capture_results`.
"""
from __future__ import annotations

import sys
import json
import asyncio
from typing import Tuple


def _import_qt() -> Tuple[object, object]:
    """Return (QtWidgets, QtCore) from the available Qt6 binding.

    Preference: PyQt6, then PySide6.
    """
    try:
        from PyQt6 import QtWidgets, QtCore  # type: ignore
        return QtWidgets, QtCore
    except Exception:
        try:
            from PySide6 import QtWidgets, QtCore  # type: ignore
            return QtWidgets, QtCore
        except Exception as exc:
            raise ImportError('No Qt6 binding found (PyQt6 or PySide6 required)') from exc


def create_main_widget() -> object:
    QtWidgets, QtCore = _import_qt()

    class MainWindow(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle('scrape_dog')
            self.resize(900, 560)

            layout = QtWidgets.QVBoxLayout(self)

            title = QtWidgets.QLabel('<h2>scrape_dog — scraping GUI</h2>')
            layout.addWidget(title)

            info = QtWidgets.QLabel('Choose adapter and provide a URL to scrape.')
            layout.addWidget(info)

            form = QtWidgets.QHBoxLayout()
            self.adapter = QtWidgets.QComboBox()
            # populate adapter names from settings if available
            try:
                from . import settings

                modes = settings.get_mode_names()
            except Exception:
                modes = ['vex', 'python', 'unity_shadergraph']
            if not modes:
                modes = ['vex', 'python', 'unity_shadergraph']
            self.adapter.addItems(modes)
            form.addWidget(self.adapter)

            self.url = QtWidgets.QLineEdit()
            self.url.setPlaceholderText('https://example.com/index.html')
            form.addWidget(self.url, 1)

            self.run_btn = QtWidgets.QPushButton('Run')
            form.addWidget(self.run_btn)

            layout.addLayout(form)

            meta_row = QtWidgets.QHBoxLayout()
            self.software = QtWidgets.QLineEdit()
            self.software.setPlaceholderText('Software (e.g. Houdini)')
            self.version = QtWidgets.QLineEdit()
            self.version.setPlaceholderText('Version (e.g. 20.5)')
            self.max_results = QtWidgets.QSpinBox()
            self.max_results.setMinimum(0)
            self.max_results.setMaximum(100000)
            self.max_results.setValue(0)
            self.max_results.setToolTip('0 means no limit')
            meta_row.addWidget(self.software)
            meta_row.addWidget(self.version)
            meta_row.addWidget(QtWidgets.QLabel('Max:'))
            meta_row.addWidget(self.max_results)
            layout.addLayout(meta_row)

            self.meta_label = QtWidgets.QLabel('')
            layout.addWidget(self.meta_label)

            self.log = QtWidgets.QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

            # signals
            self.run_btn.clicked.connect(self._on_run_clicked)
            self.adapter.currentIndexChanged.connect(self._on_adapter_changed)

            # load last settings
            try:
                from . import settings

                modes = settings.get_modes()
                last = settings.get_last_mode()
                if last and last in modes:
                    idx = self.adapter.findText(last)
                    if idx >= 0:
                        self.adapter.setCurrentIndex(idx)
                # populate fields for current
                self._on_adapter_changed(self.adapter.currentIndex())
                cur = self.adapter.currentText()
                curm = modes.get(cur)
                if curm and curm.get('url'):
                    self.url.setText(curm.get('url'))
                if curm and curm.get('software'):
                    self.software.setText(curm.get('software'))
                if curm and curm.get('version'):
                    self.version.setText(curm.get('version'))
            except Exception:
                # ignore settings failures
                pass

            self._last_doc_json = None

        def _log(self, msg: str):
            try:
                self.log.append(msg)
            except Exception:
                # last-resort: ignore
                pass

        def _on_adapter_changed(self, idx: int):
            try:
                from . import settings
                modes = settings.get_modes()
                cur = self.adapter.itemText(idx)
                meta = modes.get(cur, {})
                self.meta_label.setText(f"{meta.get('software','')} {('v' + meta.get('version')) if meta.get('version') else ''}" if meta else '')
                if meta.get('software'):
                    self.software.setText(meta.get('software'))
                if meta.get('version'):
                    self.version.setText(meta.get('version'))
                if meta.get('url'):
                    self.url.setText(meta.get('url'))
            except Exception:
                # ignore
                pass

        def _on_run_clicked(self):
            adapter = self.adapter.currentText()
            url = self.url.text().strip()
            if not url:
                self._log('Please enter a URL to scrape.')
                return
            max_results = int(self.max_results.value())
            software = self.software.text().strip()
            version = self.version.text().strip()

            self._log(f'Starting adapter {adapter} for {url} (max={max_results})...')

            # persist last_mode and updated metadata to INI
            try:
                from . import settings
                settings.set_last_mode(adapter)
                settings.update_mode(adapter, url=url or None, software=software or None, version=version or None)
            except Exception:
                self._log('Failed to persist settings')

            # Run synchronously in-process (blocks UI). This matches the user's
            # explicit preference to remove async/process complexity.
            try:
                modname = self._adapter_module_for_mode(adapter)
                import importlib

                mod = importlib.import_module(f'scrape_dog.adapters.{modname}')
                func = None
                for name in dir(mod):
                    if name.startswith('run_'):
                        func = getattr(mod, name)
                        break
                if func is None:
                    raise RuntimeError(f'Adapter {modname} exposes no run_ function')
                doc = asyncio.run(func(url, max_results=max_results))
                try:
                    data = doc.model_dump() if hasattr(doc, 'model_dump') else doc
                    out = json.dumps(data, default=str, indent=2)
                except Exception:
                    out = str(doc)
                self._last_doc_json = out
                self.log.setPlainText(out)
                self._autosave_result(out)
                self._log('Run finished.')
            except Exception as exc:
                self._log(f'Run failed: {exc}')

        # Note: Save/Cancel buttons intentionally removed — synchronous run
        # design doesn't support interruption or extra UI controls here.

        def _autosave_result(self, out_str: str):
            # save to capture_results/<software>_<version>.json, sanitize
            try:
                from pathlib import Path
                import re

                root = Path(__file__).resolve().parent
                dst = root / 'capture_results'
                dst.mkdir(exist_ok=True)
                software = (self.software.text().strip() or 'result').strip()
                version = (self.version.text().strip() or 'v').strip()
                safe = lambda s: re.sub(r"[^0-9A-Za-z_-]", '_', s)
                name = f"{safe(software)}_{safe(version)}.json"
                target = dst / name
                # avoid clobbering existing file: append index if exists
                if target.exists():
                    idx = 1
                    while True:
                        t2 = dst / f"{safe(software)}_{safe(version)}_{idx}.json"
                        if not t2.exists():
                            target = t2
                            break
                        idx += 1
                target.write_text(out_str, encoding='utf8')
                self._log(f'Autosaved to {target}')
            except Exception as exc:
                self._log(f'Autosave failed: {exc}')

        def _adapter_module_for_mode(self, mode_name: str) -> str:
            mn = mode_name.lower()
            if 'vex' in mn:
                return 'vex'
            if 'python' in mn or 'pyqgis' in mn:
                return 'python'
            if 'shader' in mn or 'shadergraph' in mn:
                return 'unity_shadergraph'
            if 'node' in mn:
                return 'vex'
            return mn.split()[0]

    return MainWindow()


def run_gui() -> None:
    QtWidgets, QtCore = _import_qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    w = create_main_widget()
    w.show()
    app.exec()
