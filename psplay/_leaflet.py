# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
from traitlets import (Bool, CFloat, CInt, Dict, Enum, Unicode, default,
                       validate)

from ipyleaflet import Circle, Control, Layer, LayersControl, LocalTileLayer

EXTENSION_VERSION = "^0.0.7"

allowed_colormaps = ["gray", "planck", "wmap", "hotcold"]


class Circle(Circle):
    radius = CFloat(10, help="radius of circle in degrees").tag(sync=True, o=True)


class LayersControl(LayersControl):
    collapsed = Bool(False).tag(sync=True, o=True)


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

    base = Bool(False).tag(sync=True, o=True)
    colormap = Enum(values=allowed_colormaps, default_value="planck").tag(sync=True, o=True)
    value_min = CFloat(-500).tag(sync=True, o=True)
    value_max = CFloat(+500).tag(sync=True, o=True)
    scale = CFloat(1.0).tag(sync=True, o=True)
    scale_amplitude = CFloat(0.1).tag(sync=True, o=True)
    tag_id = CInt(None, allow_none=True).tag(sync=True, o=True)


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
        return dict(colormap=["g"], colorscale=["u", "i"], cache=["z"])

    @validate("keybindings")
    def _validate_keybindings(self, proposal):
        """Validate keybindings list.

        Makes sure no more than 2 keys are given and no duplicates.
        """
        keys = set()
        for k, v in proposal.value.items():
            if isinstance(v, dict):
                v = v.get("keys", [])
            if len(v) > 2:
                raise ValueError("More than 2 keys for a keybinding is not allowed!")
            duplicates = keys.intersection(set(v))
            if len(duplicates) > 0:
                raise ValueError(
                    "Duplicate {} entry in keybindings. Check your keys!".format(duplicates)
                )
            keys.update(v)
        return proposal.value
