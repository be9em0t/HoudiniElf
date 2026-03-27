from .rpc_bridge import run_houdini_python


def apply_network_template(template_name: str, target_path: str) -> str:
    if template_name != 'scatter_copy':
        raise ValueError(f"Unknown template: {template_name}")
    if not target_path or not isinstance(target_path, str):
        raise ValueError("`target_path` must be a non-empty string")

    # Eval-only RPC endpoint accepts expressions only, so use a lambda chain.
    py_cmd_template = """
(lambda obj: obj is None and (_ for _ in ()).throw(RuntimeError('Target path not found: {target_path}')) or \
    (lambda geo: (lambda scatter, relax, cp: (relax.parm('snippet').set('@P *= 1.0;'), relax.setInput(0, scatter), cp.setInput(0, __import__('hou').node('/obj/agentic_mesh')), cp.setInput(1, relax), geo.layoutChildren(), obj.layoutChildren(), obj.path())[-1])(
        geo.createNode('scatter', 'agentic_scatter'),
        geo.createNode('pointwrangle', 'agentic_relax'),
        geo.createNode('copytopoints', 'agentic_copy')
    ))(
        obj.createNode('geo', 'agentic_geo')
    ))(__import__('hou').node('{target_path}'))
"""
    py_cmd = ' '.join(line.strip() for line in py_cmd_template.format(target_path=target_path).splitlines())

    return run_houdini_python(py_cmd)
