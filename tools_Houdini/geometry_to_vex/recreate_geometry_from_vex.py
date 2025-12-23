import hou
import re

def recreate_geometry_from_vex(vex_file_path):
    # Read the VEX file
    with open(vex_file_path, 'r') as f:
        vex_code = f.read()

    # Parse points
    points = []
    point_pattern = r'int pt\d+ = addpoint\(0, set\(([^,]+), ([^,]+), ([^\)]+)\)\);'
    for match in re.finditer(point_pattern, vex_code):
        x, y, z = map(float, match.groups())
        points.append((x, y, z))

    # Parse primitives (assuming one polyline)
    prim_match = re.search(r'addprim\(0, "polyline", ([^\)]+)\);', vex_code)
    if prim_match:
        indices_str = prim_match.group(1)
        indices = [int(idx.strip()) for idx in indices_str.split(',')]
    else:
        indices = []

    # Get current geometry
    node = hou.pwd()
    geo = node.geometry()
    geo.clear()

    # Create points
    created_points = []
    for pos in points:
        pt = geo.createPoint()
        pt.setPosition(hou.Vector3(pos))
        created_points.append(pt)

    # Create polyline
    if indices:
        prim = geo.createPrim(hou.PrimType.Polyline)
        for idx in indices:
            prim.addVertex(created_points[idx])

# Usage: call this function with the path to the VEX file
vex_file_path = "/Users/dunevv/Library/CloudStorage/OneDrive-TomTom/3D_projects/QGIS/VegasMNR/Vegas_CES2026/generated_vex_code.vex"
recreate_geometry_from_vex(vex_file_path)