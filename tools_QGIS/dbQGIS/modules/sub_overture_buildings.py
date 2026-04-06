#!/usr/bin/env python3
"""
Download Overture buildings for a rectangular extent.

This module is intentionally lightweight:
- no direct cloud SDK usage
- calls external `overturemaps` CLI
- suitable to be called from QGIS scripts (Python 3.9) while using an
  external Python/runtime that has Overture tooling installed.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


def wkt_polygon_to_bbox(wkt_polygon: str) -> Tuple[float, float, float, float]:
    """
    Convert a WKT POLYGON string to bbox tuple: (west, south, east, north).
    Expects a rectangular polygon but works for generic polygon extents too.
    """
    if not wkt_polygon or "POLYGON" not in wkt_polygon.upper():
        raise ValueError("Expected WKT POLYGON string.")

    # Extract all numeric tokens and pair them as x/y.
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", wkt_polygon)
    if len(nums) < 8 or len(nums) % 2 != 0:
        raise ValueError("Could not parse polygon coordinates from WKT.")

    coords = []
    for i in range(0, len(nums), 2):
        x = float(nums[i])
        y = float(nums[i + 1])
        coords.append((x, y))

    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    west, east = min(xs), max(xs)
    south, north = min(ys), max(ys)
    return west, south, east, north


def bbox_to_str(bbox: Sequence[float]) -> str:
    west, south, east, north = bbox
    return f"{west},{south},{east},{north}"


def _default_output_path(base_dir: Optional[str], output_format: str) -> str:
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ".parquet" if output_format == "geoparquet" else ".geojson"
    filename = f"overture_buildings_{ts}{suffix}"
    if base_dir:
        return str(Path(base_dir) / filename)
    return str(Path.cwd() / filename)


def _command_candidates(python_exe: Optional[str]) -> List[List[str]]:
    candidates: List[List[str]] = [
        ["overturemaps"],
        ["uvx", "overturemaps"],
    ]
    if python_exe:
        candidates.append([python_exe, "-m", "overturemaps"])
    else:
        candidates.append(["python3", "-m", "overturemaps"])
    return candidates


def _run_cmd(cmd: Sequence[str], timeout_sec: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )


def download_overture_buildings_from_wkt(
    wkt_polygon: str,
    output_path: Optional[str] = None,
    output_format: str = "geoparquet",
    overture_type: str = "building",
    base_dir: Optional[str] = None,
    python_exe: Optional[str] = None,
    timeout_sec: int = 3600,
) -> dict:
    """
    Download Overture data for a WKT polygon extent via overturemaps CLI.

    Returns a dict with keys:
    - ok: bool
    - output_path: str
    - bbox: str
    - command: str
    - stdout: str
    - stderr: str
    - error: str (when failed)
    """
    output_format = output_format.lower().strip()
    if output_format not in ("geoparquet", "geojson"):
        raise ValueError("output_format must be 'geoparquet' or 'geojson'.")

    bbox = wkt_polygon_to_bbox(wkt_polygon)
    bbox_str = bbox_to_str(bbox)

    if not output_path:
        output_path = _default_output_path(base_dir=base_dir, output_format=output_format)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    last_error = ""
    last_stdout = ""
    last_stderr = ""

    for base_cmd in _command_candidates(python_exe):
        cmd = list(base_cmd) + [
            "download",
            f"--bbox={bbox_str}",
            "--type",
            overture_type,
            "-f",
            output_format,
            "-o",
            str(out),
        ]

        try:
            res = _run_cmd(cmd, timeout_sec=timeout_sec)
        except FileNotFoundError:
            last_error = f"Command not found: {' '.join(base_cmd)}"
            continue
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "output_path": str(out),
                "bbox": bbox_str,
                "command": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "error": f"Timed out after {timeout_sec} seconds.",
            }

        last_stdout = (res.stdout or "").strip()
        last_stderr = (res.stderr or "").strip()

        if res.returncode == 0 and out.exists():
            return {
                "ok": True,
                "output_path": str(out),
                "bbox": bbox_str,
                "command": " ".join(cmd),
                "stdout": last_stdout,
                "stderr": last_stderr,
                "error": "",
            }

        last_error = (
            f"Command failed ({res.returncode}): {' '.join(cmd)}\n"
            f"{last_stderr or last_stdout or 'No output'}"
        )

    return {
        "ok": False,
        "output_path": str(out),
        "bbox": bbox_str,
        "command": "",
        "stdout": last_stdout,
        "stderr": last_stderr,
        "error": last_error or "No runnable overturemaps command found.",
    }


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download Overture buildings for bbox or WKT extent.")
    p.add_argument("--wkt", help="WKT POLYGON extent.")
    p.add_argument("--bbox", help="west,south,east,north bbox.")
    p.add_argument("-o", "--output", help="Output file path.")
    p.add_argument(
        "-f",
        "--format",
        default="geoparquet",
        choices=["geoparquet", "geojson"],
        help="Output format.",
    )
    p.add_argument("--type", default="building", help="Overture feature type.")
    p.add_argument("--base-dir", help="Base directory for default output path.")
    p.add_argument("--python-exe", help="External python executable for 'python -m overturemaps'.")
    p.add_argument("--timeout", type=int, default=3600, help="Timeout seconds.")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)

    if not args.wkt and not args.bbox:
        print("Error: provide --wkt or --bbox.")
        return 2

    if args.wkt:
        wkt = args.wkt
    else:
        parts = [p.strip() for p in args.bbox.split(",")]
        if len(parts) != 4:
            print("Error: --bbox must be west,south,east,north.")
            return 2
        west, south, east, north = [float(v) for v in parts]
        wkt = (
            "POLYGON(("
            f"{west} {south}, {west} {north}, {east} {north}, "
            f"{east} {south}, {west} {south}"
            "))"
        )

    result = download_overture_buildings_from_wkt(
        wkt_polygon=wkt,
        output_path=args.output,
        output_format=args.format,
        overture_type=args.type,
        base_dir=args.base_dir,
        python_exe=args.python_exe,
        timeout_sec=args.timeout,
    )

    if result["ok"]:
        print(f"Downloaded Overture data to: {result['output_path']}")
        print(f"BBOX: {result['bbox']}")
        print(f"Command: {result['command']}")
        return 0

    print("Overture download failed.")
    if result.get("error"):
        print(result["error"])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
