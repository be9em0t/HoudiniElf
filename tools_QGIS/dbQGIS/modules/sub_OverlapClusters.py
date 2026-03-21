# Cluster polygons by overlap
# Do some preprocesing (fix geometries)

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
# from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QApplication, QLabel,QMessageBox)

# manually append script folder 'cause fucking QGIS
# import imp
import importlib as imp
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *
from collections import deque


def fFixGeometries(layer=None):
	if layer is None:
		layer = iface.activeLayer()
	assert layer is not None, "Select your landuse polygon layer first"
	layerBaseName = layer.name()
	# call fFixGeometries(layer) from b9PyQGIS.py
	print("Fix Geometries...")
	result = b9PyQGIS.fFixGeometries(layer.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerBaseName + '_FixGeom')
	# Optionally remove original layer or leave it as-is. Caller decides.
	print("Fixed layer")
	return newLayer


def fOverlapClusters(layer=None):
    """Cluster polygon features by overlap."""
    if layer is None:
        layer = iface.activeLayer()

    assert layer is not None, "Select your landuse polygon layer first"

    # Step 0: fix layer geometries
    layer = fFixGeometries(layer)

    # Step 1: discover connected overlap clusters and assign each a stable ID.
    # Create a field to store the cluster ID (only >1-member clusters get an ID; singles get -1).
    cluster_field = "cluster_id"
    if cluster_field not in [f.name() for f in layer.fields()]:
        layer.dataProvider().addAttributes([QgsField(cluster_field, QVariant.Int)])
        layer.updateFields()

    # Read all features once (avoid multiple provider hits)
    features = list(layer.getFeatures())

    # Build spatial index from full feature list
    index = QgsSpatialIndex()
    for f in features:
        index.addFeature(f)

    # Cache geometries, areas, and bounding boxes (to avoid recomputing)
    geoms = {f.id(): f.geometry() for f in features}
    areas = {fid: g.area() for fid, g in geoms.items()}
    bboxes = {fid: g.boundingBox() for fid, g in geoms.items()}

    # Union-Find (Disjoint Set) for overlap groups
    parent = {f.id(): f.id() for f in features}

    def find(u):
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    def union(u, v):
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[rv] = ru

    # Find overlaps (bbox + precise intersect check)
    for f in features:
        fid = f.id()
        geom = geoms[fid]
        bbox = bboxes[fid]
        candidates = index.intersects(bbox)

        # Only check candidates with higher IDs to avoid redundant work
        for c in candidates:
            if c <= fid:
                continue

            # Extra quick filter: bbox check before full geometry intersect
            if not bbox.intersects(bboxes[c]):
                continue

            # Treat as overlap only if intersection area is > 0 (touching-only doesn't count).
            # This is the most robust definition for “proper overlap”.
            inter = geom.intersection(geoms[c])
            overlaps_test = (inter is not None) and (inter.area() > 0)

            if overlaps_test:
                union(fid, c)

    # Group features by connected-component root
    groups = {}
    for fid in parent:
        root = find(fid)
        groups.setdefault(root, []).append(fid)

    # Build cluster assignment (task 1)
    # Each overlap-connected group (size > 1) gets a cluster ID.
    cluster_vals = {}
    cluster_id_by_root = {}
    cluster_counter = 0

    for root, members in groups.items():
        if len(members) <= 1:
            for fid in members:
                cluster_vals[fid] = -1
            continue

        cluster_id_by_root[root] = cluster_counter
        for fid in members:
            cluster_vals[fid] = cluster_counter
        cluster_counter += 1

    # Write back cluster_id (so you can inspect clusters in the attribute table)
    with edit(layer):
        field_idx = layer.fields().indexOf(cluster_field)
        for fid, cid in cluster_vals.items():
            layer.changeAttributeValue(fid, field_idx, cid)

    print(f"Done. Found {cluster_counter} overlap clusters; stored IDs in '{cluster_field}'.")


if __name__ == '__main__':
    fOverlapClusters()


