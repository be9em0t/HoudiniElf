node = hou.pwd()
geo = node.geometry()

# Collect points
points = []
for pt in geo.points():
    pos = pt.position()
    points.append(f"set({pos[0]}, {pos[1]}, {pos[2]})")

# Output VEX code to a file (adjust path as needed)
vex_code = """
// VEX code to recreate geometry
void main() {
"""
for i, pos in enumerate(points):
    vex_code += f"    int pt{i} = addpoint(0, {pos});\n"
vex_code += "\n"

# Collect primitives (now assuming polygons/polylines after Convert SOP)
for i, prim in enumerate(geo.prims()):
    if prim.type() == hou.primType.Polygon:
        pts_vars = [f"pt{pt.number()}" for pt in prim.points()]
        vex_code += f"    int points{i}[] = array({', '.join(pts_vars)});\n"
        vex_code += f"    addprim(0, \"poly\", points{i});\n"

vex_code += "}\n"

# Save to file in the Houdini project directory
hip_path = hou.hipFile.path()
if hip_path:
    output_path = hou.expandString("$HIP/generated_vex_code.vex")
else:
    output_path = "/tmp/generated_vex_code.vex"  # Fallback

with open(output_path, 'w') as f:
    f.write(vex_code)

print(f"VEX code saved to: {output_path}")