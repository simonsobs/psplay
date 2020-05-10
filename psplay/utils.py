from itertools import product

import matplotlib.pyplot as plt
import numpy as np

from . import ps_tools


def get_tiles(layers):
    """ Fonction that converts a dictionary into a complete list of tiles """

    # Set color range
    vrange = [[-500, +500], [-100, +100], [-100, +100]]
    _range = layers.get("range")
    if _range:
        _val = _range.get("temperature")
        vrange[0] = [-_val, +_val] if _val else vrange[0]
        _val = _range.get("polarization")
        vrange[1] = [-_val, +_val] if _val else vrange[1]
        vrange[2] = vrange[1] if _val else vrange[2]
    for i, j in enumerate(["min", "max"]):
        _m = layers.get(j)
        if _m:
            _val = _m.get("temperature")
            vrange[0][i] = _val if _val is not None else vrange[0][i]
            _val = _m.get("polarization")
            vrange[1][i] = _val if _val is not None else vrange[1][i]
            vrange[2][i] = vrange[1][i] if _val is not None else vrange[2][i]

    tags = layers.get("tags")
    path = layers.get("path", "files/")
    tile_tmpl = layers.get("tile_tmpl", "")
    name_tmpl = layers.get("name_tmpl", "")

    tile_dict = dict(x="{x}", y="{y}", z="{z}", path=path)
    name_dict = dict()

    if not tags:
        return [
            dict(
                tag_id=0,
                url=tile_tmpl,
                name=name_tmpl,
                attribution="",
                value_min=vrange[0][0],
                value_max=vrange[0][1],
            )
        ]

    tiles = []
    keys = list(tags.keys())
    values = [value.get("values") for value in tags.values()]
    for value in product(*values):
        tag_id = 0
        for i, v in enumerate(value):
            tag = tags.get(keys[i])
            idx = tag.get("values").index(v)
            tag_id += idx * 10 ** i

            tile_dict.update({keys[i]: v})
            name_dict.update({keys[i]: v})
            if tag.get("substitutes"):
                name_dict.update({keys[i]: tag.get("substitutes")[idx]})

        url = tile_tmpl.format(**tile_dict)
        name = name_tmpl.format(**name_dict)
        # Hardcode temperature vs. polarization range
        value_min, value_max = vrange[0] if "T" in name_dict.values() else vrange[1]
        tiles += [
            dict(
                tag_id=tag_id,
                url=url,
                name=name,
                attribution=name,
                value_min=value_min,
                value_max=value_max,
            )
        ]

    return tiles


def get_keybindings(layers):
    keybindings = {}
    keybindings.update(
        {k: v.get("keybindings") for k, v in layers.items() if "keybindings" in v and k != "tags"}
    )
    tags = layers.get("tags", {})
    keybindings.update(
        {
            k: dict(keys=v.get("keybindings"), level=i, depth=len(v.get("values")))
            for i, (k, v) in enumerate(tags.items())
        }
    )
    return keybindings


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


def check_beam(beam_file):
    l, bl = np.loadtxt(beam_file, unpack=True)
    plt.plot(l, bl)
    plt.xlabel(r"$\ell$")
    plt.ylabel(r"$b_\ell$")


def check_window(maps, patches):
    npatches = len(patches)
    fig, axes = plt.subplots(npatches // 2, npatches // 2)
    for ipatch, (name, patch) in enumerate(patches.items()):
        patch_geometry = build_patch_geometry(patch)
        car_box, window = ps_tools.create_window(patch_geometry, maps)
        axes[ipatch // 2, ipatch % 2].imshow(window.data)
