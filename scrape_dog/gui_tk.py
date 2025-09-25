"""A minimal Tkinter GUI fallback for scrape_dog.

This lightweight GUI is used when no Qt binding is installed. It mirrors the
fields from the Qt GUI (adapter, url, software, version, max results) and
runs adapters synchronously.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import json
from pathlib import Path


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


def _autosave_result(software: str, version: str, data):
    outdir = Path(__file__).resolve().parent / 'capture_results'
    outdir.mkdir(parents=True, exist_ok=True)
    import re, datetime

    def safe(s: str) -> str:
        s = (s or '').strip()
        if not s:
            return ''
        return re.sub(r'[^0-9A-Za-z]+', '_', s)

    sname = safe(software)
    vname = safe(version)
    if sname or vname:
        base = f"{sname}_{vname}" if vname else sname
    else:
        base = f"capture_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    path = outdir / (base + '.json')
    if path.exists():
        path = outdir / (base + '_' + datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ') + '.json')
    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data, default=str, indent=2)
    path.write_text(text, encoding='utf-8')
    return path


def run_gui():
    try:
        from . import settings
        modes = settings.get_mode_names()
        last = settings.get_last_mode()
        modes_map = settings.get_modes()
    except Exception:
        modes = ['vex', 'python', 'unity_shadergraph']
        last = None
        modes_map = {}

    root = tk.Tk()
    root.title('scrape_dog (tk)')

    frm = ttk.Frame(root, padding=8)
    frm.pack(fill='both', expand=True)

    ttk.Label(frm, text='Adapter:').grid(row=0, column=0, sticky='w')
    adapter_var = tk.StringVar(value=modes[0] if modes else 'vex')
    adapter_cb = ttk.Combobox(frm, textvariable=adapter_var, values=modes)
    adapter_cb.grid(row=0, column=1, sticky='ew')

    ttk.Label(frm, text='URL:').grid(row=1, column=0, sticky='w')
    url_var = tk.StringVar()
    url_e = ttk.Entry(frm, textvariable=url_var, width=60)
    url_e.grid(row=1, column=1, sticky='ew')

    ttk.Label(frm, text='Software:').grid(row=2, column=0, sticky='w')
    software_var = tk.StringVar()
    ttk.Entry(frm, textvariable=software_var).grid(row=2, column=1, sticky='ew')

    ttk.Label(frm, text='Version:').grid(row=3, column=0, sticky='w')
    version_var = tk.StringVar()
    ttk.Entry(frm, textvariable=version_var).grid(row=3, column=1, sticky='ew')

    ttk.Label(frm, text='Max Results:').grid(row=4, column=0, sticky='w')
    max_var = tk.IntVar(value=0)
    ttk.Spinbox(frm, from_=0, to=100000, textvariable=max_var).grid(row=4, column=1, sticky='w')

    txt = scrolledtext.ScrolledText(frm, height=20)
    txt.grid(row=5, column=0, columnspan=2, sticky='nsew', pady=(8, 0))

    frm.columnconfigure(1, weight=1)
    frm.rowconfigure(5, weight=1)

    def log(msg: str):
        txt.insert('end', msg + '\n')
        txt.see('end')

    def on_adapter_change(event=None):
        cur = adapter_var.get()
        meta = modes_map.get(cur, {})
        if meta.get('url'):
            url_var.set(meta.get('url'))
        if meta.get('software'):
            software_var.set(meta.get('software'))
        if meta.get('version'):
            version_var.set(meta.get('version'))

    def on_run():
        adapter = adapter_var.get()
        url = url_var.get().strip()
        if not url:
            messagebox.showinfo('scrape_dog', 'Please enter a URL')
            return
        max_results = int(max_var.get() or 0)
        software = software_var.get().strip()
        version = version_var.get().strip()
        log(f'Starting adapter {adapter} for {url} (max={max_results})')
        try:
            modname = _adapter_module_for_mode(adapter)
            mod = __import__(f'scrape_dog.adapters.{modname}', fromlist=['*'])
            func = None
            for name in dir(mod):
                if name.startswith('run_'):
                    func = getattr(mod, name)
                    break
            if func is None:
                raise RuntimeError('Adapter missing run_ function')
            doc = asyncio.run(func(url, max_results=max_results))
            try:
                data = doc.model_dump() if hasattr(doc, 'model_dump') else doc
                out = json.dumps(data, default=str, indent=2)
            except Exception:
                out = str(doc)
            txt.delete('1.0', 'end')
            txt.insert('1.0', out)
            path = _autosave_result(software, version, out)
            log(f'Autosaved to {path}')
        except Exception as exc:
            log(f'Run failed: {exc}')

    run_btn = ttk.Button(frm, text='Run', command=on_run)
    run_btn.grid(row=6, column=0, sticky='w', pady=(8, 0))

    def on_save():
        content = txt.get('1.0', 'end').strip()
        if not content:
            messagebox.showinfo('scrape_dog', 'No result to save')
            return
        path = _autosave_result(software_var.get(), version_var.get(), content)
        log(f'Saved to {path}')

    save_btn = ttk.Button(frm, text='Save', command=on_save)
    save_btn.grid(row=6, column=1, sticky='e', pady=(8, 0))

    adapter_cb.bind('<<ComboboxSelected>>', on_adapter_change)
    if last:
        try:
            adapter_cb.set(last)
            on_adapter_change()
        except Exception:
            pass

    root.mainloop()
