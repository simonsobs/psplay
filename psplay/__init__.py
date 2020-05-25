from ._version import get_versions
from .psplay import App  # noqa

__version__ = get_versions()["version"]
del get_versions


def _jupyter_nbextension_paths():
    return [
        {
            "section": "notebook",
            "src": "static",
            "dest": "jupyter-leaflet-car",
            "require": "jupyter-leaflet-car/extension",
        }
    ]
