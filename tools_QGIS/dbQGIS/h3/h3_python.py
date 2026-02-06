# pip install h3
"""
Short usage:
  python tools_QGIS/h3_python.py --wkt '<POLYGON(...)>' --targets 0,3,4,5,6,7,8 --k-ring 1
Default outputs:
  - bbox_h3_expanded.csv  (CSV with columns h3,h3_resolution)
  - bbox_h3_values.txt    (SQL VALUES lines ready to paste)
Optional:
  --cte-out PATH          write a full CTE snippet
  --print-cte             print CTE to stdout
"""
import h3 as h3lib
import pandas as pd
import os

# Backwards-compatible search for polyfill and k_ring across h3 versions
import importlib, pkgutil, inspect

def _search_for_functions():
    """Search top-level and submodules for likely polyfill and k_ring callables.
    Returns tuple (polyfill_fn, polyfill_name, k_ring_fn, k_ring_name, candidates_dict)
    """
    candidates = {'polyfill': [], 'k_ring': []}

    # First try common known paths
    known_polyfill = ['polyfill', 'h3.polyfill', 'api.basic_str.polyfill', 'api.basic.polyfill', 'grid_polyfill', 'grid_polyfill_geojson']
    known_kring = ['k_ring', 'kRing', 'h3.k_ring', 'api.basic_str.k_ring', 'api.basic.k_ring', 'grid_disk', 'kring']

    def try_paths(paths):
        for path in paths:
            parts = path.split('.')
            obj = h3lib
            try:
                for p in parts:
                    obj = getattr(obj, p)
                if callable(obj):
                    return obj, path
            except Exception:
                continue
        return None, None

    poly_fn, poly_name = try_paths(known_polyfill)
    kfn, kname = try_paths(known_kring)

    # If not found, recursively search submodules for attributes with matching name fragments
    if poly_fn is None or kfn is None:
        # Ensure we can iterate package path
        pkg_path = getattr(h3lib, '__path__', None)
        if pkg_path:
            for finder, modname, ispkg in pkgutil.walk_packages(pkg_path, prefix=h3lib.__name__ + "."):
                try:
                    mod = importlib.import_module(modname)
                except Exception:
                    continue
                for attr in dir(mod):
                    low = attr.lower()
                    try:
                        obj = getattr(mod, attr)
                    except Exception:
                        continue
                    if callable(obj):
                        if 'polyfill' in low or 'poly' in low and 'fill' in low:
                            candidates['polyfill'].append((obj, f"{modname}.{attr}"))
                        if ('k_ring' in low) or ('kring' in low) or ('grid_disk' in low) or ('disk' in low and 'grid' in low):
                            candidates['k_ring'].append((obj, f"{modname}.{attr}"))
        # pick first candidate if not found earlier
        if poly_fn is None and candidates['polyfill']:
            poly_fn, poly_name = candidates['polyfill'][0]
        if kfn is None and candidates['k_ring']:
            kfn, kname = candidates['k_ring'][0]

    return poly_fn, poly_name, kfn, kname, candidates

polyfill_fn, polyfill_name, k_ring_fn, k_ring_name, candidates = _search_for_functions()

# If polyfill/k_ring not available, enable grid-sampling fallback using geo_to_h3
FALLBACK_TO_GRID = False
if polyfill_fn is None or k_ring_fn is None:
    FALLBACK_TO_GRID = True
    print('--- H3 polyfill/k_ring NOT found; enabling grid-sampling fallback (uses geo_to_h3) ---')
    print('Detected h3 __version__ =', getattr(h3lib, '__version__', 'unknown'))
    try:
        print('h3 core version =', h3lib.h3_version())
    except Exception:
        print('h3 core version = n/a')
    print('\nTop-level attributes (selected):')
    print([n for n in dir(h3lib) if any(k in n.lower() for k in ('poly','ring','grid','disk','geo'))][:60])
    print('\nCandidate functions found while searching submodules:')
    for k, v in candidates.items():
        print(f'  {k}: {[name for (_, name) in v][:10]}')
    print('\nIf you prefer native polyfill behavior later, install h3 v3.x into a Python 3.11 environment.')

# --- Polyfill / Grid polyfill fallback ---
import math
# approximate H3 edge lengths (km) per resolution (typical values from H3 docs)
EDGE_LENGTH_KM = {
    0: 1107.712591,
    1: 418.676005,
    2: 158.244655,
    3: 59.810857,
    4: 22.606379,
    5: 8.547,
    6: 3.229,
    7: 1.222,
    8: 0.463,
    9: 0.176,
    10: 0.066,
    11: 0.025,
}

def _edge_len_meters(res):
    return EDGE_LENGTH_KM.get(res, max(EDGE_LENGTH_KM.values())) * 1000.0

# Try to use high-quality polygon-to-cells APIs if available in h3 v4
def try_polygon_to_cells(bbox_geojson, res):
    """Attempt several polygon->cells APIs exposed by different h3 versions."""
    # 1) polygon_to_cells(geojson, resolution)
    for name in ('polygon_to_cells', 'polygon_to_cells_experimental', 'geo_to_cells', 'polygon_to_cells_geojson'):
        fn = getattr(h3lib, name, None)
        if callable(fn):
            try:
                # Many variants accept the geojson polygon and resolution
                result = fn(bbox_geojson, res)
                return set(result)
            except TypeError:
                # try alternate signature: pass ring array
                try:
                    ring = bbox_geojson['coordinates'][0]
                    result = fn(ring, res)
                    return set(result)
                except Exception:
                    continue
            except Exception:
                continue
    # 2) geo_to_h3shape / geo_to_cells variations
    if hasattr(h3lib, 'geo_to_cells') and callable(h3lib.geo_to_cells):
        try:
            return set(h3lib.geo_to_cells(bbox_geojson, res))
        except Exception:
            pass
    return None


def grid_polyfill(bbox_geojson, res, step_m=None, density_factor=0.25):
    """Approximate polyfill by (a) attempting polygon_to_cells APIs, and (b) dense grid sampling.
    density_factor: fraction of edge length to use as grid step (smaller = denser).
    """
    # Try polygon-to-cells APIs first (v4 has polygon_to_cells)
    poly_res = try_polygon_to_cells(bbox_geojson, res)
    if poly_res is not None and len(poly_res) > 0:
        return poly_res

    # Fallback: grid sampling
    if step_m is None:
        step_m = max(1.0, _edge_len_meters(res) * density_factor)

    ring = bbox_geojson['coordinates'][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    # meters per degree latitude ~111320
    meters_per_deg_lat = 111320.0
    mean_lat = (min_lat + max_lat) / 2.0
    meters_per_deg_lon = 111320.0 * math.cos(math.radians(mean_lat))
    step_deg_lat = step_m / meters_per_deg_lat
    step_deg_lon = max(1e-6, step_m / meters_per_deg_lon)

    cells = set()
    # seeded points: corners, midpoints, center
    corners = [(lats[i], lons[i]) for i in range(len(ring)-1)]
    corners += [((min_lat+max_lat)/2.0, min_lon), ((min_lat+max_lat)/2.0, max_lon), ((min_lat+max_lat)/2.0, (min_lon+max_lon)/2.0)]
    for lat, lon in corners:
        try:
            cells.add(h3lib.geo_to_h3(lat, lon, res))
        except Exception:
            try:
                cells.add(h3lib.latlng_to_cell(lat, lon, res))
            except Exception:
                pass

    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            try:
                cells.add(h3lib.geo_to_h3(lat, lon, res))
            except Exception:
                try:
                    cells.add(h3lib.latlng_to_cell(lat, lon, res))
                except Exception:
                    pass
            lon += step_deg_lon
        lat += step_deg_lat

    # If still small for high resolutions, densify once
    if len(cells) <= 4:
        dense_step_m = max(1.0, _edge_len_meters(res) * (density_factor/4.0))
        step_deg_lat = dense_step_m / meters_per_deg_lat
        step_deg_lon = max(1e-6, dense_step_m / meters_per_deg_lon)
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                try:
                    cells.add(h3lib.geo_to_h3(lat, lon, res))
                except Exception:
                    try:
                        cells.add(h3lib.latlng_to_cell(lat, lon, res))
                    except Exception:
                        pass
                lon += step_deg_lon
            lat += step_deg_lat

    return cells

# === CONFIG ===
# Use the explicit resolutions you provided (order doesn't matter)
# RESOLUTIONS = [7, 8, 6, 5, 3, 4, 0]
RESOLUTIONS = [12,11,10,9,8,7,6,5,4,3,2,1,0]
# How many rings to include around each base cell to avoid hex-edge misses
K_RING = 1
# Output CSV
OUT_CSV = 'bbox_h3.csv'
# Optional file with DB sample H3 ids (one per line) for quick membership check
DB_SAMPLE_FILE = 'db_sample_h3.txt'

# bbox polygon (lon,lat) ring in GeoJSON order:
bbox = {
  "type": "Polygon",
  "coordinates": [[
    [4.893364955393012, 52.377168558932276],
    [4.893364955393012, 52.37982748995461],
    [4.897906050545331, 52.37982748995461],
    [4.897906050545331, 52.377168558932276],
    [4.893364955393012, 52.377168558932276]
  ]]
}

# Print environment info to help debug version mismatches
print("Python executable:", os.sys.executable)
print("h3 package __version__:", getattr(h3lib, '__version__', 'unknown'))
print("h3 core version (h3.h3_version()):", getattr(h3lib, 'h3_version', lambda: 'n/a')())

# Helper: compute bbox diagonal (meters) using haversine
import math

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return 2.0 * R * math.asin(math.sqrt(a))

def bbox_diag_meters(bbox_geojson):
    ring = bbox_geojson['coordinates'][0]
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    return haversine_m(min_lat, min_lon, max_lat, max_lon)

# Generate cells per resolution
all_cells = []
bbox_diag_m = bbox_diag_meters(bbox)
for res in RESOLUTIONS:
    base = set()
    method = 'unknown'
    if not FALLBACK_TO_GRID and polyfill_fn is not None:
        try:
            base = set(polyfill_fn(bbox, res))
            method = 'polyfill'
        except Exception as e:
            print(f"polyfill call failed for res={res}: {e}; falling back to grid sampling")
            base = set(grid_polyfill(bbox, res))
            method = 'grid'
    else:
        base = set(grid_polyfill(bbox, res))
        method = 'grid'

    expanded = set()
    # Decide whether to apply k_ring: skip if bbox diagonal << hex edge length
    edge_len = _edge_len_meters(res)
    apply_k_ring = (k_ring_fn is not None) and (K_RING > 0) and (bbox_diag_m >= (edge_len * 0.5))

    if apply_k_ring:
        for c in base:
            try:
                expanded.update(k_ring_fn(c, K_RING))
            except Exception:
                expanded.add(c)
    else:
        expanded = base

    # Stats
    print(f"res={res}: base={len(base)} expanded={len(expanded)} (method={method}, polyfill={polyfill_name}, k_ring={k_ring_name}, apply_k_ring={apply_k_ring}, bbox_diag_m={bbox_diag_m:.1f}, edge_len_m={edge_len:.1f})")
    for c in expanded:
        all_cells.append((c, res))

# Dedupe and persist
df = pd.DataFrame(all_cells, columns=['h3','h3_resolution']).drop_duplicates().reset_index(drop=True)
df.to_csv(OUT_CSV, index=False)
print(f"Saved {OUT_CSV} with {len(df)} unique rows across {len(df['h3_resolution'].unique())} resolutions")
print(df['h3_resolution'].value_counts().sort_index())

# Per-resolution CSV outputs are suppressed by default (uncomment if needed)
# for res, g in df.groupby('h3_resolution'):
#    fn = f'bbox_h3_res_{res}.csv'
#    g.to_csv(fn, index=False)
#    print(f"  -> wrote {fn} ({len(g)} rows)")

# Quick membership test for DB sample H3 ids
if os.path.exists(DB_SAMPLE_FILE):
    sample = [l.strip() for l in open(DB_SAMPLE_FILE, 'r') if l.strip()]
    present = set(df['h3'])
    print('\nDB sample membership test:')
    for s in sample:
        print(s, 'IN_BBOX=' , s in present)

# Helpful tip for comparing to DB stored h3 values:
print('\nIf DB h3_index values are stored as integers consider checking formatting (string vs int).')
print('If values do NOT match, try installing a 3.x h3 package or create a conda env with Python 3.11 and a 3.x h3 build.')

# --- Utility: generate expanded tile set from a WKT polygon ---
import argparse

def wkt_to_geojson_polygon(wkt: str):
    """Convert a simple POLYGON WKT (single ring) to GeoJSON-like dict (lon,lat order).
    Assumes WKT like: POLYGON((lon lat, lon lat, ...))"""
    w = wkt.strip()
    if not w.upper().startswith('POLYGON'):
        raise ValueError('Only POLYGON WKT is supported')
    inner = w[w.find('((')+2:w.rfind('))')]
    pts = []
    for part in inner.split(','):
        part = part.strip()
        if not part:
            continue
        lon_str, lat_str = part.split()
        pts.append([float(lon_str), float(lat_str)])
    # ensure closed ring
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return {"type":"Polygon", "coordinates":[pts]}


def generate_expanded_tiles_from_wkt(wkt: str, target_resolutions, base_res=None, k_ring=0, density_factor=0.25):
    """Generate a deduplicated set of (h3, h3_resolution) covering the polygon.
    - base_res: resolution to polyfill (defaults to max(target_resolutions))
    - k_ring: if >0, use k_ring/grid_disk expansion around base cells when available
    - Returns a sorted list of tuples (h3, res)
    """
    geo = wkt_to_geojson_polygon(wkt)
    if base_res is None:
        base_res = max(target_resolutions)
    # 1) compute base tiles at base_res
    base_tiles = None
    try:
        base_tiles = try_polygon_to_cells(geo, base_res)
    except Exception:
        base_tiles = None
    if not base_tiles:
        print(f'polygon->cells API not available or returned empty for res={base_res}, falling back to grid sampling')
        base_tiles = grid_polyfill(geo, base_res, density_factor=density_factor)
    print(f'Base tiles at res {base_res}: {len(base_tiles)}')

    # 2) optionally expand with k_ring/grid_disk
    expanded = set()
    if k_ring > 0:
        # prefer k_ring_fn if found, else try grid_disk or grid_ring
        kfn = k_ring_fn
        for c in base_tiles:
            if kfn is not None:
                try:
                    # some APIs return list/iterable
                    neigh = kfn(c, k_ring)
                    expanded.update(neigh)
                except Exception as e:
                    # fallback to adding base cell
                    expanded.add(c)
            else:
                expanded.add(c)
    else:
        expanded = set(base_tiles)
    print(f'Expanded tiles after k_ring={k_ring}: {len(expanded)}')

    # 3) generate parents for all target resolutions (<= base_res)
    final = set()
    for c in expanded:
        # include the tile itself at base_res
        final.add((c, base_res))
        for t in target_resolutions:
            if base_res >= t:
                try:
                    p = h3lib.cell_to_parent(c, t)
                    final.add((p, t))
                except Exception:
                    # some APIs may be named differently
                    try:
                        p = h3lib.h3_to_parent(c, t)
                        final.add((p, t))
                    except Exception:
                        pass
    # dedupe and sort
    out = sorted(final, key=lambda x: (x[1], x[0]))
    return out


def write_csv(rows, out_path):
    df = pd.DataFrame(rows, columns=['h3', 'h3_resolution'])
    df.to_csv(out_path, index=False)
    print(f'Wrote {len(df)} rows to {out_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate expanded H3 tiles for a polygon WKT')
    parser.add_argument('--wkt', required=False, help='Polygon WKT string')
    parser.add_argument('--wkt-file', required=False, help='File containing WKT')
    parser.add_argument('--targets', default=None, help='Comma-separated target resolutions, e.g. 0,3,4,5,6,7,8')
    parser.add_argument('--base-res', type=int, default=None)
    parser.add_argument('--k-ring', type=int, default=1)
    parser.add_argument('--out', default='bbox_h3_expanded.csv')
    parser.add_argument('--sql-out', default='bbox_h3_values.txt', help='Path to write paste-ready SQL VALUES lines')
    parser.add_argument('--cte-out', default=None, help='Optional path to write a full SQL CTE snippet for paste')
    parser.add_argument('--print-cte', action='store_true', help='Print full CTE to stdout for quick paste')

    args = parser.parse_args()
    if args.wkt_file:
        wkt = open(args.wkt_file).read().strip()
    elif args.wkt:
        wkt = args.wkt
    else:
        # default polygon chosen by user earlier
        wkt = 'POLYGON((4.735068050022468 52.28356208446593, 4.735068050022468 52.444067788712985, 5.048224865164012 52.444067788712985, 5.048224865164012 52.28356208446593, 4.735068050022468 52.28356208446593))'

    if args.targets:
        targets = [int(x) for x in args.targets.split(',')]
    else:
        targets = [0,3,4,5,6,7,8]

    rows = generate_expanded_tiles_from_wkt(wkt, targets, base_res=args.base_res, k_ring=args.k_ring)
    write_csv(rows, args.out)

    # Also produce paste-ready SQL VALUES lines for direct insertion into your SQL CTE.
    # Writes a simple file with lines like:     ('881969c9b1fffff', 8),
    # Format VALUES lines without a trailing comma on the final line
    values_lines = []
    for i, (h, r) in enumerate(rows):
        suffix = ',' if i < (len(rows) - 1) else ''
        values_lines.append(f"        ('{h}', {r}){suffix}")

    sql_values_path = args.sql_out
    with open(sql_values_path, 'w') as vf:
        for ln in values_lines:
            vf.write(ln + '\n')
    print(f"Wrote {len(values_lines)} H3 VALUES lines to {sql_values_path}")

    # Optionally write a full CTE snippet ready to paste (if --cte-out provided)
    if args.cte_out:
        cte_path = args.cte_out
        with open(cte_path, 'w') as cf:
            cf.write('-- Inline bbox H3 cells (expanded; paste into SQL CTE)\n')
            cf.write('bbox_h3 AS (\n    SELECT * FROM (VALUES\n')
            for ln in values_lines:
                cf.write(ln + '\n')
            cf.write('    ) AS t(h3, h3_resolution)\n)\n')
        print(f"Wrote full CTE snippet to {cte_path}")

    # Optionally print to stdout for quick copy/paste
    if args.print_cte:
        print('-- Inline bbox H3 cells (expanded; paste into SQL CTE)')
        print('bbox_h3 AS (')
        print('    SELECT * FROM (VALUES')
        for ln in values_lines:
            print(ln)
        print('    ) AS t(h3, h3_resolution)')
        print(')')
