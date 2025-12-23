import re

# Read the VEX file
vex_file_path = "/Users/dunevv/Library/CloudStorage/OneDrive-TomTom/3D_projects/QGIS/VegasMNR/Vegas_CES2026/generated_vex_code.vex"

with open(vex_file_path, 'r') as f:
    vex_code = f.read()

# Parse points
points = []
point_pattern = r'int pt(\d+) = addpoint\(0, set\(([^,]+), ([^,]+), ([^\)]+)\)\);'
for match in re.finditer(point_pattern, vex_code):
    x, y, z = match.groups()[1:4]
    points.append(f"({x}, {y}, {z})")

# Parse primitives (assuming one polyline)
prim_match = re.search(r'addprim\(0, "polyline", ([^\)]+)\);', vex_code)
if prim_match:
    indices_str = prim_match.group(1)
    indices = [int(idx.strip()) for idx in indices_str.split(',')]
    prims = [indices]
else:
    prims = []

# Output Python code
points_str = ',\n    '.join(points)
prims_str = str(prims)[1:-1]  # remove outer brackets to make it list content

python_code = f"""
node = hou.pwd()
geo = node.geometry()
geo.clear()

# Points data
points_data = [
    {points_str}
]

# Primitives data
prims_data = [{prims_str}]

# Create points
for pos in points_data:
    pt = geo.createPoint()
    pt.setPosition(pos)

# Create primitives
for pts in prims_data:
    points_list = [geo.point(pt_idx) for pt_idx in pts]
    prim = geo.createPrim(hou.PrimType.Polyline)
    prim.setVertices(points_list)
"""

print(python_code)