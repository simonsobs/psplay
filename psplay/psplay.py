# Copyright (c) Simons Observatory.
# Distributed under the terms of the Modified BSD License.
#
import os
import pickle
import time
from copy import deepcopy

import ipywidgets as widgets
import numpy as np
import yaml

import plotly.graph_objects as go
from ipyleaflet import (DrawControl, FullScreenControl, Map, MapStyle, Polygon,
                        WidgetControl)

from . import utils
from ._leaflet import (Circle, ColorizableTileLayer, Graticule,
                       KeyBindingControl, LayersControl, StatusBarControl,
                       allowed_colormaps)
from .pstools import compute_ps


# Generate default plotly colormap based on planck colormap
def generate_default_colorscale(default="planck"):
    from pixell import colorize

    cs = colorize.schemes[default]
    return [[val, "rgb({},{},{})".format(*cols)] for val, cols in zip(cs.vals, cs.cols)]


default_colorscale = generate_default_colorscale()

# Output widget to catch functions/programs output into a widget
out = widgets.Output()


def _get_section(section, name):
    # Python 3.8 if not value := section.get(name):
    value = section.get(name)
    if not value:
        raise ValueError("Missing '{}' section".format(name))
    return value


class App:
    """ An ipywidgets and plotly application for CMB map and power spectra visualization"""

    def __init__(self, config):
        if isinstance(config, dict):
            self.config = config
        else:
            with open(config, "r") as stream:
                self.config = yaml.load(stream, Loader=yaml.FullLoader)

        self.map_config = _get_section(self.config, "map")
        self.data_config = _get_section(self.config, "data")
        self.plot_config = self.config.get("plot", {})

        self.m = None
        self.p = None
        self.patches = dict()

        self.layers = [Graticule()]
        self._add_layers()
        self._add_map()
        self._add_compute()
        self._add_plot()
        self._add_theory()

    def show_map(self):
        if self.map_config.get("use_sidecar", True):
            from sidecar import Sidecar
            from IPython.display import display

            sc = Sidecar(title=self.map_config.get("title", "CMB map"))
            with sc:
                display(self.m)
        else:
            return self.m

    def show_plot(self):
        return self.p

    def _add_layers(self):
        layers = self.map_config.get("layers", {})
        tile_default = dict(
            min_zoom=self.map_config.get("min_zoom", -5),
            max_zoom=self.map_config.get("max_zoom", +5),
            min_native_zoom=self.map_config.get("min_native_zoom", -5),
            max_native_zoom=self.map_config.get("max_native_zoom", 0),
            tile_size=self.map_config.get("tile_size", 675),
            show_loading=self.map_config.get("show_loading", True),
        )
        self.tiles, self.keybindings = utils.get_tiles(layers)
        for tile in self.tiles:
            tile_config = deepcopy(tile_default)
            tile_config.update(**tile)
            self.layers.append(ColorizableTileLayer(**tile_config))

    def _add_map(self):
        default_keybindings = dict(colormap=["g"], colorscale=["u", "i"], cache=["z"])
        default_keybindings.update(self.keybindings)
        self.m = Map(
            layers=self.layers,
            controls=(
                FullScreenControl(),
                StatusBarControl(),
                KeyBindingControl(keybindings=default_keybindings),
            ),
            crs=dict(name="CAR", custom=False),
            center=self.map_config.get("center", (0, 0)),
            min_zoom=self.map_config.get("min_zoom", -5),
            max_zoom=self.map_config.get("max_zoom", +5),
            zoom=self.map_config.get("initial_zoom", 0),
            interpolation="nearest",
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
        self.draw_control.edit = True
        self.draw_control.remove = True

        patches = self.patches

        def handle_draw(self, action, geo_json):
            patch_id = geo_json.get("properties", {}).get("style", {}).get("id", None)
            if not patch_id:
                raise ValueError("Missing patch id from GeoJSON!")
            if action in ["created", "edited"]:
                patches[patch_id] = geo_json
                patches[patch_id].update({"results": None, "buffer": None})
                if action == "edited":
                    # Reset buffers for all patches
                    for patch in patches.values():
                        patch.update({"buffer": None})
            if action == "deleted":
                del patches[patch_id]

        self.draw_control.on_draw(handle_draw)
        self.m.add_control(self.draw_control)

        widgets_config = self.map_config.get("widgets", {})
        if widgets_config.get("use_layer_control", False):
            self.m.add_control(LayersControl(position="bottomleft", collapsed=False))

        if widgets_config.get("use_scale_control", False):
            scale = widgets.FloatSlider(
                value=1.0,
                min=0,
                max=2.0,
                step=0.01,
                description="Scale",
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

        if widgets_config.get("use_cmap_control", False):
            cmap = widgets.RadioButtons(
                options=allowed_colormaps, value="planck", layout=widgets.Layout(width="100px"),
            )

            def on_cmap_change(change):
                for layer in self.layers:
                    layer.colormap = change["new"]

            cmap.observe(on_cmap_change, names="value")
            self.m.add_control(WidgetControl(widget=cmap, position="bottomright"))

        if widgets_config.get("use_buffer_control", False):
            buffer_size = widgets.FloatSlider(
                description="Buffer (deg.)", min=0, max=10, step=0.1, readout_format=".1f"
            )

            def on_buffer_size_change(change):
                for name, patch in self.patches.items():
                    geometry = utils.build_patch_geometry(patch)
                    buffer = patch.get("buffer")
                    if not buffer:
                        # Create buffer
                        if geometry["patch_type"] == "Disk":
                            shape = Circle(
                                location=geometry["center"],
                                dash_array="1, 10",
                                fill=False,
                                radius=geometry["radius"],
                            )
                        if geometry["patch_type"] == "Rectangle":
                            # Use Polygon instead of Rectangle shape since locations are sync and
                            # not Rectangle bounds
                            shape = Polygon(
                                locations=utils.build_polygon_geometry(patch),
                                dash_array="1, 10",
                                fill=False,
                            )
                        self.m.add_layer(shape)
                        shape.color = patch.get("properties").get("style").get("color")
                        patch.update({"buffer": shape})
                    else:
                        if isinstance(buffer, Circle):
                            buffer.radius = geometry["radius"] + change["new"]
                            buffer.location = geometry["center"]
                        if isinstance(buffer, Polygon):
                            buffer.locations = utils.build_polygon_geometry(patch, change["new"])
                        patch.update({"buffer_size": change["new"]})

            buffer_size.observe(on_buffer_size_change, names="value")
            self.m.add_control(WidgetControl(widget=buffer_size, position="bottomright"))

    def _add_compute(self):
        # Store original fits map
        self.maps_info_list = list()
        for imap in self.data_config.get("maps", []):
            self.maps_info_list.append(
                dict(
                    id=_get_section(imap, "id"),
                    name=_get_section(imap, "file"),
                    data_type=imap.get("data_type", "IQU"),
                    cal=None,
                )
            )

        self.masks_info_list = dict()
        for imask in self.data_config.get("masks", []):
            mask_info = dict(name=_get_section(imask, "file"))
            apodization = imask.get("apodization")
            if apodization:
                mask_info.update(
                    dict(
                        apo_type=apodization.get("type", "C1"),
                        apo_radius=apodization.get("radius", 0.3),
                    )
                )
            self.masks_info_list[_get_section(imask, "type")] = mask_info

    def _add_theory(self):
        self.theory = None
        theory_file = self.data_config.get(
            "theory_file", "bode_almost_wmap5_lmax_1e4_lensedCls_startAt2.dat"
        )
        if os.path.exists(theory_file):
            clth = {}
            lth, clth["TT"], clth["EE"], clth["BB"], clth["TE"] = np.loadtxt(
                theory_file, unpack=True,
            )
            clth["ET"] = clth["TE"]
            for spec in ["EB", "BE", "BT", "TB"]:
                clth[spec] = np.zeros(clth["TE"].shape)
            self.theory = {"lth": lth, "clth": clth}

    def _add_plot(self):
        # Main
        self.tab = widgets.Tab()
        self.tab.children = [self._add_1d_plot(), self._add_2d_plot()]
        self.tab.set_title(0, "1D power spectra")
        self.tab.set_title(1, "2D power spectra")

        # General configuration
        layout = widgets.Layout(width="auto", height="auto")
        self.compute_1d = widgets.Checkbox(
            value=self.plot_config.get("compute_1d", True), description="1D spectra", layout=layout
        )
        self.compute_2d = widgets.Checkbox(
            value=self.plot_config.get("compute_2d", True), description="2D spectra", layout=layout
        )
        self.compute_T_only = widgets.Checkbox(
            value=False, description="Only temperature", layout=layout
        )
        self.lmax = widgets.IntSlider(
            value=self.plot_config.get("lmax", 1000),
            min=0,
            max=10000,
            step=100,
            description=r"$\ell_\mathrm{max}$",
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
        self.export_button = widgets.Button(description="Export results", icon="download")

        def _clean_patches(_):
            # Clean buffer if any
            for name, patch in self.patches.items():
                if "buffer" in patch and patch["buffer"] is not None:
                    self.m.remove_layer(patch["buffer"])
            self.patches.clear()
            self.draw_control.clear()
            self.clean_button.description = "Clean patches ({})".format(len(self.patches))

        @out.capture()
        def _export_results(_):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            export_file = os.path.join(
                self.plot_config.get("export_directory", "/tmp"),
                "psplay_results_{}.pkl".format(timestamp),
            )
            # Remove buffer primitives
            for patch in self.patches.values():
                if "buffer" in patch:
                    del patch["buffer"]
            pickle.dump(self.patches, open(export_file, "wb"))
            print("Results exported in '{}'".format(export_file))

        self.compute_button.on_click(self._compute_spectra)
        self.clean_button.on_click(_clean_patches)
        self.export_button.on_click(_export_results)
        self.p = widgets.VBox(
            [
                self.tab,
                accordion,
                widgets.HBox([self.clean_button, self.export_button, self.compute_button]),
            ]
        )

    def _add_1d_plot(self):
        # Figure widget
        plotly_config = self.plot_config.get("plotly", dict())

        self.fig_1d = go.FigureWidget(
            layout=go.Layout(height=600, template=plotly_config.get("template", "plotly_white"))
        )
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
                                args=[{"visible": [True] * 100}, {"yaxis": {"type": "linear"}},],
                            ),
                            dict(
                                label="Log Scale",
                                method="update",
                                args=[{"visible": [True] * 100}, {"yaxis": {"type": "log"}},],
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
        layout = dict(updatemenus=updatemenus, autosize=True, xaxis_title=r"$\ell$")
        self.fig_1d.update_layout(layout)

        # Header
        allowed_spectra = ["TT", "TE", "TB", "ET", "BT", "EE", "EB", "BE", "BB"]
        self.spectra_1d = widgets.Dropdown(description="Spectra:", options=allowed_spectra)
        self.split_1d = widgets.Dropdown(description="Split:")
        header = widgets.HBox([self.spectra_1d, self.split_1d])

        # Config
        self.use_toeplitz = widgets.Checkbox(value=False, description="Use Toeplitz approx.")
        self.bin_size = widgets.IntSlider(
            value=self.plot_config.get("bin_size", 40),
            min=0,
            max=200,
            step=10,
            description="Bin size",
        )
        config = widgets.HBox([widgets.VBox([self.use_toeplitz])])
        if not self.data_config.get("binning_file"):
            config.children += (widgets.VBox([self.bin_size]),)
        accordion = widgets.Accordion(children=[config], selected_index=None)
        accordion.set_title(0, "Parameters")

        return widgets.VBox([header, self.fig_1d, accordion])

    def _add_2d_plot(self):
        # Figure widget
        plotly_config = self.plot_config.get("plotly", {})

        self.fig_2d = go.FigureWidget(
            layout=go.Layout(height=600, template=plotly_config.get("template", "plotly_white"))
        )
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
            # sliders=sliders,
            autosize=True,
            # width=self.fig_2d.layout.height,
            xaxis=dict(title=r"$\ell_X$", showgrid=False, zeroline=False, constrain="domain",),
            yaxis=dict(
                title=r"$\ell_Y$", scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False,
            ),
        )
        self.fig_2d.update_layout(layout)

        # Header
        allowed_spectra = ["II", "IQ", "IU", "QI", "QQ", "QU", "UI", "UQ", "UU"]
        self.spectra_2d = widgets.Dropdown(description="Spectra:", options=allowed_spectra)
        self.split_2d = widgets.Dropdown(description="Split:")
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
        self.export_button.disabled = True
        self.clean_button.description = "Clean patches ({})".format(len(self.patches))

        for ps_method, compute in zip(
            ["master", "2dflat"], [self.compute_1d.value, self.compute_2d.value]
        ):
            if not compute:
                continue
            for ipatch, (name, patch) in enumerate(self.patches.items()):
                print("Compute patch #{} for '{}' method".format(ipatch, ps_method))

                kwargs = dict(ps_method=ps_method, lmax=self.lmax.value,)
                if ps_method == "master":
                    kwargs.update(
                        dict(
                            error_method="master",
                            binning_file=self.data_config.get("binning_file"),
                            bin_size=self.bin_size.value,
                            beam_file=self.data_config.get("beam_file"),
                            source_mask=self.masks_info_list.get("source"),
                            galactic_mask=self.masks_info_list.get("galactic"),
                            compute_T_only=self.compute_T_only.value,
                            l_exact=800 if self.use_toeplitz.value else None,
                            l_band=2000 if self.use_toeplitz.value else None,
                            l_toep=2500 if self.use_toeplitz.value else None,
                        )
                    )

                method = patch.get(ps_method, dict())
                if method.get("results") and method.get("config") == kwargs:
                    print("Patch already processed under the same condition")
                    spectra, spec_name_list, lb, ps_dict, cov_dict = method.get("results").values()
                    continue

                try:
                    patch_dict = utils.build_patch_geometry(patch)
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
                except Exception as e:
                    print("An error occured during computation of power spectra : ", str(e))

            if spectra is not None:
                if ps_method == "master":
                    self.spectra_1d.options = spectra
                    self.split_1d.options = spec_name_list
                if ps_method == "2dflat":
                    self.spectra_2d.options = spectra
                    self.split_2d.options = spec_name_list

        if spectra is not None:
            self.spectra_1d.observe(self._update_1d_plot, names="value")
            self.split_1d.observe(self._update_1d_plot, names="value")
            self.spectra_2d.observe(self._update_2d_plot, names="value")
            self.split_2d.observe(self._update_2d_plot, names="value")
            self.patch_2d.options = self.patches.keys()
            self.patch_2d.observe(self._update_2d_plot, names="value")

            self._update_1d_plot(None, create=True)
            self._update_2d_plot(None, create=True)

        self.compute_button.description = "Compute spectra"
        self.compute_button.icon = "check"
        self.compute_button.disabled = False
        self.clean_button.disabled = False
        self.export_button.disabled = False

    def _update_1d_plot(self, _, create=False):
        split_name = self.split_1d.value
        spec = self.spectra_1d.value

        if create:
            # Clean data
            self.fig_1d.data = []

        # Update theory & data
        ipatch = 0
        for name, patch in self.patches.items():
            method = patch.get("master", dict())
            results = method.get("results")
            if not results:
                continue
            # Get the correct color given patch id
            color = patch.get("properties").get("style").get("color")
            x = results.get("lb")
            y = results.get("ps").get(split_name).get(spec)
            yerr = np.sqrt(np.diag(results.get("cov").get(split_name).get(spec)))
            if create:
                self.fig_1d.add_scatter(
                    name=name,
                    x=x,
                    y=y,
                    error_y=dict(type="data", array=yerr, visible=True, color=color),
                    mode="markers",
                    marker=dict(color=color),
                )
            else:
                with self.fig_1d.batch_update():
                    self.fig_1d.data[ipatch].x = x
                    self.fig_1d.data[ipatch].y = y
                    self.fig_1d.data[ipatch].error_y.array = yerr
                ipatch += 1

        if self.theory is not None:
            x = self.theory.get("lth")[: self.lmax.value]
            y = self.theory.get("clth")[self.spectra_1d.value][: self.lmax.value]
            if create:
                self.fig_1d.add_scatter(
                    name="theory", x=x, y=y, mode="lines", line=dict(color="gray"),
                )
            else:
                with self.fig_1d.batch_update():
                    self.fig_1d.data[-1].x = x
                    self.fig_1d.data[-1].y = y

        with self.fig_1d.batch_update():
            self.fig_1d.layout.title = split_name
            self.fig_1d.layout.yaxis.title = r"$D_\ell^\mathrm{%s}$" % spec

    def _update_2d_plot(self, _, create=False):
        split_name = self.split_2d.value
        spec = self.spectra_2d.value
        patch_name = self.patch_2d.value
        method = self.patches[patch_name].get("2dflat", dict())
        results = method.get("results")
        if not results:
            return
        p2d = results.get("ps").get(split_name)
        powermap = np.fft.fftshift(p2d.powermap[spec].copy())
        shape = powermap.shape
        x = np.linspace(np.min(p2d.lx), np.max(p2d.lx), shape[1])
        y = np.linspace(np.min(p2d.ly), np.max(p2d.ly), shape[0])

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

        if create:
            # Clean data
            self.fig_2d.data = []
            self.fig_2d.add_heatmap(x=x, y=y, z=powermap, colorscale=default_colorscale)
        else:
            with self.fig_2d.batch_update():
                self.fig_2d.data[0].x = x
                self.fig_2d.data[0].y = y
                self.fig_2d.data[0].z = powermap
                self.fig_2d.data[0].zmin = zmin
                self.fig_2d.data[0].zmax = zmax

        with self.fig_2d.batch_update():
            self.fig_2d.layout.sliders = sliders
            self.fig_2d.layout.title.text = "{} - {}".format(split_name, patch_name)
            self.fig_2d.layout.title.font.color = (
                self.patches[patch_name].get("properties").get("style").get("color")
            )
            self.fig_2d.layout.xaxis.range = [-self.lmax.value, +self.lmax.value]
            self.fig_2d.layout.yaxis.range = [-self.lmax.value, +self.lmax.value]
        self.fig_2d.update_traces()
