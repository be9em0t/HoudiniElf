"""sub_Z_Order.py
v0.2

Overlap-based Z-Order compression for polygon layers in QGIS.

What it does
- Computes an `area` field (if missing) using feature geometry area()
- Computes a compressed `z_order` integer for each feature based on overlaps.
  The algorithm (default) sorts features by area ascending and then assigns
  z_order as max(z_order_of_overlapping_already_processed_features) + 1.

Notes
- Run this from the QGIS Python console or as a processing script where `iface`
  is available. It edits the active layer. Backup your data before running.
- There is an `invert_z` option: if True, the final z_order values are inverted
  so that smaller areas end up with larger z values (useful if your renderer
  treats higher z as 'on top').

Usage (in QGIS Python console):
>>> from sub_Z_Order import compute_z_order_for_active_layer
>>> compute_z_order_for_active_layer(invert_z=False)

This script keeps changes minimal and uses layer editing mode. It attempts to
be robust to missing fields and non-polygon layers.
"""

import os, sys
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# print("Current script's directory:", current_script_dir)
sys.path.append(os.path.dirname(current_script_dir))
import imp


import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *


from typing import Dict, List

from qgis.core import (
	QgsProject,
	QgsFeature,
	QgsSpatialIndex,
	QgsGeometry,
	QgsField,
	QgsWkbTypes,
	QgsFeatureRequest,
)
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

# Try to import the b9PyQGIS wrapper helpers if available in the PYTHONPATH.
# These wrap native processing algorithms and are usually faster. If not
# available, we'll fall back to direct PyQGIS calls.
try:
	from tools_QGIS import b9PyQGIS as b9helpers
except Exception:
	try:
		import b9PyQGIS as b9helpers
	except Exception:
		b9helpers = None


def compute_z_order_for_active_layer(invert_z: bool = False, commit: bool = True) -> Dict[int, int]:
	"""Compute compressed overlap-based z_order for the active layer.

	Args:
		invert_z: If True, invert the computed z values so that smaller areas
				  receive larger z numbers (useful if renderer expects higher
				  z to be drawn on top).
		commit: If False, do not commit edits (useful for testing).

	Returns:
		Mapping of feature id -> z_order assigned.
	"""

	layer = iface.activeLayer()
	if layer is None:
		raise ValueError("No active layer. Please select a polygon layer.")

	# Print (and messagebar) the layer name so user knows which layer is used
	layer_name = layer.name()
	print(f"Processing layer: {layer_name}")
	try:
		iface.messageBar().pushMessage("sub_Z_Order", f"Processing layer: {layer_name}", level=0, duration=3)
	except Exception:
		# messageBar might not be available in some headless contexts
		pass

	geom_type = QgsWkbTypes.flatType(layer.wkbType())
	if geom_type not in (QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon):
		raise ValueError("Layer is not polygonal. This script works on polygon layers.")

	# Ensure fields exist: 'area' (double) and 'z_order' (int).
	# Prefer using b9helpers if available for field addition (wraps native algorithms).
	area_idx = layer.fields().indexOf('area')
	z_idx = layer.fields().indexOf('z_order')
	if (area_idx == -1 or z_idx == -1) and b9helpers is not None:
		# use wrapper to add missing fields quickly
		if area_idx == -1:
			b9helpers.fFieldCalc(layer, 'area', 'area($geometry)', 2, -1, 6)
		if z_idx == -1:
			# add integer field via processing wrapper
			b9helpers.fAddField(layer, 'z_order')

	# If still missing (or b9helpers unavailable), create them directly
	to_add = []
	area_idx = layer.fields().indexOf('area')
	z_idx = layer.fields().indexOf('z_order')
	if area_idx == -1:
		to_add.append(QgsField('area', QVariant.Double))
	if z_idx == -1:
		to_add.append(QgsField('z_order', QVariant.Int))
	if to_add:
		layer.startEditing()
		layer.dataProvider().addAttributes(to_add)
		layer.updateFields()

	# recompute indexes
	area_idx = layer.fields().indexOf('area')
	z_idx = layer.fields().indexOf('z_order')

	# Build feature cache and spatial index
	features: List[QgsFeature] = list(layer.getFeatures())
	feat_map: Dict[int, QgsFeature] = {f.id(): f for f in features}

	index = QgsSpatialIndex()
	for f in features:
		index.insertFeature(f)

	# Compute area values and prepare a list sorted by area ascending
	areas: Dict[int, float] = {}
	for f in features:
		try:
			a = f.geometry().area()
		except Exception:
			a = 0.0
		areas[f.id()] = a

	# Sort feature ids by area ascending (smallest first)
	sorted_fids = sorted(areas.keys(), key=lambda fid: (areas[fid], fid))

	z_order: Dict[int, int] = {}

	# Iterate through features from smallest to largest and assign compressed z
	for fid in sorted_fids:
		f = feat_map[fid]
		geom = f.geometry()
		if geom is None or geom.isEmpty():
			z_order[fid] = 0
			continue

		# find candidate overlapping feature ids by bbox
		bbox_ids = index.intersects(geom.boundingBox())

		max_z = 0
		for oid in bbox_ids:
			if oid == fid:
				continue
			# only consider overlaps with features that already have a z assigned
			if oid not in z_order:
				continue
			other = feat_map.get(oid)
			if other is None:
				continue
			try:
				# precise geometry intersection test
				if geom.intersects(other.geometry()):
					max_z = max(max_z, z_order.get(oid, 0))
			except Exception:
				# if intersection test fails, skip
				continue

		z_order[fid] = max_z + 1

	# Optionally invert z so that smaller areas get larger numbers
	if invert_z:
		max_assigned = max(z_order.values()) if z_order else 0
		for fid in list(z_order.keys()):
			z_order[fid] = max_assigned - z_order[fid] + 1

	# Write area and z_order back to the layer. If b9helpers exist we used
	# processing-based functions earlier to add fields; attribute writes are
	# done here in bulk via the data provider for speed.
	layer.startEditing()
	attr_updates: Dict[int, Dict[int, object]] = {}
	for fid, f in feat_map.items():
		vals: Dict[int, object] = {}
		vals[area_idx] = areas.get(fid, 0.0)
		vals[z_idx] = int(z_order.get(fid, 0))
		attr_updates[fid] = vals
	layer.dataProvider().changeAttributeValues(attr_updates)
	if commit:
		layer.commitChanges()

	# Inform user via QGIS message bar
	iface.messageBar().pushMessage(
		"sub_Z_Order",
		f"Assigned z_order to {len(z_order)} features (invert_z={invert_z}).",
		level=0,
		duration=5,
	)

	return z_order


# Important: this module is intended to be imported and called from the
# QGIS Python console. Avoid executing the function automatically when the
# file is exec()'d. To run in the console use:
#
# from tools_QGIS.sub_Z_Order import compute_z_order_for_active_layer
compute_z_order_for_active_layer(invert_z=False)

