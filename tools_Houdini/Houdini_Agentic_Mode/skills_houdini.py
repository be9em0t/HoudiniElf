"""Houdini domain skill layer: map high-level user goals to intent router actions."""
import re
from typing import Dict, Optional

try:
    from tools_Houdini.Houdini_Agentic_Mode.llm_adapter import llm_translate_intent_to_houdini_code
    from tools_Houdini.Houdini_Agentic_Mode.toolset import create_node, set_parm, cook_node, save_hip, export_geometry
except ImportError:
    try:
        from .llm_adapter import llm_translate_intent_to_houdini_code
        from .toolset import create_node, set_parm, cook_node, save_hip, export_geometry
    except ImportError:
        from llm_adapter import llm_translate_intent_to_houdini_code
        # toolset not available in this import context; fallback to direct code generation
        create_node = None
        set_parm = None
        cook_node = None
        save_hip = None
        export_geometry = None


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
    if not user_text or not isinstance(user_text, str) or not user_text.strip():
        raise ValueError('user_text must be a non-empty string')

    context = context or {}
    text = user_text.strip().lower()

    # Explicit, safe metadata-only skill operations
    if 'list nodes' in text or 'enumerate nodes' in text:
        path = context.get('target_path', '/obj')
        code = f"'\\n'.join([n.path() for n in hou.node('{path}').children()])"
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
        code = f"hou.node('{node_path}').parm('snippet').eval()"
        return {
            'intent': 'inspect_node',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': f'Inspect parameter snippet for {node_path}.',
        }

    # Specific high-level intent handlers (pattern-based) for faster deterministic behavior.
    if 'root nodes' in text and '/obj' in text:
        code = "obj = hou.node('/obj'); paths = [n.path() for n in obj.children()]; print('\\n'.join(paths))"
        return {
            'intent': 'list_nodes',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': 'List root nodes under /obj.',
        }

    if 'principled shader' in text and 'blue' in text:
        code = (
            "mat = hou.node('/mat'); "
            "if mat is None: mat = hou.node('/obj').createNode('matnet', 'mat'); "
            "n = mat.createNode('principledshader::2.0', 'principled_blue'); "
            "n.parm('basecolorr').set(0.0); n.parm('basecolorg').set(0.3); n.parm('basecolorb').set(1.0); n.moveToGoodPosition();"
        )
        return {
            'intent': 'add_principled_shader',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': 'Create a blue principled shader in /mat.',
        }

    if 'create torus' in text and 'dimensions' in text:
        w = _parse_number(text, r'dimensions\s*(\d+(?:\.\d*)?)', default=2.0)
        code = (
            f"n = hou.node('/obj').createNode('torus', 'torus_{w}'); "
            f"n.parm('rad1').set({w}); n.parm('rad2').set({w}); n.parm('tx').set(0); n.parm('ty').set(0); n.parm('tz').set(0); n.moveToGoodPosition();"
        )
        return {
            'intent': 'create_torus',
            'tool': 'run_houdini_python',
            'args': {'code': code},
            'explanation': 'Create torus with provided dimensions at origin.',
        }

    # General-purpose LLM-driven intent path.
    llm_code = llm_translate_intent_to_houdini_code(user_text, context)
    return {
        'intent': 'llm_interpreted_command',
        'tool': 'run_houdini_python',
        'args': {'code': llm_code},
        'explanation': 'Generated Houdini python code for user intent via LLM.',
    }



