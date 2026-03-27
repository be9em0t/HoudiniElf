# do not run in chat, for your own toolkit usage
def rpc_node_update(path, snippet=None, params=None, cook=True, check_errors=True):
    import hou
    n = hou.node(path)
    if n is None:
        raise RuntimeError(f"Node not found: {path}")
    if snippet is not None:
        n.parm("snippet").set(snippet)
    if params:
        for k,v in params.items():
            p = n.parm(k)
            if p is None:
                raise RuntimeError(f"Parm not found: {path}.{k}")
            p.set(v)
    if cook:
        n.cook(force=True)
    if check_errors:
        errs = n.errors()
        if errs:
            raise RuntimeError(f"Houdini node errors: {errs}")
    return n