# delete polygons with equal geometry if they belong to the same orbis_id
# v3

# Run in QGIS Python Console
from qgis.core import QgsWkbTypes, QgsVectorDataProvider

def remove_duplicate_geometries_by_field(layer, field_name='orbis_id'):
    """Remove polygon features that share the same value in `field_name` and have exactly equal geometry.

    Strategy:
    1. Build a list of duplicate feature ids by comparing geometry WKBs within each group.
    2. Try to delete via the provider (`dataProvider().deleteFeatures`).
    3. If provider deletion fails, attempt deletion inside an edit session using
       `layer.deleteFeatures()` with commit/rollback handling.

    Keeps the first-seen feature for each unique geometry within the same group.
    """
    if layer is None:
        print("No layer provided")
        return
    if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        print("Layer is not a polygon layer")
        return
    idx = layer.fields().indexFromName(field_name)
    if idx == -1:
        print(f"Field '{field_name}' not found")
        return

    seen = {}  # orbis_id -> set of geometry WKBs
    duplicates = []

    for feat in layer.getFeatures():
        key = feat[field_name]
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        wkb = geom.asWkb()  # exact-geometry fingerprint (bytes)
        if key not in seen:
            seen[key] = set()
        if wkb in seen[key]:
            duplicates.append(feat.id())
        else:
            seen[key].add(wkb)

    if not duplicates:
        print("No duplicate geometries found")
        return

    print(f"Found {len(duplicates)} duplicate features (showing up to 20 ids): {duplicates[:20]})")

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
    try:
        print("Layer editing():", layer.editing())
    except Exception:
        pass

    # Confirm duplicate IDs still exist in layer
    existing_ids = set()
    for f in layer.getFeatures():
        existing_ids.add(f.id())
    missing = [fid for fid in duplicates if fid not in existing_ids]
    if missing:
        print("Warning: some duplicate ids were not found in the layer when attempting deletion:", missing)

    # Try provider.deleteFeatures first (bulk) and report result
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

    # If bulk provider deletion failed, attempt per-id deletion to get finer diagnostics
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
remove_duplicate_geometries_by_field(layer, 'orbis_id')