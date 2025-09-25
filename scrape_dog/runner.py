"""Small runner module to execute an adapter and print the result as JSON.

This is designed to be invoked as a subprocess with the repository on
PYTHONPATH, e.g. `python -m scrape_dog.runner <mode> <url> <max_results>`.

It maps mode names to adapter modules heuristically (same logic as the GUI)
and runs the adapter coroutine, printing the resulting DocumentModel as
JSON to stdout. Progress messages and errors are written to stderr so the
caller (GUI) can show them separately.
"""
from __future__ import annotations

import sys
import json
import asyncio
from importlib import import_module
from typing import Optional


def _adapter_module_for_mode(mode_name: str) -> str:
    mn = (mode_name or '').lower()
    if 'vex' in mn:
        return 'vex'
    if 'python' in mn or 'pyqgis' in mn:
        return 'python'
    if 'shader' in mn or 'shadergraph' in mn:
        return 'unity_shadergraph'
    if 'node' in mn:
        return 'vex'
    return mn.split()[0] if mn else 'vex'


async def _run_adapter(adapter_module: str, url: str, max_results: int):
    mod = import_module(f'scrape_dog.adapters.{adapter_module}')
    func = None
    for name in dir(mod):
        if name.startswith('run_'):
            func = getattr(mod, name)
            break
    if func is None:
        raise RuntimeError(f'Adapter {adapter_module} exposes no run_ function')
    # Run and return the document model
    doc = await func(url, max_results=max_results)
    return doc


def main(argv=None):
    argv = argv or sys.argv
    if len(argv) < 2:
        print('Usage: python -m scrape_dog.runner <mode> <url> [max_results]', file=sys.stderr)
        return 2
    mode = argv[1]
    url = argv[2] if len(argv) > 2 else ''
    try:
        max_results = int(argv[3]) if len(argv) > 3 else 0
    except Exception:
        max_results = 0

    try:
        modname = _adapter_module_for_mode(mode)
        print(f'Running adapter module: {modname}', file=sys.stderr)
        doc = asyncio.run(_run_adapter(modname, url, max_results))
        # try to produce JSON
        try:
            out = doc.model_dump() if hasattr(doc, 'model_dump') else doc
            print(json.dumps(out, default=str))
        except Exception:
            # fallback to str()
            print(str(doc))
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
