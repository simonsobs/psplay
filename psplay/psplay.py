# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#

from ipyleaflet import FullScreenControl, LayersControl, Map, MapStyle

from .leaflet_car import ColorizableTileLayer, Graticule, StatusBarControl

so_attribution = 'Tiles &copy; <a href="https://simonsobservatory.org/">Simons Observatory</a>'


class App():
    def add_map(self, layers=None):
        _layers = [Graticule()]
        if layers is not None:
            _layers += layers
        return Map(layers=_layers,
                   controls=(FullScreenControl(), StatusBarControl(),
                             LayersControl(collapsed=False, position="topright")),
                   crs="CAR",
                   center=(0, 0),
                   min_zoom=-5,
                   max_zoom=+5,
                   interpolation="nearest",
                   zoom=0,
                   scroll_wheel_zoom=True,
                   fade_animation=False,
                   world_copy_jump=True,
                   style=MapStyle(cursor="default"),
                   default_style=MapStyle(cursor="default"),
                   dragging_style=MapStyle(cursor="default"))

    def define_layer(self,
                     url,
                     name,
                     attribution=so_attribution,
                     colormap="planck",
                     value_min=-500,
                     value_max=+500):
        return ColorizableTileLayer(url="files/" + url,
                                    base=True,
                                    min_zoom=-5,
                                    max_zoom=+5,
                                    min_native_zoom=-5,
                                    max_native_zoom=0,
                                    tile_size=675,
                                    attribution=attribution,
                                    name=name,
                                    show_loading=False,
                                    colormap=colormap,
                                    value_min=value_min,
                                    value_max=value_max)
