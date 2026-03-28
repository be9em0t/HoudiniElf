"""Houdini domain skill layer: map high-level user goals to intent router actions."""
import re
from typing import Dict, Optional

from .llm_adapter import llm_translate_intent_to_houdini_code


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

    # General-purpose LLM-driven intent path.
    llm_code = llm_translate_intent_to_houdini_code(user_text, context)
    return {
        'intent': 'llm_interpreted_command',
        'tool': 'run_houdini_python',
        'args': {'code': llm_code},
        'explanation': 'Generated Houdini python code for user intent via LLM.',
    }



