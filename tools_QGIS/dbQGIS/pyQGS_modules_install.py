# script for installing additional modules
# into qgis python environment from within QGIS

import sys

try:
    from pip._internal.cli.main import main as pipmain
except Exception:
    pipmain = None

try:
    # Works in QGIS Python env; falls back to terminal input when unavailable.
    from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox
except Exception:
    QInputDialog = None
    QMessageBox = None

# core dependency set used by dbQGIS scripts
BASE_MODULES = [
    "geopandas",
    "mercantile",
    "vt2geojson",
    "dbfread",
    "rasterio",
    "databricks-sql-connector",
]

# pinned examples for h3 version families
H3_V3_SPEC = "h3<4"
H3_V4_SPEC = "h3==4.3.1"

# QGIS-bundled numpy is often non-pip-managed; keep rasterio on a compatible
# branch and avoid dependency resolution that tries to replace numpy.
RASTERIO_PIN = "rasterio==1.4.4"


def _build_install_args(module_spec):
    if module_spec == "rasterio":
        return ["install", "--no-deps", RASTERIO_PIN]
    return ["install", module_spec]


def _print_python_paths():
    print("\nPython paths in this QGIS session:")
    print("\n".join(sys.path))


def _ask_text(title, prompt, default=""):
    if QInputDialog is not None:
        text, ok = QInputDialog.getText(None, title, prompt, text=default)
        return text.strip(), bool(ok)
    value = input(f"{prompt} ").strip()
    return value, True


def _ask_choice(title, prompt, choices, current=0):
    if QInputDialog is not None:
        item, ok = QInputDialog.getItem(None, title, prompt, choices, current, False)
        return item, bool(ok)

    print(f"\n{prompt}")
    for i, choice in enumerate(choices, start=1):
        print(f"{i}. {choice}")
    raw = input("Select number (blank = cancel): ").strip()
    if not raw:
        return "", False
    try:
        idx = int(raw) - 1
    except ValueError:
        return "", False
    if idx < 0 or idx >= len(choices):
        return "", False
    return choices[idx], True


def _qmsg_yes_no_values():
    # PyQt5: QMessageBox.Yes/No, PyQt6: QMessageBox.StandardButton.Yes/No
    yes = getattr(QMessageBox, "Yes", None)
    no = getattr(QMessageBox, "No", None)
    if yes is not None and no is not None:
        return yes, no

    standard_button = getattr(QMessageBox, "StandardButton", None)
    if standard_button is not None:
        yes = getattr(standard_button, "Yes", None)
        no = getattr(standard_button, "No", None)
        if yes is not None and no is not None:
            return yes, no

    return None, None


def _ask_yes_no(title, prompt, default_no=True):
    if QMessageBox is not None:
        yes, no = _qmsg_yes_no_values()
        if yes is not None and no is not None:
            buttons = yes | no
            default = no if default_no else yes
            answer = QMessageBox.question(None, title, prompt, buttons, default)
            return answer == yes

    suffix = "[y/N]" if default_no else "[Y/n]"
    raw = input(f"{prompt} {suffix}: ").strip().lower()
    if not raw:
        return not default_no
    return raw in ("y", "yes")


def _run_pip(args):
    if pipmain is None:
        print("pip is not available in this QGIS Python environment.")
        print("Try opening the OSGeo/QGIS shell that includes pip, then rerun from QGIS.")
        return 2

    print(f"\n>>> pip {' '.join(args)}")
    code = pipmain(args)
    if code == 0:
        print("OK")
    else:
        print(f"Failed with exit code {code}")
    return code


def list_installed_modules():
    _print_python_paths()
    return _run_pip(["list"])


def install_one_module_test():
    default_module = BASE_MODULES[0]
    module, ok = _ask_text(
        "pyQGIS Install Test",
        "Module name to install (example: mercantile)",
        default=default_module,
    )
    if not ok or not module:
        print("Cancelled")
        return 1
    return _run_pip(_build_install_args(module))


def _choose_h3_spec():
    want_h3 = _ask_yes_no("Optional h3", "Also install h3?")
    if not want_h3:
        return None

    choice, ok = _ask_choice(
        "h3 version",
        "Choose h3 version branch",
        ["3.x (h3<4)", "4.x pinned (h3==4.3.1)"],
    )
    if not ok:
        print("h3 choice cancelled; skipping h3")
        return None
    if choice.startswith("3.x"):
        return H3_V3_SPEC
    return H3_V4_SPEC


def install_all_modules():
    modules = list(BASE_MODULES)
    h3_spec = _choose_h3_spec()
    if h3_spec:
        modules.append(h3_spec)

    if not _ask_yes_no(
        "Confirm install",
        "Install all selected modules into this QGIS Python environment?",
    ):
        print("Cancelled")
        return 1

    any_fail = False
    for module_spec in modules:
        result = _run_pip(_build_install_args(module_spec))
        if result != 0:
            any_fail = True

    if any_fail:
        print("\nCompleted with errors. Review output above for failing packages.")
        return 1

    print("\nAll selected modules installed.")
    return 0


def uninstall_modules_one_by_one():
    modules = list(BASE_MODULES) + ["h3"]
    any_action = False

    for module in modules:
        uninstall_this = _ask_yes_no(
            "Confirm uninstall",
            f"Uninstall '{module}' from this QGIS Python environment?",
        )
        if uninstall_this:
            any_action = True
            _run_pip(["uninstall", module, "-y"])

    if not any_action:
        print("No modules selected for uninstall.")
    return 0


def show_main_menu():
    options = [
        "List installed modules",
        "Install-test one module",
        "Install all required modules",
        "Uninstall modules one by one",
        "Exit",
    ]

    choice, ok = _ask_choice("pyQGIS Module Manager", "Choose action", options)
    if not ok:
        print("Cancelled")
        return 5

    if choice == options[0]:
        return 1
    if choice == options[1]:
        return 2
    if choice == options[2]:
        return 3
    if choice == options[3]:
        return 4
    return 5


def main():
    action = show_main_menu()
    if action == 1:
        list_installed_modules()
    elif action == 2:
        install_one_module_test()
    elif action == 3:
        install_all_modules()
    elif action == 4:
        uninstall_modules_one_by_one()
    else:
        print("Exit")


def _should_autorun():
    # QGIS Python console can execute scripts with __name__ == '__console__'.
    return globals().get("__name__") in ("__main__", "__console__")


if _should_autorun():
    main()
