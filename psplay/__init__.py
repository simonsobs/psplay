# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
#

from ._version import version_info, __version__  # noqa

# Allow dependencies to psplay to not be installed upon post-link for
# conda-build.

try:
    from .psplay import App
    # from .leaflet_car import Graticule
except ImportError:
    pass


def _jupyter_nbextension_paths():
    return [{
        'section': 'notebook',
        'src': 'static',
        'dest': 'jupyter-leaflet-car',
        'require': 'jupyter-leaflet-car/extension'
    }]
