"""Houdini RPC tool layer for command execution and safe helpers."""
from typing import Dict

from .rpc_bridge import check_houdini_rpc, run_houdini_python


def rpc_health() -> Dict[str, str]:
    """Returns health status and message."""
    status = check_houdini_rpc()
    if status == 'rpc_ok':
        return {'status': 'ok', 'message': 'Houdini RPC server is reachable'}
    return {'status': 'down', 'message': status}


def execute_python(code: str) -> Dict[str, str]:
    """Execute Python code in Houdini through RPC."""
    assert isinstance(code, str) and code.strip(), 'code must be non-empty string'

    result = run_houdini_python(code)
    return {'status': 'ok', 'result': result}


def create_node(node_type: str, parent: str = '/obj', name: str = None, parms: Dict[str, object] = None) -> Dict[str, str]:
    """Create a Houdini node and optionally set parameters."""
    if not node_type:
        raise ValueError('node_type is required')
    name_expr = f", '{name}'" if name else ''
    code_lines = [
        "import hou",
        f"root = hou.node('{parent}')",
        "if root is None: raise RuntimeError('parent path not found: {parent}')",
        f"node = root.createNode('{node_type}'{name_expr})",
        "node.moveToGoodPosition()",
    ]
    if parms:
        for key, value in parms.items():
            code_lines.append(f"node.parm('{key}').set({repr(value)})")
    code_lines.append("root.layoutChildren()")
    code = '\n'.join(code_lines)
    return execute_python(code)


def set_parm(node_path: str, parm_name: str, value: object) -> Dict[str, str]:
    """Set node parameter in Houdini."""
    if not node_path or not parm_name:
        raise ValueError('node_path and parm_name are required')
    code = (
        "import hou\n"
        f"node = hou.node('{node_path}')\n"
        "if node is None: raise RuntimeError('node not found: {node_path}')\n"
        f"parm = node.parm('{parm_name}')\n"
        "if parm is None: raise RuntimeError('parm not found: {parm_name}')\n"
        f"parm.set({repr(value)})\n"
    )
    return execute_python(code)
