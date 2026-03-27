"""Houdini domain skill layer: map high-level user goals to intent router actions."""
import re
from typing import Dict, Optional


def _parse_color(text: str):
    colors = {
        'pink': (1.0, 0.41, 0.71),
        'blue': (0.0, 0.0, 1.0),
        'red': (1.0, 0.0, 0.0),
        'green': (0.0, 1.0, 0.0),
        'white': (1.0, 1.0, 1.0),
        'black': (0.0, 0.0, 0.0),
    }
    for k, v in colors.items():
        if k in text:
            return k, v
    return 'white', colors['white']


def _parse_number(text: str, pattern: str, default: float = 1.0) -> float:
    match = re.search(pattern, text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return default


def interpret_request(user_text: str, context: Optional[Dict] = None) -> Dict:
    context = context or {}
    text = user_text.strip().lower()

    if 'list nodes' in text or 'enumerate nodes' in text:
        path = context.get('target_path', '/obj')
        code = f"'\\n'.join([n.path() for n in __import__('hou').node('{path}').children()])"
        return {
            'intent': 'list_nodes',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': f'List nodes under path {path}.',
        }

    if 'inspect node' in text:
        node_path = context.get('node_path')
        if not node_path:
            raise ValueError('inspect node requires node_path in context')
        code = f"__import__('hou').node('{node_path}').parm('snippet').eval()"
        return {
            'intent': 'inspect_node',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': f'Inspect parameter snippet for {node_path}.',
        }

    if 'create' in text and 'sphere' in text:
        radius = _parse_number(text, r'radius\s*of\s*([0-9]*\.?[0-9]+)', 1.0)
        if radius == 1.0:
            diameter = _parse_number(text, r'diameter\s*of\s*([0-9]*\.?[0-9]+)', 2.0)
            radius = diameter / 2.0
        height = _parse_number(text, r'([0-9]*\.?[0-9]+)\s*above\s*ground', 0.0)
        color_name, (r_val, g_val, b_val) = _parse_color(text)

        code = f"""
import hou
obj = hou.node('/obj')
if obj is None:
    raise RuntimeError('/obj not found')
geo = obj.createNode('geo', 'agentic_{color_name}_sphere_geo')
geo.moveToGoodPosition()
sph = geo.createNode('sphere', 'agentic_{color_name}_sphere')
sph.parm('radx').set({radius})
sph.parm('rady').set({radius})
sph.parm('radz').set({radius})
trans = geo.createNode('xform', 'agentic_{color_name}_sphere_xform')
trans.setInput(0, sph)
trans.parm('ty').set({height})
col = geo.createNode('color', 'agentic_{color_name}_sphere_color')
col.setInput(0, trans)
col.parm('colorr').set({r_val})
col.parm('colorg').set({g_val})
col.parm('colorb').set({b_val})
col.setDisplayFlag(True)
col.setRenderFlag(True)
geo.layoutChildren()
obj.setDisplayFlag(False)
geo.setCurrent(True, clear_all_selected=True)
'created a {color_name} sphere in /obj at y={height}'
"""
        return {
            'intent': f'create_{color_name}_sphere',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': f'Create sphere with radius {radius}, color {color_name}, at height {height}.',
        }

    if 'run' in text or 'execute' in text or 'python' in text:
        code = context.get('code')
        if not code:
            raise ValueError('No code provided for run_houdini_python fallback')
        return {
            'intent': 'run_python',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': 'Execute explicit python command.',
        }

    raise ValueError(f'Unknown intent: {user_text}')
