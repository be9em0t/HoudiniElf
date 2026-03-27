import hou

def _find_existing_python_shell():
    # 1) direct desktop search via enum tabType (if available)
    try:
        desktop = hou.ui.curDesktop()
        if hasattr(hou, "paneTabType"):
            try:
                shell = desktop.paneTabOfType(hou.paneTabType.PythonShell)
                if shell:
                    return shell
            except Exception:
                pass
    except Exception:
        pass

    # 2) scan all visible tabs
    for tab in hou.ui.paneTabs():
        name = tab.type().name()
        if name in ("pythonShell", "PythonShell"):
            return tab
    return None

def _try_create_python_shell():
    # try both desktop and hou.ui creator forms
    candidates = []
    if hasattr(hou, "paneTabType"):
        for attr in dir(hou.paneTabType):
            if attr.startswith("_"):
                continue
            try:
                candidates.append(getattr(hou.paneTabType, attr))
            except Exception:
                pass

    # some API variants expect a string or enum name
    candidates += ["pythonShell", "PythonShell"]

    desktop = None
    try:
        desktop = hou.ui.curDesktop()
    except Exception:
        desktop = None

    for candidate in candidates:
        if desktop is not None:
            try:
                shell = desktop.createFloatingPaneTab(candidate)
                shell.setActive(True)
                print(f"Opened python shell with desktop.createFloatingPaneTab({candidate})")
                return shell
            except Exception as exc:
                print(f"desktop.createFloatingPaneTab({candidate}) failed: {exc}")

        if hasattr(hou.ui, "createFloatingPaneTab"):
            try:
                shell = hou.ui.createFloatingPaneTab(candidate)
                shell.setActive(True)
                print(f"Opened python shell with hou.ui.createFloatingPaneTab({candidate})")
                return shell
            except Exception as exc:
                print(f"hou.ui.createFloatingPaneTab({candidate}) failed: {exc}")

    return None

def ensure_python_shell_open():
    shell = _find_existing_python_shell()
    if shell:
        try:
            shell.setActive(True)
        except Exception:
            pass
        return shell
    # try to create; if fails, return None and keep normal output path
    return _try_create_python_shell()

def show_message(text):
    # use UI message only if no shell available
    shell = _find_existing_python_shell()
    if shell is None:
        try:
            hou.ui.displayMessage(text, severity=hou.severityType.Warning)
            return
        except Exception:
            pass
    print(text)

def print_selected_node_diagnostics():
    nodes = hou.selectedNodes()
    if not nodes:
        show_message("No node selected")
        return

    node = nodes[0]
    errors = node.errors()
    warnings = node.warnings()

    ensure_python_shell_open()
    if not (errors or warnings):
        print(f"No warnings/errors on {node.path()}")
        return

    print(f"Node: {node.path()}")
    if errors:
        print("Errors:")
        for e in errors:
            print("  -", e)
    if warnings:
        print("Warnings:")
        for w in warnings:
            print("  -", w)

print_selected_node_diagnostics()