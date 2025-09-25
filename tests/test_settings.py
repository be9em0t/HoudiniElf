import sys
import tempfile
from pathlib import Path
import importlib


def _ensure_repo_on_path():
    # Prepend repo root so tests can import the package when run in isolation
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def test_settings_read_write_and_last_mode(monkeypatch, tmp_path):
    # Ensure settings module uses a temp package dir for INI
    _ensure_repo_on_path()
    pkg_dir = tmp_path / 'pkg'
    pkg_dir.mkdir()
    # copy the settings module path by monkeypatching __file__ location
    import scrape_dog.settings as settings

    # monkeypatch the module file location so _get_ini_path points to tmp
    monkeypatch.setattr(settings, '__file__', str(pkg_dir / 'settings.py'))

    # Ensure no INI exists at the target
    ini_path = (pkg_dir / 'scrape_settings.ini')
    if ini_path.exists():
        ini_path.unlink()

    # Seed defaults explicitly and verify sections created
    defaults = {
        'foo': {'url': 'https://example.com', 'software': 'X', 'version': '1.0'},
        'bar': {'url': 'https://other', 'software': 'Y', 'version': '2.0'},
    }
    settings.ensure_defaults(defaults)
    modes = settings.get_modes()
    assert 'foo' in modes and 'bar' in modes
    assert modes['foo']['url'] == 'https://example.com'

    # Test last mode get/set
    settings.set_last_mode('foo')
    assert settings.get_last_mode() == 'foo'

    # Update mode url and verify persisted
    settings.update_mode('foo', url='https://changed')
    modes = settings.get_modes()
    assert modes['foo']['url'] == 'https://changed'


def test_get_mode_names_and_get_mode(monkeypatch, tmp_path):
    pkg_dir = tmp_path / 'pkg2'
    pkg_dir.mkdir()
    _ensure_repo_on_path()
    import scrape_dog.settings as settings
    monkeypatch.setattr(settings, '__file__', str(pkg_dir / 'settings.py'))

    defaults = {
        'alpha': {'url': 'https://a', 'software': 'A', 'version': '0.1'},
    }
    settings.ensure_defaults(defaults)
    names = settings.get_mode_names()
    assert 'alpha' in names
    mode = settings.get_mode('alpha')
    assert mode['software'] == 'A'
    assert mode['version'] == '0.1'
