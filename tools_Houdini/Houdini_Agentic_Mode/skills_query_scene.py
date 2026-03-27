from .rpc_bridge import run_houdini_python


def list_nodes(path: str) -> str:
    if not path or not isinstance(path, str):
        raise ValueError('path must be non-empty')
    code = f"""
import hou
n = hou.node({path!r})
if n is None:
    raise RuntimeError('Node not found: ' + {path!r})
children = n.children()
print('\n'.join([c.path() for c in children]))
""".strip()
    return run_houdini_python(code)
