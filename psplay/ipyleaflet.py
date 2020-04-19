# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
from traitlets import CFloat, Enum, Unicode

from ipyleaflet import Control, Layer, LocalTileLayer, allowed_crs

from ._version import EXTENSION_VERSION

allowed_crs += ['CAR']
allowed_colormaps = ['gray', 'planck', 'wmap', 'hotcold']


class Graticule(Layer):
    _view_name = Unicode('LeafletGraticuleView').tag(sync=True)
    _model_name = Unicode('LeafletGraticuleModel').tag(sync=True)
    _view_module = Unicode('jupyter-leaflet-car').tag(sync=True)
    _model_module = Unicode('jupyter-leaflet-car').tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    name = Unicode('graticule').tag(sync=True)


class ColorizableTileLayer(LocalTileLayer):
    _view_name = Unicode('LeafletColorizableTileLayerView').tag(sync=True)
    _model_name = Unicode('LeafletColorizableTileLayerModel').tag(sync=True)
    _view_module = Unicode('jupyter-leaflet-car').tag(sync=True)
    _model_module = Unicode('jupyter-leaflet-car').tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    colormap = Enum(values=allowed_colormaps, default_value='planck').tag(sync=True, o=True)
    value_min = CFloat(-500).tag(sync=True, o=True)
    value_max = CFloat(+500).tag(sync=True, o=True)
    scale = CFloat(1.0).tag(sync=True, o=True)


class StatusBarControl(Control):
    _view_name = Unicode('LeafletStatusBarControlView').tag(sync=True)
    _model_name = Unicode('LeafletStatusBarControlModel').tag(sync=True)
    _view_module = Unicode('jupyter-leaflet-car').tag(sync=True)
    _model_module = Unicode('jupyter-leaflet-car').tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    prefix = Unicode('').tag(sync=True, o=True)
    position = Unicode('bottomleft').tag(sync=True, o=True)
