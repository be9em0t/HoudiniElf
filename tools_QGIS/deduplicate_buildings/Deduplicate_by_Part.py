"""Deduplication utilities for QGIS (run in the QGIS Python console)

- remove_part_overlap_duplicates_by_geometry(layer, part_field='part', overlap_mode='geom',
    area_threshold=0.0, edge_tolerance=0.0, erosion_segments=5)
    * Removes features whose `part` attribute is NULL/False when they meaningfully
        overlap a feature with `part` == True.
    * overlap_mode: 'exact' (WKB equality), 'geom' (intersection area > 0 excluding
        pure touching), or 'area_pct' (intersection area fraction of the false feature).
    * edge_tolerance: when >0 the function erodes the false polygon by this amount
        (map units in a projected CRS) and requires interior overlap after erosion, which
        avoids deleting features that only touch or overlap by tiny edge artifacts.
    * For accurate area/length/buffer calculations the function transforms geometries
        in-memory to a projected CRS (project CRS if available, else UTM or EPSG:3857).

- remove_duplicate_geometries_by_orbis_id(layer, field_name='orbis_id')
    * Deletes features that share the same `orbis_id` and have identical geometry
        (exact WKB equality). Keeps the first seen feature per geometry.

Both functions use a robust deletion flow: try provider.deleteFeatures (bulk),
then per-id provider deletes for diagnostics, then a layer edit-session fallback
with commit/rollback. They print diagnostic information and do not modify layer CRS.

Usage example:
        layer = iface.activeLayer()
        remove_part_overlap_duplicates_by_geometry(layer, 'part', overlap_mode='geom', edge_tolerance=0.5)
        remove_duplicate_geometries_by_orbis_id(layer, 'orbis_id')
"""
from qgis.core import QgsWkbTypes, QgsVectorDataProvider, QgsSpatialIndex, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature

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


def remove_part_overlap_duplicates_by_geometry(layer, part_field='part', overlap_mode='geom', area_threshold=0.0, edge_tolerance=0.3, erosion_segments=5):
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

    # If layer is in geographic CRS (degrees), prepare a transform to a projected CRS
    # so area/intersection/buffer operations use linear (e.g., meter) units. We will
    # only transform geometries for calculations; the source layer is not modified.
    need_transform = False
    transform = None
    target_crs = None
    layer_crs = layer.crs()
    try:
        if layer_crs.isGeographic():
            need_transform = True
    except Exception:
        auth = layer_crs.authid() if hasattr(layer_crs, 'authid') else ''
        if '4326' in str(auth):
            need_transform = True

    if need_transform:
        proj_crs = QgsProject.instance().crs()
        try:
            if proj_crs and not proj_crs.isGeographic():
                target_crs = proj_crs
        except Exception:
            target_crs = None

        if target_crs is None:
            extent = layer.extent()
            lon = (extent.xMinimum() + extent.xMaximum()) / 2.0
            lat = (extent.yMinimum() + extent.yMaximum()) / 2.0
            try:
                zone = int((lon + 180.0) / 6.0) + 1
                if lat >= 0:
                    epsg = 32600 + zone
                else:
                    epsg = 32700 + zone
                target_crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
            except Exception:
                target_crs = QgsCoordinateReferenceSystem('EPSG:3857')

        try:
            transform = QgsCoordinateTransform(layer_crs, target_crs, QgsProject.instance().transformContext())
            print(f"Transforming geometries from {layer_crs.authid()} to {target_crs.authid()} for accurate area tests")
        except Exception as e:
            transform = None
            print("Failed to create coordinate transform for reprojection:", e)

    # Build lists of true and false features (id, feat, geom, area, bbox)
    true_feats = []
    false_feats = []
    ffields = layer.fields().names()
    for feat in layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        val = feat[part_field] if part_field in ffields else None
        # prepare a calculation geometry (transformed if necessary)
        try:
            calc_geom = geom.clone()
        except Exception:
            # fallback if clone not available
            calc_geom = geom
        if transform is not None:
            try:
                calc_geom.transform(transform)
            except Exception:
                # if transform fails, fall back to original geometry
                calc_geom = geom
        try:
            area = calc_geom.area()
        except Exception:
            area = 0.0
        bbox = calc_geom.boundingBox()
        if _is_part_true(val):
            true_feats.append((feat.id(), feat, calc_geom, area, bbox))
        else:
            false_feats.append((feat.id(), feat, calc_geom, area, bbox))

    duplicates = []
    # Build spatial index for true features to speed candidate lookup
    true_map = {tid: (feat_obj, geom, area, bbox) for tid, feat_obj, geom, area, bbox in true_feats}
    index = QgsSpatialIndex()
    for tid, feat_obj, geom, area, bbox in true_feats:
        try:
            # create a temporary feature with the transformed geometry for indexing
            tmpf = QgsFeature()
            try:
                tmpf.setGeometry(geom)
            except Exception:
                # if setGeometry fails, skip adding to index for this feature
                continue
            try:
                tmpf.setId(tid)
            except Exception:
                pass
            try:
                index.insertFeature(tmpf)
            except Exception:
                try:
                    index.addFeature(tmpf)
                except Exception:
                    # spatial index insertion failed for this feature; continue without it
                    pass
        except Exception:
            # ignore and continue
            pass

    # Choose overlap test based on mode
    for fid, feat_obj, fgeom, farea, fbbox in false_feats:
        found = False
        # candidate true feature ids by bbox
        try:
            candidate_ids = index.intersects(fbbox)
        except Exception:
            # fallback to scanning all true features if index fails
            candidate_ids = list(true_map.keys())

        for tid in candidate_ids:
            try:
                tfeat_obj, tgeom, tarea, tbbox = true_map[tid]
            except KeyError:
                continue
            # quick bbox reject (redundant but safe)
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

                # If edge_tolerance > 0, compute an eroded version of the false geometry
                inner_inter_area = None
                if edge_tolerance and edge_tolerance > 0:
                    try:
                        inner = fgeom.buffer(-float(edge_tolerance), int(erosion_segments))
                        if inner is not None and not inner.isEmpty():
                            try:
                                inner_inter = inner.intersection(tgeom)
                                inner_inter_area = inner_inter.area() if inner_inter is not None and not inner_inter.isEmpty() else 0.0
                            except Exception:
                                inner_inter_area = 0.0
                        else:
                            inner_inter_area = 0.0
                    except Exception:
                        inner_inter_area = None

                if overlap_mode == 'geom':
                    if edge_tolerance and inner_inter_area is not None:
                        # require that the eroded geometry still overlaps (avoids edge-only overlaps)
                        if inner_inter_area > 0.0:
                            found = True
                    else:
                        if inter_area > 0.0:
                            found = True
                elif overlap_mode == 'area_pct':
                    # protect division by zero
                    if edge_tolerance and inner_inter_area is not None:
                        if farea > 0 and (inner_inter_area / farea) >= float(area_threshold):
                            found = True
                    else:
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


def remove_duplicate_geometries_by_orbis_id(layer, field_name='orbis_id'):
    """Remove features that share the same `field_name` value and have identical geometry.

    Keeps the first-seen feature for each unique geometry within the same group.
    Uses the same robust deletion flow (provider -> per-id -> edit-session) and prints diagnostics.
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
        try:
            wkb = geom.asWkb()
        except Exception:
            # fallback to asWkt if asWkb fails
            try:
                wkb = geom.asWkt().encode('utf-8')
            except Exception:
                continue
        if key not in seen:
            seen[key] = set()
        if wkb in seen[key]:
            duplicates.append(feat.id())
        else:
            seen[key].add(wkb)

    if not duplicates:
        print("No duplicate geometries found by orbis_id")
        return

    print(f"Found {len(duplicates)} duplicate features (showing up to 20 ids): {duplicates[:20]}")

    prov = layer.dataProvider()
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

    # Confirm duplicate IDs still exist
    existing_ids = {f.id() for f in layer.getFeatures()}
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

    # Try per-id provider deletion
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

    # Fallback to layer edit session
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


# Example usage (commented):
# layer = iface.activeLayer()
# remove_duplicate_geometries_by_orbis_id(layer, 'orbis_id')