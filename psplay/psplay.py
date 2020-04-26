# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
import os
from itertools import product

import ipywidgets as widgets
import numpy as np
import yaml

import plotly.graph_objects as go
from ipyleaflet import (DrawControl, FullScreenControl, LayersControl, Map,
                        MapStyle, WidgetControl)

from .ipyleaflet import (ColorizableTileLayer, Graticule, StatusBarControl,
                         allowed_colormaps)
from .ps_tools import compute_ps

# Default SO attribution for tiles
so_attribution = '&copy; <a href="https://simonsobservatory.org/">Simons Observatory</a>'

# Generate default plotly colormap based on planck colormap
def generate_default_colorscale(default="planck"):
    from pixell import colorize

    cs = colorize.schemes[default]
    return [[val, "rgb({},{},{})".format(*cols)] for val, cols in zip(cs.vals, cs.cols)]


default_colorscale = generate_default_colorscale()

# Output widget to catch functions/programs output into a widget
out = widgets.Output()


class App:
    """ An ipywidgets and plotly application for CMB map and power spectra visualization"""

    def __init__(self, config):
        if isinstance(config, dict):
            self.config = config
        else:
            with open(config, "r") as stream:
                self.config = yaml.load(stream, Loader=yaml.FullLoader)

        self.m = None
        self.p = None
        self.patches = dict()

        self.layers = [Graticule()]
        self._add_layers()
        self._add_map()
        self._add_plot()
        self._add_theory()

    def show_map(self):
        return self.m

    def show_plot(self):
        return self.p

    def _add_layers(self):
        def _get_section(section, name):
            value = section.get(name)
            if not value:
                raise ValueError("Missing '{}' section".format(name))
            return value

        self.maps_info_list = list()
        self.map_ids = list()
        maps = _get_section(self.config, "maps")
        for imap in maps:
            # Data info
            map_id = _get_section(imap, "id")
            self.map_ids.append(map_id)
            fits = _get_section(imap, "fits")
            data_type = imap.get("data_type", "IQU")
            info = {"name": fits, "data_type": data_type, "id": map_id, "cal": None}
            self.maps_info_list.append(info)

            # Tiles
            tiles = _get_section(imap, "tiles")
            path = _get_section(tiles, "path")

            # Set color range
            vrange = [[-500, +500], [-100, +100], [-100, +100]]
            _range = tiles.get("range")
            if _range:
                _val = _range.get("temperature")
                vrange[0] = [-_val, +_val] if _val else vrange[0]
                _val = _range.get("polarization")
                vrange[1] = [-_val, +_val] if _val else vrange[1]
                vrange[2] = vrange[1] if _val else vrange[2]
            for i, j in enumerate(["min", "max"]):
                _m = tiles.get(j)
                if _m:
                    _val = _m.get("temperature")
                    vrange[0][i] = _val if _val else vrange[0][i]
                    _val = _m.get("polarization")
                    vrange[1][i] = _val if _val else vrange[1][i]
                    vrange[2][i] = vrange[1][i] if _val else vrange[2][i]

            for i, item in enumerate(data_type):
                name = "{} - {} - {}".format(tiles.get("prefix", "CMB"), map_id, item)
                url = (
                    path
                    if ".png" in path
                    else "files/" + os.path.join(path, fits, "{z}/tile_{y}_{x}_%s.png" % i)
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
        # if maps.get("sort", True):
        self.layers.sort()

    def _add_map(self):
        self.m = Map(
            layers=self.layers,
            controls=(FullScreenControl(), StatusBarControl(), LayersControl(position="topright"),),
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
        self._add_controls()

    def _add_controls(self):
        self.draw_control = DrawControl()
        self.draw_control.polyline = {}
        self.draw_control.polygon = {}
        self.draw_control.circlemarker = {}
        self.draw_control.circle = {"repeatMode": True}
        self.draw_control.rectangle = {"repeatMode": True}
        self.draw_control.edit = False
        self.draw_control.remove = False

        patches = self.patches

        def handle_draw(self, action, geo_json):
            if action == "created":
                name = "patch #{}".format(len(patches.keys()))
                patches[name] = geo_json
            elif action == "deleted":
                for k, v in patches.items():
                    if v == geo_json:
                        patches[k] = None
            else:
                print("Action = ", action)

        self.draw_control.on_draw(handle_draw)
        self.m.add_control(self.draw_control)

        scale = widgets.FloatSlider(
            value=1.0,
            min=0,
            max=2.0,
            step=0.01,
            description="scale",
            continuous_update=True,
            orientation="vertical",
            readout_format=".2f",
            layout=widgets.Layout(width="100px"),
        )

        def on_scale_change(change):
            for layer in self.layers:
                layer.scale = change["new"]

        scale.observe(on_scale_change, names="value")
        self.m.add_control(WidgetControl(widget=scale, position="bottomright"))

        cmap = widgets.RadioButtons(
            options=allowed_colormaps, value="planck", layout=widgets.Layout(width="100px"),
        )

        def on_cmap_change(change):
            for layer in self.layers:
                layer.colormap = change["new"]

        cmap.observe(on_cmap_change, names="value")
        self.m.add_control(WidgetControl(widget=cmap, position="bottomright"))

    def _add_theory(self):
        clth = {}
        lth, clth["TT"], clth["EE"], clth["BB"], clth["TE"] = np.loadtxt(
            "bode_almost_wmap5_lmax_1e4_lensedCls_startAt2.dat", unpack=True
        )
        clth["ET"] = clth["TE"]
        for spec in ["EB", "BE", "BT", "TB"]:
            clth[spec] = clth["TE"] * 0
        self.theory = {"lth": lth, "clth": clth}

    def _add_plot(self):
        plot_config = self.config.get("plot", dict())
        plotly_config = plot_config.get("plotly", dict())

        self.fig = go.FigureWidget(
            layout=go.Layout(height=600, template=plotly_config.get("template", "plotly_white"))
        )

        # Header
        allowed_spectra = ["TT", "TE", "TB", "ET", "BT", "EE", "EB", "BE", "BB"]
        self.spectra_menu = widgets.Dropdown(description="Spectra:", options=allowed_spectra)
        self.split_menu = widgets.Dropdown(
            description="Split:",
            value="{}x{}".format(*self.map_ids),
            options=["{}x{}".format(*p) for p in product(self.map_ids, repeat=2)],
        )
        self.patch_menu = widgets.Dropdown(description="Patch:", options=self.patches.keys())
        self.header = widgets.HBox([self.spectra_menu, self.split_menu])

        # Config
        layout = widgets.Layout(width="auto", height="auto")
        self.compute_T_only = widgets.Checkbox(value=False, description="Temp. only", layout=layout)
        self.plot_theory = widgets.Checkbox(value=True, description="Plot theory", layout=layout)
        self.plot_theory.observe(self._update_theory, names="value")
        self.ps_method = widgets.RadioButtons(
            options=["master", "pseudo", "2dflat"],
            value=plot_config.get("method", "master"),
            description="Method:",
            layout=layout,
        )

        def _update_method(_):
            if self.ps_method.value == "2dflat":
                self.plot_theory.disabled = True
                self.header.children = tuple(list(self.header.children) + [self.patch_menu])
            else:
                self.plot_theory.disabled = False
                if len(self.header.children) == 3:
                    self.header.children = self.header.children[:-1]

        self.ps_method.observe(_update_method, names="value")

        self.error_method = widgets.RadioButtons(
            options=["master", "knox"],
            value=plot_config.get("error", "master"),
            description="Error:",
            layout=layout,
        )
        self.lmax = widgets.IntSlider(
            value=plot_config.get("lmax", 1000),
            min=0,
            max=10000,
            step=100,
            description="$\ell_\mathrm{max}$",
        )
        self.bin_size = widgets.IntSlider(
            value=plot_config.get("bin size", 40), min=0, max=100, step=10, description="Bin size",
        )
        container = widgets.HBox(
            [
                widgets.VBox([self.compute_T_only, self.plot_theory]),
                self.ps_method,
                self.error_method,
                widgets.VBox([self.lmax, self.bin_size]),
            ]
        )
        accordion = widgets.Accordion(children=[container, out], selected_index=None)
        accordion.set_title(0, "Configuration")
        accordion.set_title(1, "Logs")

        # Footer
        self.compute_button = widgets.Button(description="Compute spectra", icon="check")
        self.clean_button = widgets.Button(description="Clean patches", icon="trash-alt")

        def _clean_patches(_):
            for k in list(self.patches.keys()):
                del self.patches[k]
            self.draw_control.clear()
            self.clean_button.description = "Clean patches ({})".format(len(self.patches))

        self.compute_button.on_click(self._compute_spectra)
        self.clean_button.on_click(_clean_patches)
        footer = widgets.HBox([self.clean_button, self.compute_button])

        self.p = widgets.VBox([self.header, self.fig, accordion, footer])

    @out.capture()
    def _compute_spectra(self, _):
        out.clear_output()
        spectra = None

        self.compute_button.description = "Running..."
        self.compute_button.icon = "gear"
        self.compute_button.disabled = True
        self.clean_button.disabled = True
        self.clean_button.description = "Clean patches ({})".format(len(self.patches))

        def parse_rectangle(coordinates):
            return [coordinates[0][0][::-1], coordinates[0][2][::-1]]

        for name, patch in self.patches.items():
            print("Compute new patch")
            if patch is None:
                continue
            patch_dict = None
            geometry = patch.get("geometry")
            if geometry.get("type") == "Polygon":
                patch_dict = {
                    "patch_type": "Rectangle",
                    "patch_coordinate": parse_rectangle(geometry.get("coordinates")),
                }
            elif geometry.get("type") == "Point":
                style = patch.get("properties").get("style")
                if style.get("radius"):
                    patch_dict = {
                        "patch_type": "Disk",
                        "center": geometry.get("coordinates")[::-1],
                        "radius": style.get("radius"),
                    }
            else:
                print("Shape '{} not supported".format(geometry))
                continue

            spectra, spec_name_list, lb, ps_dict, cov_dict = compute_ps(
                patch_dict,
                self.maps_info_list,
                ps_method=self.ps_method.value,
                error_method=self.error_method.value,
                bin_size=self.bin_size.value,
                compute_T_only=self.compute_T_only.value,
                lmax=self.lmax.value,
            )
            patch.update(
                {
                    "results": {
                        "spectra": spectra,
                        "spec_name_list": spec_name_list,
                        "lb": lb,
                        "ps": ps_dict,
                        "cov": cov_dict,
                    }
                }
            )
        if spectra is not None:
            self.spectra_menu.options = spectra
            self.spectra_menu.observe(self._update_plot, names="value")
            self.split_menu.options = spec_name_list
            self.split_menu.observe(self._update_plot, names="value")
            self.patch_menu.options = self.patches.keys()
            self.patch_menu.observe(self._update_plot, names="value")

            self._update_plot(None)

        self.compute_button.description = "Compute spectra"
        self.compute_button.icon = "check"
        self.compute_button.disabled = False
        self.clean_button.disabled = False

    def _update_theory(self, _):
        if self.plot_theory.value:
            self.fig.add_scatter(
                name="theory",
                x=self.theory.get("lth")[: self.lmax.value],
                y=self.theory.get("clth")[self.spectra_menu.value][: self.lmax.value],
                mode="lines",
                line=dict(color="gray"),
            )
        else:
            # Remove last trace
            self.fig.data = self.fig.data[:-1]

    def _update_plot(self, _):
        split_name = self.split_menu.value
        spec = self.spectra_menu.value
        ps_method = self.ps_method.value

        # Clean data & layout
        self.fig.data = []
        # self.fig.layout = {}
        if ps_method == "2dflat":
            from plotly.colors import qualitative

            patch_name = self.patch_menu.value
            results = self.patches[patch_name].get("results")
            if not results:
                return
            powermap = results.get("ps").get(split_name).powermap[spec]
            powermap = np.fft.fftshift(powermap.copy())
            shape = powermap.shape
            self.fig.update_layout(
                width=self.fig.layout.height * shape[1] / shape[0],
                title=dict(
                    text="{} - {}".format(split_name, patch_name),
                    font=dict(color=qualitative.Plotly[list(self.patches).index(patch_name)]),
                ),
                xaxis_title="$\ell_X$",
                yaxis_title="$\ell_Y$",
                coloraxis={"colorscale": default_colorscale},
            )
            self.fig.add_heatmap(z=powermap, coloraxis="coloraxis")

        else:
            self.fig.update_layout(
                title=split_name, xaxis_title="$\ell$", yaxis_title="$D_\ell^\mathrm{%s}$" % spec,
            )

            for ipatch, (name, patch) in enumerate(self.patches.items()):
                results = patch.get("results")
                if not results:
                    continue
                x = results.get("lb")
                y = results.get("ps").get(split_name).get(spec)
                yerr = np.sqrt(np.diag(results.get("cov").get(split_name).get(spec)))
                self.fig.add_scatter(
                    name=name,
                    x=x,
                    y=y,
                    error_y={"type": "data", "array": yerr, "visible": True},
                    mode="markers",
                )
            self._update_theory(None)
