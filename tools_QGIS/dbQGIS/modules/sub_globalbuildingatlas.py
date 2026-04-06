#!/usr/bin/env python3
"""
Download GlobalBuildingAtlas (GBA) tiles for a bbox/WKT extent.

Supported dataset flavors:
- odbl_polygon : GBA.ODbLPolygon (GeoJSON, ODbL)
- lod1_polygon : GBA.LoD1/Polygon (GeoJSON, CC BY-NC 4.0)
- lod1_json    : GBA.LoD1/LoD1 (JSON, CC BY-NC 4.0)
- all          : all three flavors above

Notes:
- Data is organized as 5°x5° tiles with names like e025_n45_e030_n40.
- Region folder is discovered automatically by probing known region paths.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

HF_RESOLVE = "https://huggingface.co/datasets"
REGIONS = ["africa", "asiaeast", "asiawest", "europe", "northamerica", "oceania", "southamerica"]

DATASETS = {
    "odbl_polygon": {
        "repo": "zhu-xlab/GBA.ODbLPolygon",
        "subdir_prefix": "",
        "ext": ".geojson",
        "license": "ODbL",
    },
    "lod1_polygon": {
        "repo": "zhu-xlab/GBA.LoD1",
        "subdir_prefix": "Polygon",
        "ext": ".geojson",
        "license": "CC BY-NC 4.0",
    },
    "lod1_json": {
        "repo": "zhu-xlab/GBA.LoD1",
        "subdir_prefix": "LoD1",
        "ext": ".json",
        "license": "CC BY-NC 4.0",
    },
}

JOIN_KEY_CANDIDATES = [
    "id",
    "fid",
    "feature_id",
    "building_id",
    "bldg_id",
    "gba_id",
    "uid",
    "uuid",
]


def wkt_polygon_to_bbox(wkt_polygon: str) -> Tuple[float, float, float, float]:
    if not wkt_polygon or "POLYGON" not in wkt_polygon.upper():
        raise ValueError("Expected WKT POLYGON string.")
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", wkt_polygon)
    if len(nums) < 8 or len(nums) % 2 != 0:
        raise ValueError("Could not parse polygon coordinates from WKT.")
    coords = []
    for i in range(0, len(nums), 2):
        coords.append((float(nums[i]), float(nums[i + 1])))
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return min(xs), min(ys), max(xs), max(ys)


def _format_lon(value: int) -> str:
    return ("e" if value >= 0 else "w") + f"{abs(value):03d}"


def _format_lat(value: int) -> str:
    return ("n" if value >= 0 else "s") + f"{abs(value):02d}"


def _bin_mins(vmin: float, vmax: float, step: int = 5) -> List[int]:
    # Half-open [vmin, vmax) with epsilon to avoid pulling an extra bin when boundary is exact.
    eps = 1e-12
    start = math.floor(vmin / step) * step
    end = math.floor((vmax - eps) / step) * step
    if end < start:
        end = start
    vals = []
    x = start
    while x <= end:
        vals.append(int(x))
        x += step
    return vals


def bbox_to_gba_tiles(bbox: Sequence[float]) -> List[str]:
    west, south, east, north = bbox
    if west >= east or south >= north:
        raise ValueError("Invalid bbox ordering. Expected west<south<... with west<east and south<north.")

    lon_mins = _bin_mins(west, east, step=5)
    lat_mins = _bin_mins(south, north, step=5)

    tiles = []
    for lon_min in lon_mins:
        lon_max = lon_min + 5
        for lat_min in lat_mins:
            lat_max = lat_min + 5
            tile = f"{_format_lon(lon_min)}_{_format_lat(lat_max)}_{_format_lon(lon_max)}_{_format_lat(lat_min)}"
            tiles.append(tile)
    return sorted(set(tiles))


def _candidate_urls(dataset_key: str, tile: str) -> List[str]:
    spec = DATASETS[dataset_key]
    repo = spec["repo"]
    prefix = spec["subdir_prefix"]
    ext = spec["ext"]

    urls = []
    for region in REGIONS:
        if prefix:
            path = f"{prefix}/{region}/{tile}{ext}"
        else:
            path = f"{region}/{tile}{ext}"
        urls.append(f"{HF_RESOLVE}/{repo}/resolve/main/{path}")
    return urls


def _url_exists(url: str, timeout_sec: int = 30) -> bool:
    # Some hosting setups do not support HEAD reliably for large/LFS-backed files.
    # Try HEAD first, then fallback to a lightweight GET if needed.
    req_head = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req_head, timeout=timeout_sec) as resp:
            return 200 <= resp.status < 400
    except Exception:
        pass

    req_get = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req_get, timeout=timeout_sec) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _download_file(url: str, out_path: Path, timeout_sec: int = 600) -> None:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp, out_path.open("wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def _resolve_existing_url(dataset_key: str, tile: str, timeout_sec: int = 30) -> Optional[str]:
    for url in _candidate_urls(dataset_key, tile):
        if _url_exists(url, timeout_sec=timeout_sec):
            return url
    return None


def _find_join_key(poly_props: Dict, attrs_props: Dict, preferred: Optional[str] = None) -> Optional[str]:
    if preferred:
        return preferred if preferred in poly_props and preferred in attrs_props else None

    for key in JOIN_KEY_CANDIDATES:
        if key in poly_props and key in attrs_props:
            return key

    # fallback: any common key with non-empty values
    common = set(poly_props.keys()).intersection(set(attrs_props.keys()))
    if common:
        return sorted(common)[0]
    return None


def _load_geojson_features(path: Path) -> List[Dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        return data.get("features", [])
    if isinstance(data, list):
        # tolerate plain feature arrays
        return data
    return []


def _geometry_bbox(geom: Dict) -> Optional[Tuple[float, float, float, float]]:
    if not geom:
        return None
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None

    def walk(v):
        if isinstance(v, (list, tuple)):
            if len(v) >= 2 and isinstance(v[0], (int, float)) and isinstance(v[1], (int, float)):
                yield (float(v[0]), float(v[1]))
            else:
                for i in v:
                    yield from walk(i)

    pts = list(walk(coords))
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_intersects(a: Sequence[float], b: Sequence[float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _load_lod1_attr_map(path: Path, join_key_hint: Optional[str]) -> Tuple[Dict[str, Dict], Optional[str]]:
    """
    Load LoD1 JSON attributes into a dict keyed by join id.
    Returns (attr_map, detected_join_key).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict] = []

    if isinstance(data, dict):
        if data.get("type") == "FeatureCollection":
            for f in data.get("features", []):
                records.append(f.get("properties", {}))
        elif "features" in data and isinstance(data["features"], list):
            for f in data["features"]:
                if isinstance(f, dict):
                    records.append(f.get("properties", f))
        elif "data" in data and isinstance(data["data"], list):
            for row in data["data"]:
                if isinstance(row, dict):
                    records.append(row)
        else:
            # maybe dict keyed by id -> attrs
            if all(isinstance(v, dict) for v in data.values()):
                for k, v in data.items():
                    row = dict(v)
                    row.setdefault("id", k)
                    records.append(row)
    elif isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                records.append(row.get("properties", row))

    if not records:
        return {}, None

    sample = records[0]
    join_key = join_key_hint if join_key_hint in sample else None
    if not join_key:
        for k in JOIN_KEY_CANDIDATES:
            if k in sample:
                join_key = k
                break
    if not join_key:
        join_key = next(iter(sample.keys()), None)
    if not join_key:
        return {}, None

    amap: Dict[str, Dict] = {}
    for row in records:
        v = row.get(join_key)
        if v is None:
            continue
        amap[str(v)] = row
    return amap, join_key


def merge_lod1_tile(
    lod1_polygon_path: Path,
    lod1_json_path: Path,
    output_geojson_path: Path,
    join_key: Optional[str] = None,
    bbox: Optional[Sequence[float]] = None,
) -> Dict:
    features = _load_geojson_features(lod1_polygon_path)
    if not features:
        return {"ok": False, "error": f"No features in {lod1_polygon_path}"}

    sample_poly_props = (features[0] or {}).get("properties", {}) or {}
    attr_map, attrs_key = _load_lod1_attr_map(lod1_json_path, join_key_hint=join_key)
    if not attr_map:
        return {"ok": False, "error": f"No attribute records in {lod1_json_path}"}

    # Determine actual join key on polygon side.
    effective_key = _find_join_key(sample_poly_props, next(iter(attr_map.values())), preferred=join_key or attrs_key)
    if not effective_key:
        return {"ok": False, "error": "Could not determine join key between polygon and LoD1 JSON."}

    merged = 0
    kept = 0
    out_features = []
    for f in features:
        geom = f.get("geometry")
        if bbox is not None:
            gb = _geometry_bbox(geom)
            if gb is None or not _bbox_intersects(gb, bbox):
                continue
        kept += 1

        props = f.setdefault("properties", {})
        rid = props.get(effective_key)
        if rid is None:
            out_features.append(f)
            continue
        attrs = attr_map.get(str(rid))
        if not attrs:
            out_features.append(f)
            continue
        for k, v in attrs.items():
            if k not in props:
                props[k] = v
        merged += 1
        out_features.append(f)

    output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": out_features}
    output_geojson_path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    return {
        "ok": True,
        "join_key": effective_key,
        "features_total": len(features),
        "features_kept_after_bbox": kept,
        "features_merged": merged,
        "output": str(output_geojson_path),
    }


def merge_odbl_with_lod1_json_tile(
    odbl_polygon_path: Path,
    lod1_json_path: Path,
    output_geojson_path: Path,
    bbox: Optional[Sequence[float]] = None,
) -> Dict:
    features = _load_geojson_features(odbl_polygon_path)
    if not features:
        return {"ok": False, "error": f"No features in {odbl_polygon_path}"}

    attr_map, _ = _load_lod1_attr_map(lod1_json_path, join_key_hint="id")
    if not attr_map:
        return {"ok": False, "error": f"No attribute records in {lod1_json_path}"}

    out_features = []
    merged = 0
    kept = 0

    for f in features:
        geom = f.get("geometry")
        if bbox is not None:
            gb = _geometry_bbox(geom)
            if gb is None or not _bbox_intersects(gb, bbox):
                continue
        kept += 1

        props = f.setdefault("properties", {})
        src = str(props.get("source", "")).strip().lower()
        bid = str(props.get("id", "")).strip()
        region = str(props.get("region", "")).strip().upper()

        candidates = []
        if src and bid and region:
            candidates.append(f"{src}{bid}{region}")
        if src and bid:
            candidates.append(f"{src}{bid}")
        if bid and region:
            candidates.append(f"osm{bid}{region}")
        if bid:
            candidates.append(bid)

        attrs = None
        for c in candidates:
            attrs = attr_map.get(c)
            if attrs:
                break

        if attrs:
            for k, v in attrs.items():
                if k not in props:
                    props[k] = v
            merged += 1

        out_features.append(f)

    output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": out_features}
    output_geojson_path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    return {
        "ok": True,
        "join_key": "source+id+region -> lod1_json key",
        "features_total": len(features),
        "features_kept_after_bbox": kept,
        "features_merged": merged,
        "output": str(output_geojson_path),
    }


def export_geojsons_to_gpkg(
    geojson_paths: Sequence[Path],
    gpkg_path: Path,
    layer_name: str = "gba_lod1_merged",
) -> Dict:
    ogr2ogr = shutil.which("ogr2ogr")
    if not ogr2ogr:
        return {"ok": False, "error": "ogr2ogr not found on PATH."}
    if not geojson_paths:
        return {"ok": False, "error": "No GeoJSON files to export."}

    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    if gpkg_path.exists():
        gpkg_path.unlink()

    first = True
    for src in geojson_paths:
        if first:
            cmd = [
                ogr2ogr,
                "-f",
                "GPKG",
                str(gpkg_path),
                str(src),
                "-nln",
                layer_name,
            ]
            first = False
        else:
            cmd = [
                ogr2ogr,
                "-f",
                "GPKG",
                str(gpkg_path),
                str(src),
                "-nln",
                layer_name,
                "-append",
                "-update",
            ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return {
                "ok": False,
                "error": f"ogr2ogr failed ({res.returncode}): {res.stderr or res.stdout}",
                "command": " ".join(cmd),
            }
    return {"ok": True, "output": str(gpkg_path), "layer_name": layer_name}


def download_gba_tiles(
    bbox: Sequence[float],
    output_dir: str,
    dataset: str = "all",
    timeout_sec: int = 600,
) -> Dict:
    if dataset == "all":
        dataset_keys = list(DATASETS.keys())
    else:
        if dataset not in DATASETS:
            raise ValueError(f"Unknown dataset '{dataset}'.")
        dataset_keys = [dataset]

    tiles = bbox_to_gba_tiles(bbox)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failures = []

    for ds in dataset_keys:
        spec = DATASETS[ds]
        ds_dir = out_dir / ds
        ds_dir.mkdir(parents=True, exist_ok=True)

        for tile in tiles:
            url = _resolve_existing_url(ds, tile, timeout_sec=min(timeout_sec, 30))
            if not url:
                failures.append({"dataset": ds, "tile": tile, "error": "Tile not found in known regions"})
                continue

            filename = Path(url).name
            out_file = ds_dir / filename
            try:
                _download_file(url, out_file, timeout_sec=timeout_sec)
                results.append(
                    {
                        "dataset": ds,
                        "license": spec["license"],
                        "tile": tile,
                        "url": url,
                        "output": str(out_file),
                    }
                )
            except urllib.error.HTTPError as e:
                failures.append({"dataset": ds, "tile": tile, "url": url, "error": f"HTTP {e.code}"})
            except Exception as e:
                failures.append({"dataset": ds, "tile": tile, "url": url, "error": str(e)})

    manifest = {
        "bbox": {
            "west": bbox[0],
            "south": bbox[1],
            "east": bbox[2],
            "north": bbox[3],
        },
        "tiles": tiles,
        "dataset": dataset,
        "downloads": results,
        "failures": failures,
        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }

    manifest_path = out_dir / "gba_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    manifest["ok"] = len(results) > 0
    return manifest


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download GlobalBuildingAtlas tiles for bbox/WKT.")
    p.add_argument("--wkt", help="WKT POLYGON extent.")
    p.add_argument("--bbox", help="west,south,east,north")
    p.add_argument(
        "--dataset",
        default="all",
        choices=["all", "odbl_polygon", "lod1_polygon", "lod1_json"],
        help="Dataset flavor.",
    )
    p.add_argument("--output-dir", help="Output directory.")
    p.add_argument("--timeout", type=int, default=600, help="Download timeout per file in seconds.")
    p.add_argument("--reuse-existing", action="store_true", help="Skip downloads and reuse files already present in --output-dir.")
    p.add_argument("--merge-lod1", action="store_true", help="Merge lod1_polygon + lod1_json into merged GeoJSONs.")
    p.add_argument(
        "--merge-source",
        default="odbl",
        choices=["odbl", "lod1_polygon"],
        help="Geometry source for merge when --merge-lod1 is used.",
    )
    p.add_argument("--join-key", help="Optional join key for LoD1 merge.")
    p.add_argument("--to-gpkg", action="store_true", help="Export merged LoD1 outputs to GeoPackage.")
    p.add_argument("--layer-name", default="gba_lod1_merged", help="Layer name when exporting to GeoPackage.")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)

    if not args.wkt and not args.bbox:
        print("Error: provide --wkt or --bbox.")
        return 2

    if args.wkt:
        bbox = wkt_polygon_to_bbox(args.wkt)
    else:
        parts = [p.strip() for p in args.bbox.split(",")]
        if len(parts) != 4:
            print("Error: --bbox must be west,south,east,north")
            return 2
        bbox = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))

    if args.output_dir:
        out_dir = args.output_dir
    else:
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = str(Path.cwd() / f"globalbuildingatlas_{ts}")

    print("GlobalBuildingAtlas downloader")
    print(f"BBOX: {bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}")
    print(f"Dataset: {args.dataset}")
    print("Licenses:")
    if args.dataset in ("all", "odbl_polygon"):
        print("- odbl_polygon: ODbL")
    if args.dataset in ("all", "lod1_polygon", "lod1_json"):
        print("- lod1_polygon / lod1_json: CC BY-NC 4.0 (non-commercial)")
    print("")

    if args.reuse_existing:
        manifest_path = Path(out_dir) / "gba_manifest.json"
        if manifest_path.exists():
            result = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            result = {
                "bbox": {"west": bbox[0], "south": bbox[1], "east": bbox[2], "north": bbox[3]},
                "tiles": bbox_to_gba_tiles(bbox),
                "dataset": args.dataset,
                "downloads": [],
                "failures": [],
                "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "manifest": str(manifest_path),
                "ok": True,
            }
        result["manifest"] = str(manifest_path)
        result["ok"] = True
    else:
        result = download_gba_tiles(
            bbox=bbox,
            output_dir=out_dir,
            dataset=args.dataset,
            timeout_sec=args.timeout,
        )

    print(f"Output dir: {out_dir}")
    print(f"Manifest: {result.get('manifest')}")
    print(f"Downloaded files: {len(result.get('downloads', []))}")
    print(f"Failures: {len(result.get('failures', []))}")
    if result.get("failures"):
        print("Some tiles could not be downloaded. Check manifest for details.")

    if args.merge_lod1:
        lod1_poly_dir = Path(out_dir) / "lod1_polygon"
        odbl_poly_dir = Path(out_dir) / "odbl_polygon"
        lod1_json_dir = Path(out_dir) / "lod1_json"
        merged_dir = Path(out_dir) / "lod1_merged"
        merged_reports = []

        if not lod1_json_dir.exists():
            print("LoD1 merge skipped: missing lod1_polygon and/or lod1_json downloads.")
        else:
            if args.merge_source == "odbl":
                if not odbl_poly_dir.exists():
                    print("LoD1 merge skipped: missing odbl_polygon downloads.")
                    result["lod1_merge"] = merged_reports
                    manifest_path = Path(result["manifest"])
                    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    return 0 if result.get("ok") else 1
                polygon_files = sorted(odbl_poly_dir.glob("*.geojson"))
            else:
                if not lod1_poly_dir.exists():
                    print("LoD1 merge skipped: missing lod1_polygon downloads.")
                    result["lod1_merge"] = merged_reports
                    manifest_path = Path(result["manifest"])
                    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    return 0 if result.get("ok") else 1
                polygon_files = sorted(lod1_poly_dir.glob("*.geojson"))

            for poly_file in polygon_files:
                json_file = lod1_json_dir / (poly_file.stem + ".json")
                if not json_file.exists():
                    merged_reports.append(
                        {"ok": False, "tile": poly_file.stem, "error": f"Missing {json_file.name}"}
                    )
                    continue
                out_geojson = merged_dir / poly_file.name
                if args.merge_source == "odbl":
                    rep = merge_odbl_with_lod1_json_tile(poly_file, json_file, out_geojson, bbox=bbox)
                else:
                    rep = merge_lod1_tile(poly_file, json_file, out_geojson, join_key=args.join_key, bbox=bbox)
                rep["tile"] = poly_file.stem
                merged_reports.append(rep)

            result["lod1_merge"] = merged_reports
            ok_count = sum(1 for r in merged_reports if r.get("ok"))
            print(f"LoD1 merged tiles: {ok_count}/{len(merged_reports)}")

            if args.to_gpkg:
                merged_geojsons = [Path(r["output"]) for r in merged_reports if r.get("ok") and r.get("output")]
                gpkg_path = Path(out_dir) / "gba_lod1_merged.gpkg"
                gpkg_report = export_geojsons_to_gpkg(merged_geojsons, gpkg_path, layer_name=args.layer_name)
                result["gpkg_export"] = gpkg_report
                if gpkg_report.get("ok"):
                    print(f"GPKG created: {gpkg_report.get('output')} (layer: {gpkg_report.get('layer_name')})")
                else:
                    print(f"GPKG export failed: {gpkg_report.get('error')}")

        # Rewrite manifest with merge/export info.
        manifest_path = Path(result["manifest"])
        manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
