from typing import Dict, Optional

try:
    from .skills_houdini import interpret_request
except ImportError:
    from skills_houdini import interpret_request


def route_intent(intent_text: str, context: Optional[Dict] = None) -> Dict:
    return interpret_request(intent_text, context)


def execute_routed_intent(routed: Dict):
    from .network_templates import apply_network_template
    from .vex_tools import push_vex_to_node
    from .rpc_bridge import run_houdini_python

    tool = routed.get('tool')
    args = routed.get('args', {})

    if tool == 'apply_network_template':
        return apply_network_template(**args)
    if tool == 'push_vex_to_node':
        return push_vex_to_node(**args)
    if tool == 'run_houdini_python':
        return run_houdini_python(**args)
    raise ValueError(f"Unsupported tool: {tool}")
