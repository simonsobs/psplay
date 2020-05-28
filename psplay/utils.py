from copy import deepcopy
from itertools import product

import matplotlib.pyplot as plt
import numpy as np

from pixell import colorize

from . import pstools

colorize.mpl_setdefault("planck")

# Default SO attribution for tiles
so_attribution = '&copy; <a href="https://simonsobservatory.org/">Simons Observatory</a>'


def get_tiles(layers):
    """ Fonction that converts a dictionary into a complete list of tiles """

    keybindings = {}
    tiles = []

    for ilayer, layer in enumerate(layers):
        # name = str(*layer.keys())
        layer = dict(*layer.values())

        overlay = layer.get("overlay", False)
        opacity = layer.get("opacity", 0.5 if overlay else 1.0)
        # Add keybindings to change opacity or layer level
        if overlay:
            keybindings.update(dict(opacity=["o", "p"], overlay=["m"]))
        else:
            keybindings.update({"layer": dict(keys=["n"], level=0, depth=ilayer)})

        # Colormap
        scale_amplitude = layer.get("colorscale", {}).get("amplitude", 0.1)
        block = layer.get("colormap", {})
        colormap = block.get("name", "hotcold" if overlay else "planck")
        if block.get("keybindings"):
            keybindings.update({"colormap": block.get("keybindings")})

        # Set color range
        vrange = [[-500, +500], [-100, +100], [-100, +100]]
        _range = layer.get("range")
        if _range:
            _val = _range.get("temperature")
            vrange[0] = [-_val, +_val] if _val else vrange[0]
            _val = _range.get("polarization")
            vrange[1] = [-_val, +_val] if _val else vrange[1]
            vrange[2] = vrange[1] if _val else vrange[2]
        for i, j in enumerate(["min", "max"]):
            _m = layer.get(j)
            if _m:
                _val = _m.get("temperature")
                vrange[0][i] = _val if _val is not None else vrange[0][i]
                _val = _m.get("polarization")
                vrange[1][i] = _val if _val is not None else vrange[1][i]
                vrange[2][i] = vrange[1][i] if _val is not None else vrange[2][i]

        tags = layer.get("tags", {})
        path = layer.get("path", "files/")
        tile_tmpl = layer.get("tile", "")
        name_tmpl = layer.get("name", "")

        tile_dict = dict(path=path, x="{x}", y="{y}", z="{z}")
        name_dict = dict()

        tile_config = dict(
            base=not overlay,
            opacity=opacity,
            url=tile_tmpl,
            name=name_tmpl,
            attribution=name_tmpl,
            value_min=vrange[0][0],  # if not overlay else 1,
            value_max=vrange[0][1],  # if not overlay else 0,
            colormap=colormap,
            scale_amplitude=scale_amplitude,
            tag_id=ilayer,
        )

        if not tags:
            tiles += [tile_config]
        else:
            # Grab keybindings
            for i, (k, v) in enumerate(tags.items()):
                if "keybindings" not in v:
                    raise ValueError("Missing 'keybindings' for '{}' tag".format(k))
                keybindings.update(
                    {
                        k: dict(
                            keys=v.get("keybindings"),
                            level=i + 1,
                            depth=len(v.get("values") or []),
                        )
                    }
                )

            # Generate all combinations
            values = [value.get("values") for value in tags.values()]
            for value in product(*values):
                tag_id = 0
                for i, v in enumerate(value):
                    key = list(tags.keys())[i]
                    tag = tags.get(key)
                    idx = tag.get("values").index(v)
                    tag_id += idx * 10 ** (i + 1)

                    tile_dict.update({key: v})
                    name_dict.update({key: v})
                    if tag.get("substitutes"):
                        name_dict.update({key: tag.get("substitutes")[idx]})

                # Hardcode temperature vs. polarization range
                value_min, value_max = vrange[0] if "T" in name_dict.values() else vrange[1]
                updated_config = deepcopy(tile_config)
                updated_config.update(
                    dict(
                        tag_id=tag_id,
                        url=tile_tmpl.format(**tile_dict),
                        name=name_tmpl.format(**name_dict),
                        attribution=name_tmpl.format(**name_dict),
                        value_min=value_min,
                        value_max=value_max,
                    )
                )
                tiles += [updated_config]

    # Remove layer keybindings if only one
    if keybindings.get("layer", {}).get("depth", 0) == 0:
        del keybindings["layer"]
    return tiles, keybindings


def build_patch_geometry(patch):
    def parse_rectangle(coordinates):
        return [coordinates[0][0][::-1], coordinates[0][2][::-1]]

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
        print("Shape '{}' not supported".format(geometry))

    return patch_dict


def build_polygon_geometry(patch, increment=0):
    geometry = patch.get("geometry")
    if geometry.get("type") == "Polygon":
        coordinates = geometry.get("coordinates")
        y = [y[0] for y in coordinates[0]]
        x = [x[1] for x in coordinates[0]]
        xc = np.mean([x[0], x[1]])
        yc = np.mean([y[-1], y[-2]])
        x = [x + np.sign(x - xc) * increment for x in x]
        y = [y + np.sign(y - yc) * increment for y in y]
        return list(zip(x, y))


def check_beam(app):
    l, bl = np.loadtxt(app.plot_config.get("beam_file"), unpack=True)
    plt.plot(l, bl)
    plt.xlabel(r"$\ell$")
    plt.ylabel(r"$b_\ell$")


def check_window(app):
    npatches = len(app.patches)
    fig, axes = plt.subplots((npatches + 1) // 2, 2)
    if npatches % 2:
        fig.delaxes(*axes.flat[npatches:])
    for ipatch, (name, patch) in enumerate(app.patches.items()):
        patch_geometry = build_patch_geometry(patch)
        car_box, window = pstools.create_window(
            patch_geometry,
            app.maps_info_list,
            source_mask=app.masks_info_list.get("source"),
            galactic_mask=app.masks_info_list.get("galactic"),
        )
        ax = axes.flat[ipatch]
        extent = [car_box[1][1], car_box[0][1], car_box[0][0], car_box[1][0]]
        ax.imshow(window.data[::-1, ::-1], extent=extent, vmin=-1, vmax=+1)
        ax.set_xlabel("RA [°]")
        ax.set_ylabel("DEC [°]")
