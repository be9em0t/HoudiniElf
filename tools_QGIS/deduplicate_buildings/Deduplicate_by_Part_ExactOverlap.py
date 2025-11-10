# delete polygons where `part` is NULL/False and overlap a polygon where `part` is True
# v2

# Run in QGIS Python Console
from qgis.core import QgsWkbTypes, QgsVectorDataProvider

def _is_part_true(val):
    """Return True if the `part` field value should be considered True.

    Accepts booleans, ints and common string representations.
    """
    if val is True:
        return True
    if val is None:
        return False
    try:
        # handle numeric 1/0
        if isinstance(val, (int, float)):
            return int(val) == 1
    except Exception:
        pass
    s = str(val).strip().lower()
    return s in ("1", "true", "t", "yes", "y")


def remove_part_overlap_duplicates_by_geometry(layer, part_field='part', overlap_mode='geom', area_threshold=0.0):
    """Remove polygon features where `part` is NULL/False and whose geometry overlaps a
    polygon feature where `part` is True.

    Parameters
    - layer: QgsVectorLayer
    - part_field: name of the attribute marking "part" (default 'part')
    - overlap_mode: one of
        * 'exact'    - identical geometry (WKB equality)
        * 'geom'     - true geometric overlap: intersection area > 0 and not just touching (default)
        * 'area_pct' - overlap if intersection area / false_feature_area >= area_threshold
    - area_threshold: used only when overlap_mode == 'area_pct'; a fraction in [0,1]

    Notes
    - `geom` mode excludes "touching" (boundaries touching but interiors not overlapping).
    - `area_pct` compares intersection area to the false/NULL feature's area (useful to
      ignore very small overlaps).
    """
    if layer is None:
        print("No layer provided")
        return
    if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        print("Layer is not a polygon layer")
        return

    # Build lists of true and false features (id, geom, area, bbox)
    true_feats = []
    false_feats = []
    ffields = layer.fields().names()
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        val = feat[part_field] if part_field in ffields else None
        try:
            area = geom.area()
        except Exception:
            area = 0.0
        bbox = geom.boundingBox()
        if _is_part_true(val):
            true_feats.append((feat.id(), geom, area, bbox))
        else:
            false_feats.append((feat.id(), geom, area, bbox))

    duplicates = []
    # Choose overlap test based on mode
    for fid, fgeom, farea, fbbox in false_feats:
        found = False
        for tid, tgeom, tarea, tbbox in true_feats:
            # quick bbox reject
            if not fbbox.intersects(tbbox):
                continue

            if overlap_mode == 'exact':
                # compare WKBs (fast)
                if fgeom.asWkb() == tgeom.asWkb():
                    found = True
            else:
                # exclude pure touching
                try:
                    if fgeom.touches(tgeom):
                        # touches -> not an overlap
                        continue
                except Exception:
                    pass

                # compute intersection area
                try:
                    inter = fgeom.intersection(tgeom)
                    inter_area = inter.area() if inter is not None and not inter.isEmpty() else 0.0
                except Exception:
                    inter_area = 0.0

                if overlap_mode == 'geom':
                    if inter_area > 0.0:
                        found = True
                elif overlap_mode == 'area_pct':
                    # protect division by zero
                    if farea > 0 and (inter_area / farea) >= float(area_threshold):
                        found = True
                else:
                    raise ValueError(f"Unknown overlap_mode: {overlap_mode}")

            if found:
                duplicates.append(fid)
                break

    if not duplicates:
        print("No part-overlap duplicates found (identical geometry)")
        return

    print(f"Found {len(duplicates)} features with part NULL/False overlapping a part=True feature (ids up to 20): {duplicates[:20]}")

    prov = layer.dataProvider()

    # Diagnostic info
    try:
        prov_caps = prov.capabilities()
    except Exception:
        prov_caps = None
    print("Provider name:", getattr(prov, 'name', lambda: '<unknown>')())
    try:
        print("Provider dataSourceUri:", prov.dataSourceUri())
    except Exception:
        print("Provider dataSourceUri: <unavailable>")
    print("Provider capabilities (int):", prov_caps)
    if prov_caps is not None:
        can_delete = bool(prov_caps & QgsVectorDataProvider.DeleteFeatures)
        print("Provider supports DeleteFeatures:", can_delete)
    print("Layer isEditable():", layer.isEditable())

    # Confirm duplicate IDs still exist in layer
    existing_ids = set()
    for f in layer.getFeatures():
        existing_ids.add(f.id())
    missing = [fid for fid in duplicates if fid not in existing_ids]
    if missing:
        print("Warning: some duplicate ids were not found in the layer when attempting deletion:", missing)

    # Try bulk provider delete
    ok = False
    try:
        ok = prov.deleteFeatures(duplicates)
        print("prov.deleteFeatures returned:", ok)
    except Exception as e:
        ok = False
        print("provider.deleteFeatures() raised an exception:", e)

    if ok:
        layer.triggerRepaint()
        print(f"Deleted {len(duplicates)} duplicate features via provider")
        return

    # Try per-id provider deletion to isolate failures
    print("Attempting per-id deletion using provider.deleteFeatures([id]) to isolate failures...")
    per_failures = []
    for fid in duplicates:
        try:
            r = prov.deleteFeatures([fid])
            print(f"provider.deleteFeatures([{fid}]) -> {r}")
            if not r:
                per_failures.append(fid)
        except Exception as e:
            print(f"provider.deleteFeatures([{fid}]) raised:", e)
            per_failures.append(fid)

    if not per_failures:
        layer.triggerRepaint()
        print(f"Deleted {len(duplicates)} features via per-id provider calls")
        return

    print("Per-id provider deletions failed for ids:", per_failures)

    # Provider approach failed. Try deleting inside an edit session as a fallback.
    print("Attempting deletion inside layer edit session as fallback...")
    started_editing = False
    try:
        if not layer.isEditable():
            started_editing = layer.startEditing()
            print("Started edit session:", started_editing)
        ok2 = layer.deleteFeatures(duplicates)
        print("layer.deleteFeatures returned:", ok2)
        if ok2:
            if started_editing:
                commit_ok = layer.commitChanges()
                print("commitChanges returned:", commit_ok)
                if not commit_ok:
                    print("Deleted features but commit failed — please check and commit/rollback in QGIS")
                else:
                    print(f"Deleted {len(duplicates)} duplicate features and committed changes")
            else:
                print(f"Deleted {len(duplicates)} duplicate features (layer already in edit mode). Remember to commit changes")
            layer.triggerRepaint()
            return
        else:
            # If we started an edit session and deleteFeatures returns False, rollback to avoid partial state
            if started_editing:
                layer.rollBack()
            print("Failed to delete duplicates using layer.deleteFeatures()")
    except Exception as e:
        if started_editing:
            try:
                layer.rollBack()
            except Exception:
                pass
        print("Exception while deleting duplicates with layer.deleteFeatures():", e)

    print("Failed to delete duplicates")


# Example: use active layer
layer = iface.activeLayer()
remove_part_overlap_duplicates_by_geometry(layer, 'part')