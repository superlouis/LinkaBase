"""Read the application version from project metadata."""
from importlib.metadata import version as installed_version
from pathlib import Path
import tomllib

PYPROJECT = Path(__file__).resolve().parents[1] / 'pyproject.toml'


def get_version():
    """Prefer checkout metadata, including when an older wheel is installed."""
    if PYPROJECT.is_file():
        with PYPROJECT.open('rb') as source:
            return tomllib.load(source)['project']['version']
    return installed_version('linkabase')


__version__ = get_version()
