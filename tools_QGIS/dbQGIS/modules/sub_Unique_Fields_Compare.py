"""
v1.7
QGIS helper: List unique values of a field and compare against a pasted query list.

Usage:
 - Open QGIS Python Console or add as a script in the Processing toolbox.
 - Run this script. A small dialog will appear where you can select the active layer's field,
   paste the contents of `landuse_types.query` (or any text containing values),
   then press 'Compare'.

What it does:
 - Extracts unique values from the chosen field (strings are normalized).
 - Parses the pasted query text to find tokens inside single quotes and plain words.
 - Shows values present in the layer but missing from the query, and values present in the
   query but missing from the layer.

This script is minimal and avoids expanding scope beyond the user's request.
"""

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject
import re

print('list_unique_compare: module loaded')


print('list_unique_compare: loaded')

# guard to prevent double-show
_dialog_shown = False


def normalize(v):
    if v is None:
        return ''
    s = str(v).strip()
    # normalize spaces and lowercase for comparison
    return re.sub(r"\s+", " ", s).lower()


class UniqueCompareDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('List unique values and compare')
        self.resize(700, 480)
        layout = QtWidgets.QVBoxLayout()

        # Horizontal row: Layer name (active), refresh button, Field selector
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(QtWidgets.QLabel('Layer:'))
        self.layer_label = QtWidgets.QLabel('<no active layer>')
        hl.addWidget(self.layer_label)
        self.refresh_layer_btn = QtWidgets.QPushButton('Refresh layer')
        hl.addWidget(self.refresh_layer_btn)
        hl.addWidget(QtWidgets.QLabel('Field:'))
        self.field_combo = QtWidgets.QComboBox()
        hl.addWidget(self.field_combo)
        layout.addLayout(hl)

        layout.addWidget(QtWidgets.QLabel('Paste the contents of landuse_types.query (or any text):'))
        self.query_text = QtWidgets.QPlainTextEdit()
        layout.addWidget(self.query_text, stretch=2)

        # Prefer using b9PyQGIS fast helper when available
        self.pref_helper = QtWidgets.QCheckBox('Prefer b9PyQGIS fast helper')
        self.pref_helper.setChecked(True)
        layout.addWidget(self.pref_helper)

        btn_h = QtWidgets.QHBoxLayout()
        self.compare_btn = QtWidgets.QPushButton('Compare')
        self.compare_query_btn = QtWidgets.QPushButton('Compare query fields')
        self.list_btn = QtWidgets.QPushButton('List uniques')
        self.copy_btn = QtWidgets.QPushButton('Copy results')
        self.close_btn = QtWidgets.QPushButton('Close')
        btn_h.addWidget(QtWidgets.QLabel('Match:'))
        self.match_mode = QtWidgets.QComboBox()
        self.match_mode.addItems(['exact', 'contains', 'regex'])
        btn_h.addWidget(self.match_mode)
        btn_h.addWidget(self.list_btn)
        btn_h.addWidget(self.compare_btn)
        btn_h.addWidget(self.compare_query_btn)
        btn_h.addWidget(self.copy_btn)
        btn_h.addStretch()
        btn_h.addWidget(self.close_btn)
        layout.addLayout(btn_h)

        layout.addWidget(QtWidgets.QLabel('Results:'))
        self.results = QtWidgets.QPlainTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results, stretch=3)

        self.setLayout(layout)

        # signals
        self.compare_btn.clicked.connect(self.on_compare)
        self.list_btn.clicked.connect(self.list_unique_values)
        self.compare_query_btn.clicked.connect(self.on_compare_query)
        self.copy_btn.clicked.connect(self.on_copy)
        self.close_btn.clicked.connect(self.close)
        self.refresh_layer_btn.clicked.connect(self.populate_fields_from_active_layer)

        # populate fields from the currently active layer
        self.populate_fields_from_active_layer()

        # simple cache for unique values: {(layer_id, field): set(values)}
        self._uniq_cache = {}

    def populate_fields_from_active_layer(self):
        """Populate the field combo from the currently selected (active) layer.

        Updates the layer label with the layer name.
        """
        try:
            from qgis.utils import iface
            layer = iface.activeLayer()
        except Exception:
            layer = None

        self.field_combo.clear()
        if layer is None:
            self.layer_label.setText('<no active layer>')
            self._active_layer_id = None
            return

        self.layer_label.setText(layer.name())
        self._active_layer_id = layer.id()
        for f in layer.fields():
            self.field_combo.addItem(f.name())

    def showEvent(self, event):
        # refresh fields each time the dialog is shown so the active layer is picked up
        try:
            self.populate_fields_from_active_layer()
        except Exception:
            pass
        super().showEvent(event)

    def populate_layers(self):
        self.layer_combo.clear()
        layers = QgsProject.instance().mapLayers().values()
        for lyr in layers:
            # only vector layers have fields
            try:
                fields = lyr.fields()
            except Exception:
                continue
            self.layer_combo.addItem(lyr.name(), lyr.id())
        if self.layer_combo.count():
            self.refresh_fields()

    def refresh_fields(self):
        self.field_combo.clear()
        lid = self.layer_combo.currentData()
        if not lid:
            return
        lyr = QgsProject.instance().mapLayer(lid)
        if not lyr:
            return
        for f in lyr.fields():
            self.field_combo.addItem(f.name())

    def parse_query_values(self, text):
        """Extract values from text. Handles tokens in single quotes and bare words.

        For example: "'park', 'garden' or \"greenfield\"" -> [park, garden, greenfield]
        """
        # find single-quoted tokens
        quoted = re.findall(r"'([^']+)'", text)
        # also find double-quoted
        double_q = re.findall(r'"([^"]+)"', text)
        # and find bare words composed of letters, underscores or hyphens
        bare = re.findall(r"\b[\w-]+\b", text)
        vals = set()
        for v in quoted + double_q:
            nv = normalize(v)
            if nv:
                vals.add(nv)
        # include bare words but skip SQL keywords like IN, OR, AND, etc.
        skip = {'in', 'or', 'and', 'select', 'where', 'like', 'not'}
        for v in bare:
            lv = v.lower()
            if lv in skip:
                continue
            vals.add(normalize(v))
        return vals

    def parse_query_fields(self, text):
        """Parse query text and return a dict: field_name -> set(values)

        Looks for patterns like: "landuse" in ( 'a', 'b', 'c' )
        and extracts the quoted values inside the parentheses. Values are normalized.
        """
        fields = {}
        # regex to find FIELD in ( ... ) where FIELD may be quoted
        # allow empty parentheses as well (use * instead of +)
        pattern = re.compile(r'"?([A-Za-z0-9_]+)"?\s*in\s*\(([^)]*)\)', re.IGNORECASE)
        for m in pattern.finditer(text):
            fld = m.group(1)
            inner = m.group(2)
            vals = set()
            inner = inner.strip()
            # extract quoted tokens first
            quoted = re.findall(r"'([^']+)'", inner)
            double_q = re.findall(r'"([^"]+)"', inner)
            for v in quoted + double_q:
                nv = normalize(v)
                if nv:
                    vals.add(nv)
            # also accept bare words separated by commas
            bare = re.findall(r"\b[\w-]+\b", inner)
            skip = {'in', 'or', 'and'}
            for v in bare:
                if v.lower() in skip:
                    continue
                vals.add(normalize(v))
            fields[fld] = vals
        return fields

    def get_unique_values_for_field(self, lyr, field):
        """Return a set of normalized unique values for given layer and field.

        Tries to use b9PyQGIS.fListUniqueVals when available for speed, else falls back.
        """
        # try fast helper
        try:
            import b9PyQGIS
            try:
                res = b9PyQGIS.fListUniqueVals(lyr, field)
            except Exception:
                res = None
        except Exception:
            res = None

        if res and isinstance(res, dict) and res.get('UNIQUE_VALUES') is not None:
            unique_vals = res.get('UNIQUE_VALUES')
            if isinstance(unique_vals, str):
                if ';' in unique_vals:
                    vals_list = [v.strip() for v in unique_vals.split(';') if v.strip()]
                else:
                    vals_list = [unique_vals.strip()] if unique_vals.strip() else []
            else:
                vals_list = list(unique_vals)
            return set(normalize(v) for v in vals_list if v is not None and str(v).strip() != '')

        # fallback: iterate features
        uniq = set()
        for feat in lyr.getFeatures():
            val = feat[field]
            nv = normalize(val)
            if nv != '':
                uniq.add(nv)
        return uniq

    def on_compare_query(self):
        """Compare every field found in the pasted query against the active layer values.

        Shows only new values (present in layer but not in the query) per field.
        """
        try:
            from qgis.utils import iface
            lyr = iface.activeLayer()
        except Exception:
            lyr = None
        if lyr is None:
            QtWidgets.QMessageBox.warning(self, 'No layer', 'No active vector layer selected.')
            return

        qtext = self.query_text.toPlainText()
        parsed = self.parse_query_fields(qtext)

        if not parsed:
            QtWidgets.QMessageBox.information(self, 'No fields', 'No field IN (...) patterns found in the query text.')
            return

        results = {}
        for field, qvals in parsed.items():
            if field not in [f.name() for f in lyr.fields()]:
                # field not present in layer
                results[field] = None
                continue
            layer_vals = self.get_unique_values_for_field(lyr, field)
            new_vals = sorted(layer_vals - qvals)
            results[field] = new_vals

        # format output: show only fields with new values (and indicate missing fields)
        out_lines = ['Unique new values:']
        any_new = False
        for field, vals in results.items():
            if vals is None:
                out_lines.append(f'"{field}": (field missing in layer)')
                continue
            if vals:
                any_new = True
                quoted = ", ".join([f"'{v}'" for v in vals])
                out_lines.append(f'"{field}": {quoted}')
        if not any_new:
            out_lines.append('(none)')

        self.results.setPlainText('\n'.join(out_lines))

    def on_compare(self):
        # Use the currently active layer
        try:
            from qgis.utils import iface
            lyr = iface.activeLayer()
        except Exception:
            lyr = None

        if lyr is None:
            QtWidgets.QMessageBox.warning(self, 'No layer', 'No active vector layer selected.')
            return

        field = self.field_combo.currentText()
        if not field:
            QtWidgets.QMessageBox.warning(self, 'No field', 'Select a field to inspect.')
            return

        # collect unique values from the layer
        uniq = set()
        for feat in lyr.getFeatures():
            val = feat[field]
            norm = normalize(val)
            if norm != '':
                uniq.add(norm)

        # parse query text
        qtext = self.query_text.toPlainText()
        query_vals = self.parse_query_values(qtext)

        mode = self.match_mode.currentText()
        if mode == 'exact':
            only_in_layer = sorted(uniq - query_vals)
            only_in_query = sorted(query_vals - uniq)
            both = sorted(uniq & query_vals)
        else:
            # contains or regex: build matched sets
            matched_layer = set()
            matched_query = set()
            for lv in uniq:
                for q in query_vals:
                    try:
                        if mode == 'contains':
                            if q in lv or lv in q:
                                matched_layer.add(lv)
                                matched_query.add(q)
                        elif mode == 'regex':
                            # treat q as a regex pattern
                            if re.search(q, lv):
                                matched_layer.add(lv)
                                matched_query.add(q)
                    except re.error:
                        # invalid regex -> skip this pattern
                        continue
            only_in_layer = sorted(uniq - matched_layer)
            only_in_query = sorted(query_vals - matched_query)
            both = sorted(matched_layer)

        out_lines = []
        out_lines.append('Unique values in layer (normalized): %d' % len(uniq))
        out_lines.append('Values in query (parsed): %d' % len(query_vals))
        out_lines.append('')
        out_lines.append('Values present in layer but missing from query:')
        if only_in_layer:
            out_lines.extend(['  - ' + v for v in only_in_layer])
        else:
            out_lines.append('  (none)')
        out_lines.append('')
        out_lines.append('Values present in query but missing from layer:')
        if only_in_query:
            out_lines.extend(['  - ' + v for v in only_in_query])
        else:
            out_lines.append('  (none)')
        out_lines.append('')
        out_lines.append('Values present in both:')
        if both:
            out_lines.extend(['  - ' + v for v in both])
        else:
            out_lines.append('  (none)')

        self.results.setPlainText('\n'.join(out_lines))

    def list_unique_values(self):
        """List unique normalized values from the active layer's selected field."""
        try:
            from qgis.utils import iface
            lyr = iface.activeLayer()
        except Exception:
            lyr = None
        if lyr is None:
            QtWidgets.QMessageBox.warning(self, 'No layer', 'No active vector layer selected.')
            return
        field = self.field_combo.currentText()
        if not field:
            QtWidgets.QMessageBox.warning(self, 'No field', 'Select a field to inspect.')
            return
        import time
        started = time.time()

        # Fast path: try to use user's b9PyQGIS helper if available
        try:
            import b9PyQGIS
            try:
                res = b9PyQGIS.fListUniqueVals(lyr, field)
            except Exception:
                res = None
        except Exception:
            res = None

        if res and isinstance(res, dict) and res.get('UNIQUE_VALUES') is not None:
            # The helper returns a structure with UNIQUE_VALUES and TOTAL_VALUES keys
            unique_vals = res.get('UNIQUE_VALUES')
            # If the helper returned a semicolon-separated string, split it into items
            if isinstance(unique_vals, str):
                if ';' in unique_vals:
                    vals_list = [v.strip() for v in unique_vals.split(';') if v.strip()]
                else:
                    vals_list = [unique_vals.strip()] if unique_vals.strip() else []
            else:
                # assume an iterable of strings
                vals_list = list(unique_vals)

            total_number = res.get('TOTAL_VALUES', len(vals_list))
            # Format like your old function: semicolon-separated
            semi = ';'.join(vals_list)
            out_lines = [f'Result for field "{field}" of layer "{lyr.name()}":', f'Number of variants: {total_number}', '', semi]
            elapsed = time.time() - started
            out_lines.append('')
            out_lines.append(f'Fast path via b9PyQGIS used (took {elapsed:.3f}s)')
            print('list_unique_compare: used b9PyQGIS.fListUniqueVals, %d uniques, %.3fs' % (len(vals_list), elapsed))
            self.results.setPlainText('\n'.join(out_lines))
            return

        # Fallback: Python iteration over features (slower)
        uniq = set()
        raw_preview = []
        count = 0
        for feat in lyr.getFeatures():
            val = feat[field]
            norm = normalize(val)
            if norm != '':
                uniq.add(norm)
            # collect a short preview of raw values
            if len(raw_preview) < 20:
                raw_preview.append(str(val))
            count += 1

        out_lines = ['Unique values in layer (normalized): %d' % len(uniq), 'Total features scanned: %d' % count, '']
        if uniq:
            out_lines.append('Preview raw values (first %d):' % len(raw_preview))
            out_lines.extend(['  - ' + v for v in raw_preview])
            out_lines.append('')
            out_lines.append('Unique normalized values:')
            out_lines.extend(['  - ' + v for v in sorted(uniq)])
        else:
            out_lines.append('  (none)')
            QtWidgets.QMessageBox.information(self, 'No values', 'No non-empty values found in field "%s"' % field)

        elapsed = time.time() - started
        out_lines.append('')
        out_lines.append(f'Fallback Python path used (took {elapsed:.3f}s)')
        print('list_unique_compare: listed %d unique values from field %s (%.3fs)' % (len(uniq), field, elapsed))
        self.results.setPlainText('\n'.join(out_lines))

    def on_copy(self):
        cb = QtWidgets.QApplication.clipboard()
        cb.setText(self.results.toPlainText())


def run_dialog():
    """Open the dialog.

    When running inside QGIS, parent to iface.mainWindow() and show non-modal so it appears
    on top of the QGIS window. If not running inside an existing QApplication, create one
    and exec_.
    """
    parent = None
    try:
        # In the QGIS Python Console the global `iface` is available
        from qgis.utils import iface
        parent = iface.mainWindow()
    except Exception:
        parent = None

    app = QtWidgets.QApplication.instance()
    global _dialog_shown
    if _dialog_shown:
        return

    if app is None:
        # Not running inside a Qt app (rare for QGIS). Create and exec a QApplication.
        app = QtWidgets.QApplication([])
        dlg = UniqueCompareDialog()
        dlg.show()
        print('list_unique_compare: dialog opened (standalone)')
        app.exec_()
        return

    # Running inside QGIS: parent to iface main window and show non-modally
    dlg = UniqueCompareDialog(parent)
    # Make the dialog a top-level window so raise()/activateWindow() works reliably
    try:
        dlg.setWindowFlags(dlg.windowFlags() | QtCore.Qt.Window)
    except Exception:
        # If Qt flags are not available for some reason, ignore
        pass
    dlg.setWindowModality(QtCore.Qt.NonModal)
    dlg.show()
    try:
        dlg.raise_()
        dlg.activateWindow()
    except Exception:
        pass
    print('list_unique_compare: dialog opened (QGIS)')
    _dialog_shown = True



if __name__ == '__main__':
    run_dialog()

