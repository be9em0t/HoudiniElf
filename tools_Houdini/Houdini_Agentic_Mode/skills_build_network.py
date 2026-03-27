from .network_templates import apply_network_template
import re


def build_network_from_intent(intent: str, target_path: str):
    intent = intent.strip().lower()
    if 'scatter' in intent and 'copy' in intent and 'build new geo network' not in intent:
        return apply_network_template('scatter_copy', target_path)
    if 'build new geo network' in intent:
        return build_geo_network_from_description(intent, target_path)
    raise ValueError(f"No template mapping for intent: {intent}")


def _parse_floats(text: str):
    return [float(x) for x in re.findall(r'[-+]?[0-9]*\.?[0-9]+', text)]


def build_geo_network_from_description(description: str, target_path: str = '/obj') -> str:
    """Generate Houdini expression for a defined geometry/ scatter/ copy pipeline."""
    pos_match = re.search(r'positioned at\s*([\d\-\.]+)\s*,\s*([\d\-\.]+)\s*,\s*([\d\-\.]+)', description)
    size_match = re.search(r'side dimesions of\s*([\d\-\.]+)', description)
    scatter_match = re.search(r'scatter over it\s*([0-9]+)\s*points', description)
    sphere_match = re.search(r'sphere with diameter of\s*([\d\-\.]+)', description)

    px, py, pz = (float(x) for x in pos_match.groups()) if pos_match else (100.0, 0.0, 0.0)
    side = float(size_match.group(1)) if size_match else 42.0
    scatter_count = int(scatter_match.group(1)) if scatter_match else 1024
    sphere_d = float(sphere_match.group(1)) if sphere_match else 1.42

    code = (
        f"(lambda root: (" \
        f"(geo := root.createNode('geo', 'agentic_geo')), " \
        f"(cube := geo.createNode('box', 'agentic_box')), " \
        f"cube.parm('tx').set({px}), cube.parm('ty').set({py}), cube.parm('tz').set({pz}), " \
        f"cube.parm('sizex').set({side}), cube.parm('sizey').set({side}), cube.parm('sizez').set({side}), " \
        f"(spt := geo.createNode('scatter', 'agentic_scatter')), spt.parm('npts').set({scatter_count}), spt.setInput(0, cube), " \
        f"(sph := geo.createNode('sphere', 'agentic_sphere')), sph.parm('radx').set({sphere_d / 2.0}), sph.parm('rady').set({sphere_d / 2.0}), sph.parm('radz').set({sphere_d / 2.0}), " \
        f"(cp := geo.createNode('copytopoints', 'agentic_copy')), cp.setInput(0, sph), cp.setInput(1, spt), " \
        f"(mat := geo.createNode('material', 'agentic_material')), mat.setInput(0, cp), " \
        f"(out := geo.createNode('null', 'agentic_out')), out.setInput(0, mat), " \
        f"geo.layoutChildren(), root.layoutChildren(), out.path())[ -1])(__import__('hou').node('{target_path}'))"
    )

    return code
