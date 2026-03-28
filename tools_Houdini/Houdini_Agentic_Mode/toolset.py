"""Atomic Houdini tool wrappers for MCP/LLM usage."""
from .rpc_bridge import run_houdini_python


def create_node(node_type: str, parent: str = '/obj', name: str = None) -> str:
    if not name:
        name = f"{node_type}_auto"
    code = f"p = hou.node('{parent}'); n = p.createNode('{node_type}', '{name}'); n.moveToGoodPosition(); n.path()"
    return run_houdini_python(code)


def set_parm(node_path: str, parm: str, value) -> str:
    code = f"n=hou.node('{node_path}'); n.parm('{parm}').set({repr(value)}); 'ok'"
    return run_houdini_python(code)


def cook_node(node_path: str) -> str:
    code = f"n=hou.node('{node_path}'); n.cook(force=True); 'ok'"
    return run_houdini_python(code)


def save_hip(path: str) -> str:
    code = f"hou.hipFile.save('{path}'); 'ok'"
    return run_houdini_python(code)


def export_geometry(node_path: str, path: str) -> str:
    code = (
        f"n=hou.node('{node_path}'); "
        f"if n is None: raise RuntimeError('node not found'); "
        f"g=n.geometry(); g.saveToFile('{path}'); 'ok'"
    )
    return run_houdini_python(code)
