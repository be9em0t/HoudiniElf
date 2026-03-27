# ⚡ List Houdini file references and export to CSV
# Short: writes houdini_file_references_report.csv next to the .hip (or to ~ if unsaved)

import os, csv
try:
    import hou
except Exception:
    print("Run this inside Houdini / hython.")
    raise

def gather_file_refs(only_external=False, project_var='HIP', include_all=True):
    hipdir = os.environ.get('HIP', '')
    rows = []
    for parm, reported_path in hou.fileReferences(project_dir_variable=project_var, include_all_refs=include_all):
        # Some references are not attached to a Parm (parm can be None).
        # Guard every parm call and fall back to reasonable defaults.
        if parm is None:
            node_path = ''
            parm_path = ''
            parm_name = ''
            raw = reported_path or ''
        else:
            # safe accessors for parm-derived values
            try:
                node_path = parm.node().path() if parm.node() is not None else ''
            except Exception:
                node_path = ''
            try:
                parm_path = parm.path()
            except Exception:
                parm_path = ''
            try:
                parm_name = parm.name()
            except Exception:
                parm_name = ''
            try:
                raw = parm.unexpandedString()
            except Exception:
                raw = reported_path or ''

        # expand/resolve the reported path (may contain $HIP/$JOB)
        try:
            resolved = hou.text.expandString(reported_path) if reported_path else ''
        except Exception:
            resolved = reported_path or ''

        inside_hip = False
        if hipdir and resolved:
            try:
                inside_hip = os.path.abspath(resolved).startswith(os.path.abspath(hipdir))
            except Exception:
                inside_hip = False

        if only_external and inside_hip:
            continue

        try:
            exists_on_disk = bool(resolved) and os.path.exists(resolved)
        except Exception:
            exists_on_disk = False

        rows.append({
            'node_path': node_path,
            'parm_path': parm_path,
            'parm_name': parm_name,
            'raw_string': raw,
            'reported_path': reported_path,
            'resolved_path': resolved,
            'inside_HIP': inside_hip,
            'exists_on_disk': exists_on_disk
        })
    return rows

# ----- Parameters (based on your selections) -----
only_external = False          # you selected: All file references
out_dir = os.path.dirname(hou.hipFile.path()) or os.path.expanduser('~')
out_file = os.path.join(out_dir, 'houdini_file_references_report.csv')

rows = gather_file_refs(only_external=only_external)
if not rows:
    print("No file references found.")
else:
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("Wrote", out_file)
    # macOS: open the CSV automatically
    try:
        os.system('open "{}"'.format(out_file))
    except Exception:
        pass