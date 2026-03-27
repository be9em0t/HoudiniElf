import pathlib
from .rpc_bridge import run_houdini_python


def push_vex_to_node(node_path: str, file_path: str, cook: bool = True) -> str:
    """Load a VEX file and push to a wrangle node snippet."""
    if not node_path or not isinstance(node_path, str):
        raise ValueError("`node_path` must be a non-empty string")
    if not file_path or not isinstance(file_path, str):
        raise ValueError("`file_path` must be a non-empty string")

    p = pathlib.Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"VEX file not found: {file_path}")

    code = p.read_text(encoding="utf-8")

    # Eval-only endpoint. Use lambda+tuple to avoid statements.
    if cook:
        actions = f"(n.parm('snippet').set({code!r}), n.cook(force=True), n.path())"
    else:
        actions = f"(n.parm('snippet').set({code!r}), n.path())"

    py_cmd = (
        f"(lambda n: n is None and (_ for _ in ()).throw(RuntimeError('Node not found: {node_path}')) "
        f"or {actions}[-1])(__import__('hou').node({node_path!r}))"
    )

    return run_houdini_python(py_cmd)
