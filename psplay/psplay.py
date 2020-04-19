# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
import os

import yaml

from ipyleaflet import FullScreenControl, LayersControl, Map, MapStyle

from .ipyleaflet import ColorizableTileLayer, Graticule, StatusBarControl

so_attribution = 'Tiles &copy; <a href="https://simonsobservatory.org/">Simons Observatory</a>'


class App:
    def __init__(self, config):
        if isinstance(config, dict):
            self.config = config
        else:
            with open(config, "r") as stream:
                self.config = yaml.load(stream, Loader=yaml.FullLoader)
        self.layers = [Graticule()]
        self._add_layers()
        self._add_map()

    def show_map(self):
        return self.m

    def _add_layers(self):
        def _get_section(section, name):
            if not (value := section.get(name)):
                raise ValueError("Missing '{}' section".format(name))
            return value

        maps = _get_section(self.config, "maps")
        for imap in maps:
            map_id = _get_section(imap, "id")
            fits = _get_section(imap, "fits")
            tiles = _get_section(imap, "tiles")
            path = _get_section(tiles, "path")
            vrange = [[-500, +500], [-100, +100], [-100, +100]]
            if (r := tiles.get("range")) :
                if (val := r.get("temperature")) :
                    vrange[0] = [-val, +val]
                if (val := r.get("polarization")) :
                    vrange[1] = [-val, +val]
                    vrange[2] = [-val, +val]
            for i, j in enumerate(["min", "max"]):
                if (m := tiles.get(j)) :
                    if (val := m.get("temperature")) :
                        vrange[0][i] = val
                    if (val := m.get("polarization")) :
                        vrange[1][i] = val
                        vrange[2][i] = val

            data_type = imap.get("data_type", "IQU")
            for i, item in enumerate(data_type):
                name = "{} - {} - {}".format(tiles.get("prefix", "CMB"), map_id, item)
                url = (
                    path
                    if ".png" in path
                    else "files" + os.path.join(path, fits, "{z}/tile_{y}_{x}_%s.png" % i)
                )
                self.layers.append(
                    ColorizableTileLayer(
                        url=url,
                        base=True,
                        min_zoom=-5,
                        max_zoom=+5,
                        min_native_zoom=-5,
                        max_native_zoom=0,
                        tile_size=675,
                        attribution=tiles.get("attribution", so_attribution),
                        name=name,
                        show_loading=False,
                        colormap=tiles.get("colormap", "planck"),
                        value_min=vrange[i][0],
                        value_max=vrange[i][1],
                    )
                )

    def _add_map(self):
        self.m = Map(
            layers=self.layers,
            controls=(
                FullScreenControl(),
                StatusBarControl(),
                LayersControl(collapsed=False, position="topright"),
            ),
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
            dragging_style=MapStyle(cursor="default"),
        )
