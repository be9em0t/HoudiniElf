from typing import Dict, Optional

from .network_templates import apply_network_template
from .vex_tools import push_vex_to_node
from .rpc_bridge import run_houdini_python
from .skills_build_network import build_network_from_intent


def route_intent(intent_text: str, context: Optional[Dict] = None) -> Dict:
    """Map high-level intent to tool call structure."""
    text = intent_text.strip().lower()
    context = context or {}

    if 'build new geo network' in text or ('scatter over it' in text and 'copy to points' in text):
        code = build_network_from_intent(text, context.get('target_path', '/obj'))
        return {
            'intent': 'build_geo_network',
            'tool': 'run_houdini_python',
            'args': {'code': code},
        }

    if 'scatter' in text and ('copy' in text or 'network' in text or 'chain' in text):
        return {
            'intent': 'scatter_copy',
            'tool': 'apply_network_template',
            'args': {'template_name': 'scatter_copy', 'target_path': context.get('target_path', '/obj')},
        }

    if 'push' in text and 'vex' in text:
        node_path = context.get('node_path')
        file_path = context.get('file_path')
        if not node_path or not file_path:
            raise ValueError('push_vex_to_node requires node_path and file_path in context')
        return {
            'intent': 'push_vex',
            'tool': 'push_vex_to_node',
            'args': {'node_path': node_path, 'file_path': file_path},
        }

    if 'list nodes' in text or 'enumerate nodes' in text:
        target_path = context.get('target_path', '/obj')
        return {
            'intent': 'list_nodes',
            'tool': 'run_houdini_python',
            'args': {'code': f"'\\n'.join([n.path() for n in __import__('hou').node('{target_path}').children()])"},
        }

    if 'inspect node' in text:
        node_path = context.get('node_path')
        if not node_path:
            raise ValueError('inspect node requires node_path')
        return {
            'intent': 'inspect_node',
            'tool': 'run_houdini_python',
            'args': {'code': f"__import__('hou').node('{node_path}').parm('snippet').eval()"},
        }

    # fallback: safe run_houdini_python if nothing else matches
    if 'run' in text or 'execute' in text or 'python' in text:
        code = context.get('code')
        if not code:
            raise ValueError('No code provided for run_houdini_python fallback')
        return {
            'intent': 'run_python',
            'tool': 'run_houdini_python',
            'args': {'code': code},
        }

    raise ValueError(f"Unknown intent: {intent_text}")


def execute_routed_intent(routed: Dict):
    tool = routed['tool']
    args = routed['args']

    if tool == 'apply_network_template':
        return apply_network_template(**args)
    if tool == 'push_vex_to_node':
        return push_vex_to_node(**args)
    if tool == 'run_houdini_python':
        return run_houdini_python(**args)
    raise ValueError(f"Unsupported tool: {tool}")
