# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
#

from ._version import __version__, version_info  # noqa
from .psplay import App  # noqa


def _jupyter_nbextension_paths():
    return [
        {
            "section": "notebook",
            "src": "static",
            "dest": "jupyter-leaflet-car",
            "require": "jupyter-leaflet-car/extension",
        }
    ]
