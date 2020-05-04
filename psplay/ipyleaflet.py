# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
from traitlets import CFloat, Dict, Enum, Unicode, default, validate

from ipyleaflet import Control, Layer, LocalTileLayer, allowed_crs

from ._version import EXTENSION_VERSION

allowed_crs += ["CAR"]
allowed_colormaps = ["gray", "planck", "wmap", "hotcold"]


class Graticule(Layer):
    _view_name = Unicode("LeafletGraticuleView").tag(sync=True)
    _model_name = Unicode("LeafletGraticuleModel").tag(sync=True)
    _view_module = Unicode("jupyter-leaflet-car").tag(sync=True)
    _model_module = Unicode("jupyter-leaflet-car").tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    name = Unicode("graticule").tag(sync=True)


class ColorizableTileLayer(LocalTileLayer):
    _view_name = Unicode("LeafletColorizableTileLayerView").tag(sync=True)
    _model_name = Unicode("LeafletColorizableTileLayerModel").tag(sync=True)
    _view_module = Unicode("jupyter-leaflet-car").tag(sync=True)
    _model_module = Unicode("jupyter-leaflet-car").tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    colormap = Enum(values=allowed_colormaps, default_value="planck").tag(sync=True, o=True)
    value_min = CFloat(-500).tag(sync=True, o=True)
    value_max = CFloat(+500).tag(sync=True, o=True)
    scale = CFloat(1.0).tag(sync=True, o=True)
    tag = Unicode("layer").tag(sync=True, o=True)

    def __lt__(self, other):
        return self.name[-1] < other.name[-1]


class StatusBarControl(Control):
    _view_name = Unicode("LeafletStatusBarControlView").tag(sync=True)
    _model_name = Unicode("LeafletStatusBarControlModel").tag(sync=True)
    _view_module = Unicode("jupyter-leaflet-car").tag(sync=True)
    _model_module = Unicode("jupyter-leaflet-car").tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    prefix = Unicode("").tag(sync=True, o=True)
    position = Unicode("bottomleft").tag(sync=True, o=True)


class KeyBindingControl(Control):
    _view_name = Unicode("LeafletKeyBindingControlView").tag(sync=True)
    _model_name = Unicode("LeafletKeyBindingControlModel").tag(sync=True)
    _view_module = Unicode("jupyter-leaflet-car").tag(sync=True)
    _model_module = Unicode("jupyter-leaflet-car").tag(sync=True)

    _view_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)
    _model_module_version = Unicode(EXTENSION_VERSION).tag(sync=True)

    keybindings = Dict().tag(sync=True, o=True)
    help_text = Unicode("").tag(sync=True, o=True)
    position = Unicode("topright").tag(sync=True, o=True)

    @default("keybindings")
    def _default_keybindings(self):
        return dict(colormap=["g"], scale=["u", "i"], layer=["j", "k"], cache=["z"])

    @validate("keybindings")
    def _validate_keybindings(self, proposal):
        """Validate keybindings list.

        Makes sure no more than 2 keys are given.
        """
        for k, v in proposal.value.items():
            if len(v) > 2:
                raise ValueError("More than 2 keys for a keybinding is not allowed!")
        return proposal.value
