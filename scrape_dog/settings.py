"""INI-backed settings for scrape_dog.

Provides helpers to read and write scraper mode entries and the meta
`last_mode` flag stored in `scrape_settings.ini` next to the package.

All file I/O stays inside the `scrape_dog` package so the rest of the app
can remain unaware of the storage format.
"""
from __future__ import annotations

from pathlib import Path
import configparser
from typing import Dict, Optional


_INI_NAME = 'scrape_settings.ini'


def _get_ini_path() -> Path:
    return Path(__file__).resolve().parent / _INI_NAME


def _load_parser() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # preserve case of keys
    p = _get_ini_path()
    if p.exists():
        cfg.read(p, encoding='utf-8')
    return cfg


def get_mode_names() -> list[str]:
    cfg = _load_parser()
    return [s for s in cfg.sections() if s.lower() != 'meta']


def get_modes() -> Dict[str, Dict[str, str]]:
    cfg = _load_parser()
    modes: Dict[str, Dict[str, str]] = {}
    for sec in cfg.sections():
        if sec.lower() == 'meta':
            continue
        data = {}
        # accept a few common key names for the root url
        url_key = None
        for k in ('url', 'root_url', 'root url'):
            if k in cfg[sec]:
                url_key = k
                break
        data['url'] = cfg[sec].get(url_key or 'url', '')
        data['software'] = cfg[sec].get('software', '')
        data['version'] = cfg[sec].get('version', '')
        modes[sec] = data
    return modes


def get_mode(name: str) -> Optional[Dict[str, str]]:
    return get_modes().get(name)


def get_last_mode() -> Optional[str]:
    cfg = _load_parser()
    if 'meta' in cfg and 'last_mode' in cfg['meta']:
        return cfg['meta']['last_mode']
    return None


def set_last_mode(name: str) -> None:
    cfg = _load_parser()
    if 'meta' not in cfg:
        cfg['meta'] = {}
    cfg['meta']['last_mode'] = name
    _save_parser(cfg)


def update_mode(name: str, *, software: Optional[str] = None, version: Optional[str] = None, url: Optional[str] = None) -> None:
    cfg = _load_parser()
    if name not in cfg:
        cfg[name] = {}
    if software is not None:
        cfg[name]['software'] = software
    if version is not None:
        cfg[name]['version'] = version
    if url is not None:
        cfg[name]['url'] = url
    _save_parser(cfg)


def _save_parser(cfg: configparser.ConfigParser) -> None:
    p = _get_ini_path()
    # ensure directory exists (it should) and write
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as fh:
        cfg.write(fh)


def ensure_defaults(defaults: Dict[str, Dict[str, str]]) -> None:
    """Optionally create missing sections from a defaults mapping.

    This is helpful on first run to seed the INI with useful values.
    """
    cfg = _load_parser()
    changed = False
    for name, data in defaults.items():
        if name not in cfg:
            cfg[name] = {}
            if 'software' in data:
                cfg[name]['software'] = data['software']
            if 'version' in data:
                cfg[name]['version'] = data['version']
            if 'url' in data:
                cfg[name]['url'] = data['url']
            changed = True
    if changed:
        _save_parser(cfg)


# On first import, if the package-level INI doesn't exist, seed it with a
# small set of sensible defaults matching the repository's `scrape_settings.ini`.
_DEFAULTS = {
    'houdini vex': {
        'url': 'https://www.sidefx.com/docs/houdini20.5/vex/functions/index.html',
        'version': '20.5',
        'software': 'Houdini',
    },
    'houdini nodes': {
        'url': 'https://www.sidefx.com/docs/houdini20.5/nodes/obj/index.html',
        'version': '20.5',
        'software': 'Houdini',
    },
    'python pyqgis api': {
        'url': 'https://qgis.org/pyqgis/3.40/core/index.html',
        'version': '3.40',
        'software': 'QGIS',
    },
    'shadergraph': {
        'url': 'https://docs.unity3d.com/Packages/com.unity.shadergraph@17.1/manual/Node-Library.html',
        'version': '17.1',
        'software': 'Unity ShaderGraph',
    },
}


def _seed_if_missing() -> None:
    p = _get_ini_path()
    if not p.exists():
        ensure_defaults(_DEFAULTS)


# perform seeding lazily on import
try:
    _seed_if_missing()
except Exception:
    # be tolerant of I/O errors during import; callers can still use functions
    # and unit tests will control file locations by monkeypatching if needed.
    pass
