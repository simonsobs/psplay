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

        self.use_sidecar = self.config.get("use_sidecar", True)
        self.m = None
        self.p = None
        self.patches = dict()

        self.layers = [Graticule()]
        self._add_layers()
        self._add_map()
        self._add_plot()
        self._add_theory()

    def show_map(self):
        if self.use_sidecar:
            from sidecar import Sidecar
            from IPython.display import display

            sc = Sidecar(title="CMB map")
            with sc:
                display(self.m)
        else:
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

            if any(s in path for s in [".png", "http"]):
                self.layers.append(
                    ColorizableTileLayer(
                        url=path,
                        base=True,
                        min_zoom=-5,
                        max_zoom=+5,
                        min_native_zoom=-5,
                        max_native_zoom=0,
                        tile_size=675,
                        attribution=tiles.get("attribution", so_attribution),
                        name=tiles.get("name", ""),
                        show_loading=False,
                        colormap=tiles.get("colormap", "planck"),
                        value_min=vrange[i][0],
                        value_max=vrange[i][1],
                    )
                )
            else:
                for i, item in enumerate(data_type):
                    name = "{} - {} - {}".format(tiles.get("prefix", "CMB"), map_id, item)
                    url = os.path.join("files", path, fits, "{z}/tile_{y}_{x}_%s.png" % i)
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
        plot_config = self.config.get("plot", dict())
        clth = {}
        lth, clth["TT"], clth["EE"], clth["BB"], clth["TE"] = np.loadtxt(
            plot_config.get("theory", "bode_almost_wmap5_lmax_1e4_lensedCls_startAt2.dat"),
            unpack=True,
        )
        clth["ET"] = clth["TE"]
        for spec in ["EB", "BE", "BT", "TB"]:
            clth[spec] = clth["TE"] * 0.0
        self.theory = {"lth": lth, "clth": clth}

    def _add_plot(self):
        # Main
        self.tab = widgets.Tab()
        self.tab.children = [self._add_1d_plot(), self._add_2d_plot()]
        self.tab.set_title(0, "1D power spectra")
        self.tab.set_title(1, "2D power spectra")

        # General configuration
        layout = widgets.Layout(width="auto", height="auto")
        self.compute_1d = widgets.Checkbox(value=True, description="1D spectra", layout=layout)
        self.compute_2d = widgets.Checkbox(value=True, description="2D spectra", layout=layout)
        self.compute_T_only = widgets.Checkbox(
            value=False, description="Only temperature", layout=layout
        )
        self.lmax = widgets.IntSlider(
            value=1000, min=0, max=10000, step=100, description=r"$\ell_\mathrm{max}$",
        )

        # Logs
        accordion = widgets.Accordion(
            children=[
                widgets.HBox(
                    [
                        widgets.VBox([self.compute_1d, self.compute_2d]),
                        widgets.VBox([self.compute_T_only, self.lmax]),
                    ]
                ),
                out,
            ],
            selected_index=None,
        )
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
        self.p = widgets.VBox(
            [self.tab, accordion, widgets.HBox([self.clean_button, self.compute_button])]
        )

    def _add_1d_plot(self):
        # Figure widget
        plot_config = self.config.get("plot", dict())
        plotly_config = plot_config.get("plotly", dict())

        self.fig_1d = go.FigureWidget(
            layout=go.Layout(height=600, template=plotly_config.get("template", "plotly_white"))
        )

        # Header
        allowed_spectra = ["TT", "TE", "TB", "ET", "BT", "EE", "EB", "BE", "BB"]
        self.spectra_1d = widgets.Dropdown(description="Spectra:", options=allowed_spectra)
        self.split_1d = widgets.Dropdown(
            description="Split:",
            value="{}x{}".format(*self.map_ids),
            options=["{}x{}".format(*p) for p in product(self.map_ids, repeat=2)],
        )
        header = widgets.HBox([self.spectra_1d, self.split_1d])

        # Config
        layout = widgets.Layout(width="auto", height="auto")
        self.use_toeplitz = widgets.Checkbox(
            value=False, description="Use Toeplitz approx.", layout=layout
        )
        self.bin_size = widgets.IntSlider(
            value=plot_config.get("bin size", 40), min=0, max=200, step=10, description="Bin size",
        )
        config = widgets.HBox([widgets.VBox([self.use_toeplitz]), widgets.VBox([self.bin_size])])
        accordion = widgets.Accordion(children=[config], selected_index=None)
        accordion.set_title(0, "Parameters")

        return widgets.VBox([header, self.fig_1d, accordion])

    def _add_2d_plot(self):
        # Figure widget
        plot_config = self.config.get("plot", dict())
        plotly_config = plot_config.get("plotly", dict())

        self.fig_2d = go.FigureWidget(
            layout=go.Layout(height=600, template=plotly_config.get("template", "plotly_white"))
        )

        # Header
        allowed_spectra = ["II", "IQ", "IU", "QI", "QQ", "QU", "UI", "UQ", "UU"]
        self.spectra_2d = widgets.Dropdown(description="Spectra:", options=allowed_spectra)
        self.split_2d = widgets.Dropdown(
            description="Split:",
            value="{}x{}".format(*self.map_ids),
            options=["{}x{}".format(*p) for p in product(self.map_ids, repeat=2)],
        )
        self.patch_2d = widgets.Dropdown(description="Patch:", options=self.patches.keys())
        header = widgets.HBox([self.spectra_2d, self.split_2d, self.patch_2d])

        return widgets.VBox([header, self.fig_2d])

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

        for ps_method, compute in zip(
            ["master", "2dflat"], [self.compute_1d.value, self.compute_2d.value]
        ):
            if not compute:
                continue
            for ipatch, (name, patch) in enumerate(self.patches.items()):
                print("Compute patch #{}".format(ipatch))
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

                kwargs = dict(ps_method=ps_method, lmax=self.lmax.value,)
                if ps_method == "master":
                    kwargs.update(
                        dict(
                            error_method="master",
                            bin_size=self.bin_size.value,
                            compute_T_only=self.compute_T_only.value,
                            l_exact=800 if self.use_toeplitz.value else None,
                            l_band=2000 if self.use_toeplitz.value else None,
                            l_toep=2500 if self.use_toeplitz.value else None,
                        )
                    )

                method = patch.get(ps_method, dict())
                if method.get("config") == kwargs:
                    print("Patch already processed under the same condition")
                    continue

                spectra, spec_name_list, lb, ps_dict, cov_dict = compute_ps(
                    patch=patch_dict, maps_info_list=self.maps_info_list, **kwargs
                )
                method.update(
                    dict(
                        config=kwargs,
                        results={
                            "spectra": spectra,
                            "spec_name_list": spec_name_list,
                            "lb": lb,
                            "ps": ps_dict,
                            "cov": cov_dict,
                        },
                    )
                )
                patch.update({ps_method: method})

            if ps_method == "master":
                self.spectra_1d.options = spectra
                self.split_1d.options = spec_name_list
            if ps_method == "2dflat":
                self.spectra_2d.options = spectra
                self.split_2d.options = spec_name_list

        if spectra is not None:
            self.spectra_1d.observe(self._update_plot, names="value")
            self.split_1d.observe(self._update_plot, names="value")
            self.spectra_2d.observe(self._update_plot, names="value")
            self.split_2d.observe(self._update_plot, names="value")
            self.patch_2d.options = self.patches.keys()
            self.patch_2d.observe(self._update_plot, names="value")

            self._update_plot(None)

        self.compute_button.description = "Compute spectra"
        self.compute_button.icon = "check"
        self.compute_button.disabled = False
        self.clean_button.disabled = False

    def _update_plot(self, _):
        if self.compute_1d.value:
            self._update_1d_plot()
        if self.compute_2d.value:
            self._update_2d_plot()

    def _update_1d_plot(self):
        split_name = self.split_1d.value
        spec = self.spectra_1d.value

        # Clean data
        self.fig_1d.data = []

        # Update theory & data
        for name, patch in self.patches.items():
            method = patch.get("master", dict())
            results = method.get("results")
            if not results:
                continue
            x = results.get("lb")
            y = results.get("ps").get(split_name).get(spec)
            yerr = np.sqrt(np.diag(results.get("cov").get(split_name).get(spec)))
            self.fig_1d.add_scatter(
                name=name,
                x=x,
                y=y,
                error_y=dict(type="data", array=yerr, visible=True),
                mode="markers",
            )
        self.fig_1d.add_scatter(
            name="theory",
            x=self.theory.get("lth")[: self.lmax.value],
            y=self.theory.get("clth")[self.spectra_1d.value][: self.lmax.value],
            mode="lines",
            line=dict(color="gray"),
        )

        yaxis_title = r"$D_\ell^\mathrm{%s}$" % spec
        updatemenus = list(
            [
                dict(
                    active=0,
                    type="buttons",
                    buttons=list(
                        [
                            dict(
                                label="Linear Scale",
                                method="update",
                                args=[
                                    {"visible": [True] * len(self.fig_1d.data)},
                                    {"yaxis": {"title": yaxis_title, "type": "linear"}},
                                ],
                            ),
                            dict(
                                label="Log Scale",
                                method="update",
                                args=[
                                    {"visible": [True] * len(self.fig_1d.data)},
                                    {"yaxis": {"title": yaxis_title, "type": "log"}},
                                ],
                            ),
                        ]
                    ),
                    direction="right",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=1.0,
                    xanchor="right",
                    y=1.1,
                    yanchor="top",
                )
            ]
        )
        layout = dict(
            updatemenus=updatemenus,
            autosize=True,
            title=split_name,
            xaxis_title=r"$\ell$",
            yaxis_title=yaxis_title,
        )
        try:
            self.fig_1d.update_layout(layout)
        except ValueError:
            # Do not know what's going on : an exception is raised by the graphical
            # representation works well so skip it for the time being
            print("Exception raised from 'update_layout'")
            pass

    def _update_2d_plot(self):
        split_name = self.split_2d.value
        spec = self.spectra_2d.value
        patch_name = self.patch_2d.value
        method = self.patches[patch_name].get("2dflat")
        if not method:
            return
        results = method.get("results")
        if not results:
            return
        p2d = results.get("ps").get(split_name)
        powermap = np.fft.fftshift(p2d.powermap[spec].copy())
        shape = powermap.shape
        x = np.linspace(np.min(p2d.lx), np.max(p2d.lx), shape[1])
        y = np.linspace(np.min(p2d.ly), np.max(p2d.ly), shape[0])

        from plotly.colors import qualitative

        # Clean data
        self.fig_2d.data = []
        self.fig_2d.add_heatmap(x=x, y=y, z=powermap, colorscale=default_colorscale)

        # Create slider and buttons
        zmin, zmax = np.min(powermap), np.max(powermap)
        steps = []
        for scale in np.arange(0, 1.1, 0.1):
            step = dict(
                label="{:0.1f}".format(scale),
                method="restyle",
                args=[
                    dict(
                        zmin=scale * zmin, zmax=scale * zmax, cmin=scale * zmin, cmax=scale * zmax,
                    )
                ],
            )
            steps.append(step)

        sliders = [
            dict(
                len=0.5,
                active=len(steps) - 1,
                currentvalue={"prefix": "z-scale: "},
                x=0.25,
                pad={"t": 50},
                steps=steps,
            )
        ]
        updatemenus = list(
            [
                dict(
                    active=0,
                    buttons=list(
                        [
                            dict(label="2D", method="restyle", args=["type", "heatmap"],),
                            dict(label="3D", method="restyle", args=["type", "surface"],),
                        ]
                    ),
                    direction="down",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=1.0,
                    xanchor="right",
                    y=1.15,
                    yanchor="top",
                )
            ]
        )
        layout = dict(
            updatemenus=updatemenus,
            sliders=sliders,
            autosize=True,
            # width=self.fig_2d.layout.height,
            title=dict(
                text="{} - {}".format(split_name, patch_name),
                font=dict(color=qualitative.Plotly[list(self.patches).index(patch_name)]),
            ),
            xaxis=dict(
                title=r"$\ell_X$",
                showgrid=False,
                zeroline=False,
                range=[-self.lmax.value, +self.lmax.value],
                constrain="domain",
            ),
            yaxis=dict(
                title=r"$\ell_Y$",
                scaleanchor="x",
                scaleratio=1,
                showgrid=False,
                zeroline=False,
                range=[-self.lmax.value, +self.lmax.value],
            ),
        )
        self.fig_2d.update_layout(layout)
