#!/usr/bin/env python3
"""
export_shelf.py

Scan a Houdini user prefs `toolbar` folder and produce a self-contained
.shelf file for a given (lightweight) shelf that only contains memberTool
entries (like your `vla.shelf`). The script also collects referenced
script and icon files into an assets directory.

Usage:
  python export_shelf.py --prefs ~/Library/Preferences/houdini/20.5 \
      --shelf-file ~/Library/Preferences/houdini/20.5/toolbar/vla.shelf \
      --out ~/Desktop/vla_export.shelf --assets-dir ~/Desktop/vla_assets

The script does not require Houdini's Python (works with system Python).
It parses .shelf XML files, finds <tool> definitions referenced by the
memberTool list and writes a new .shelf containing those tool nodes plus
the toolshelf entry.

Limitations:
- Assumes shelf XMLs have <tool> elements with attribute 'name'.
- Tries to collect assets referenced by <icon> tags and <script file="...">.
- Test the produced shelf in Houdini before overwriting prefs.
"""

import argparse
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--prefs", required=True,
                   help="Houdini user prefs root (e.g. ~/Library/Preferences/houdini/20.5)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--shelf-file",
                       help="Path to the shelf file that contains the toolshelf (e.g. vla.shelf)")
    group.add_argument("--shelf-name",
                       help="Name of the toolshelf to export (will search toolbar/ for toolshelf name)")
    p.add_argument("--out", required=True, help="Output .shelf path")
    p.add_argument("--assets-dir", required=False,
                   help="Optional path to copy scripts/icons into (recommended)")
    return p.parse_args()


def get_member_tool_names(shelf_file_path):
    tree = ET.parse(shelf_file_path)
    root = tree.getroot()
    # find toolshelf node
    names = []
    for ts in root.findall('.//toolshelf'):
        for mem in ts.findall('memberTool'):
            name = mem.get('name')
            if name:
                names.append(name)
    return names, root


def find_shelf_file_by_name(toolbar_dir, shelf_name):
    """Search .shelf files under toolbar_dir for a toolshelf element with name==shelf_name.
    Return tuple (shelf_file_path, toolshelf_element, tree_root) or (None, None, None).
    """
    for dirpath, _, filenames in os.walk(toolbar_dir):
        for fn in filenames:
            if not fn.lower().endswith('.shelf') and not fn.lower().endswith('.xml'):
                continue
            full = os.path.join(dirpath, fn)
            try:
                tree = ET.parse(full)
            except ET.ParseError:
                continue
            root = tree.getroot()
            for ts in root.findall('.//toolshelf'):
                if ts.get('name') == shelf_name or ts.get('label') == shelf_name:
                    return full, ts, root
    return None, None, None


def find_tool_nodes(prefs_root, member_names):
    """Search all .shelf/.xml files under prefs_root for <tool> nodes that
    match any of member_names. Matching is tolerant: exact name, label, or
    case-insensitive occurrence of the member name in the tool subtree text.
    Returns dict member_name->(tool_element, source_file).
    """
    found = {}
    member_lc = [m.lower() for m in member_names]
    for dirpath, _, filenames in os.walk(prefs_root):
        for fn in filenames:
            if not fn.lower().endswith('.shelf') and not fn.lower().endswith('.xml'):
                continue
            full = os.path.join(dirpath, fn)
            try:
                tree = ET.parse(full)
            except ET.ParseError:
                # skip malformed
                continue
            root = tree.getroot()
            for tool in root.findall('.//tool'):
                t_name = (tool.get('name') or '').strip()
                t_label = (tool.get('label') or '').strip()
                # compute combined text of tool subtree
                subtree_text = ET.tostring(tool, encoding='utf-8', method='text').decode('utf-8').lower()

                for idx, m in enumerate(member_lc):
                    original_member = member_names[idx]
                    if original_member in found:
                        continue
                    # direct matches
                    if t_name.lower() == m or t_label.lower() == m:
                        found[original_member] = (tool, full)
                        continue
                    # contained text match (case-insensitive)
                    if m in subtree_text:
                        found[original_member] = (tool, full)
                        continue
    return found


def collect_asset_paths(tool_elem):
    """Return a set of asset file paths (relative paths) referenced by a tool element."""
    assets = set()
    # look for <icon> tags
    for icon in tool_elem.findall('.//icon'):
        if icon.text and icon.text.strip():
            assets.add(icon.text.strip())
    # look for script elements with file attribute or text that looks like a relative file
    for sc in tool_elem.findall('.//script'):
        fattr = sc.get('file')
        if fattr:
            assets.add(fattr)
        # sometimes script contains a reference to 'scripts/...' or a filename
        if sc.text and 'scripts/' in sc.text:
            # crude extraction: look for scripts/... token
            parts = sc.text.split()
            for part in parts:
                if 'scripts/' in part:
                    # strip punctuation
                    part = part.strip('"\'')
                    assets.add(part)
    return assets


def copy_assets(assets, prefs_root, assets_out_dir):
    copied = []
    for asset in assets:
        # asset may be relative like scripts/foo.py or icons/bar.png
        src = os.path.join(prefs_root, asset)
        if not os.path.exists(src):
            # try relative to toolbar dir
            src = os.path.join(prefs_root, 'toolbar', asset)
        if not os.path.exists(src):
            # skip missing
            continue
        dst = os.path.join(assets_out_dir, asset)
        dst_dir = os.path.dirname(dst)
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append((src, dst))
    return copied


def build_output_shelf(out_shelf_path, tools_by_name, original_toolshelf_elem):
    # root
    root = ET.Element('shelfDocument')

    # append tool nodes first (deepcopy)
    for name, (tool_elem, srcfile) in tools_by_name.items():
        root.append(deepcopy(tool_elem))

    # append the toolshelf definition (copying the original toolshelf element if available)
    if original_toolshelf_elem is not None:
        root.append(deepcopy(original_toolshelf_elem))
    else:
        # fallback: create a simple toolshelf element listing members
        ts = ET.Element('toolshelf')
        ts.set('name', os.path.splitext(os.path.basename(out_shelf_path))[0])
        ts.set('label', os.path.splitext(os.path.basename(out_shelf_path))[0])
        for name in tools_by_name.keys():
            m = ET.Element('memberTool')
            m.set('name', name)
            ts.append(m)
        root.append(ts)

    # write xml with declaration
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0) if hasattr(ET, 'indent') else None
    tree.write(out_shelf_path, encoding='utf-8', xml_declaration=True)


def main():
    args = parse_args()
    prefs = os.path.expanduser(args.prefs)
    out = os.path.expanduser(args.out)

    shelf_file = None
    original_toolshelf = None
    shelf_root = None

    # determine shelf file and toolshelf element
    if getattr(args, 'shelf_file', None):
        shelf_file = os.path.expanduser(args.shelf_file)
    else:
        # search for shelf by name
        toolbar_dir = os.path.join(prefs, 'toolbar')
        found_file, ts_elem, root = find_shelf_file_by_name(toolbar_dir, args.shelf_name)
        if not found_file:
            print('Could not find a shelf named', args.shelf_name, 'under', toolbar_dir)
            sys.exit(1)
        shelf_file = found_file
        original_toolshelf = ts_elem
        shelf_root = root

    if not os.path.isdir(prefs):
        print('Prefs folder not found:', prefs)
        sys.exit(1)

    if not os.path.exists(shelf_file):
        print('Shelf file not found:', shelf_file)
        sys.exit(1)

    # if we didn't already parse the shelf (when found by name), parse now
    if shelf_root is None:
        member_names, shelf_root = get_member_tool_names(shelf_file)
    else:
        # extract member names from original_toolshelf element
        member_names = []
        for mem in original_toolshelf.findall('memberTool'):
            n = mem.get('name')
            if n:
                member_names.append(n)
    if not member_names:
        print('No memberTool entries found in', shelf_file)
        sys.exit(1)

    print('Found member tools:', member_names)

    tools_found = find_tool_nodes(prefs, member_names)

    if not tools_found:
        print('No tool definitions found for these members under', toolbar_dir)
        print('You may need to search other .shelf files or use Houdini to export directly.')
        sys.exit(1)

    print('Found definitions for:', list(tools_found.keys()))

    # collect assets
    assets = set()
    for name, (tool_elem, srcfile) in tools_found.items():
        assets.update(collect_asset_paths(tool_elem))

    if args.assets_dir and assets:
        assets_out = os.path.expanduser(args.assets_dir)
        os.makedirs(assets_out, exist_ok=True)
        copied = copy_assets(assets, prefs, assets_out)
        print('Copied assets:', copied)
    elif assets:
        print('Assets referenced but --assets-dir not provided. Assets list:')
        for a in assets:
            print(' -', a)

    # find the original toolshelf element for inclusion
    original_toolshelf = None
    # search for toolshelf element with matching name inside the provided shelf file
    for ts in shelf_root.findall('.//toolshelf'):
        original_toolshelf = ts
        break

    # build output shelf that includes the tool nodes and toolshelf
    build_output_shelf(out, tools_found, original_toolshelf)
    print('Wrote consolidated shelf to', out)


if __name__ == '__main__':
    main()
