"""Merge individual pyqgis category JSON files into a single consolidated file.

Usage:
    python merge_pyqgis.py [--dir PATH] [--out FILE] [--version 3.40]

Behavior:
- Scans the given directory (default: script dir) for JSON files.
- Loads files that contain a top-level "nodes" list (category files produced by the scraper).
- Deduplicates by class name, preferring non-empty/longer descriptions and non-empty URLs.
- Collects categories per class into a list.
- Writes a single JSON with keys: "pyqgis_version", "classes" (list of objects).

This is intentionally small, robust, and fails fast on malformed files.
"""
import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime


def load_json_safe(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load {path}: {e}")
        return None


def merge_directory(directory: Path, out_path: Path, version_hint: str | None = None):
    merged = []
    detected_versions = set()

    # Process files in alphabetical order
    files = sorted(directory.glob('*.json'), key=lambda x: x.name)
    for p in files:
        data = load_json_safe(p)
        if not data:
            continue
        # Accept files with a 'nodes' list or 'classes' list
        nodes = None
        if isinstance(data, dict) and 'nodes' in data and isinstance(data['nodes'], list):
            nodes = data['nodes']
        elif isinstance(data, dict) and 'classes' in data and isinstance(data['classes'], list):
            nodes = data['classes']
        else:
            continue

        # detect version label from file if present
        for key in ('pyqgis_version', 'houdini_version', 'version'):
            if key in data and isinstance(data[key], str) and data[key]:
                detected_versions.add(data[key])

        # Determine category for this file: prefer top-level 'category', else filename stem
        raw_cat = ''
        if isinstance(data, dict) and 'category' in data and isinstance(data['category'], str) and data['category'].strip():
            raw_cat = data['category'].strip()
        else:
            raw_cat = p.stem
        # sanitize category to one-liner like Map_Actions
        category = re.sub(r'[^A-Za-z0-9]+', '_', raw_cat).strip('_')

        # Append all items from this file, preserving their order and assigning this category
        for item in nodes:
            if not isinstance(item, dict):
                continue
            name = (item.get('name') or '').strip()
            if not name:
                continue
            desc = (item.get('description') or '').strip()
            url = (item.get('url') or '').strip()
            merged.append({
                'name': name,
                'description': desc,
                'url': url,
                'category': category
            })

    # Determine version to write
    version = version_hint or (sorted(detected_versions)[0] if detected_versions else '')
    out = {
        'module': 'pyqgis',
        'type': 'classes',
        'version': version,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'classes': merged
    }

    try:
        with out_path.open('w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Wrote merged file: {out_path} (classes: {len(out['classes'])})")
    except Exception as e:
        print(f"Failed to write {out_path}: {e}")
        return 1
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--dir', '-d', default='.', help='Directory containing category JSON files')
    p.add_argument('--out', '-o', default=None, help='Output filename (default: pyqgis_<version>.json or pyqgis_all.json)')
    p.add_argument('--version', '-v', default=None, help='Version hint (e.g. 3.40)')
    args = p.parse_args(argv)

    directory = Path(args.dir).resolve()
    if not directory.exists() or not directory.is_dir():
        print('Directory not found:', directory)
        return 2

    # build default out filename: include module, type and version
    out_name = args.out
    if not out_name:
        if args.version:
            out_name = f'pyqgis_classes_{args.version}.json'
        else:
            out_name = 'pyqgis_classes_all.json'
    out_path = directory / out_name

    return merge_directory(directory, out_path, args.version)


if __name__ == '__main__':
    raise SystemExit(main())
