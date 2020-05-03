const L = require('../leaflet-car.js');
const control = require('jupyter-leaflet');

var keybindings = {};

var cache = {};
L.Map.include({
    _updateColors: function (e, layer) {
        if (layer.options && "colormap" in layer.options) {
            if (keybindings["colormap"].includes(e.key)) {
                console.log("Colormap 1");
                var colormap = layer.options.colormap;
                var colormaps = Object.keys(L.ColorizableUtils.colormaps);
                for (var i = 0; i < colormaps.length; i++) {
                    if (colormap === colormaps[i]) {
                        layer.options.colormap = colormaps[(i+1) % colormaps.length];
                        break;
                    }
                }
            } else if (keybindings["scale"][0] == e.key) {
                console.log("increase color");
                var scale = layer.options.scale;
                layer.options.scale *= 1.1;
            } else if (keybindings["scale"][1] == e.key) {
                console.log("decrease color");
                var scale = layer.options.scale;
                layer.options.scale /= 1.1;
            }
        }
    },
    baseFireDOMEvent: L.Map.prototype._fireDOMEvent,
    _fireDOMEvent: function (e, type, targets) {
        if (e.type === 'keypress') {

            var keys = [].concat.apply([], Object.values(keybindings));
            if (! keys.includes(e.key)) {
                console.log("Key not recognized");
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            console.log("Overload fireDOM: key press");
            console.log("e.key =", e.key);
            console.log("type =", type)

            if ("cache" in keybindings && keybindings["cache"].includes(e.key)) {
                console.log("Clean cache");
                cache.data = {};
                return;
            }

            // Find the layer the event is propagating from and its parents.
	    targets = (targets || []).concat(this._findEventTargets(e, type));

	    if (!targets.length) { return; }
            var layers = targets[0]._layers;

            if (("colormap" in keybindings && keybindings["colormap"].includes(e.key)) ||
                ("scale" in keybindings && keybindings["scale"].includes(e.key))) {
                if (this.layer_groups) {
                    console.log("Update color");
                    for (var key in this.layer_groups) {
                        for (var i = 0; i < this.layer_groups[key].length; i++) {
                            this._updateColors(e, this.layer_groups[key][i]);
                        }
                    }
                }
                // Update current layer
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "tag" in layer.options) {
                        layer._updateTiles();
                    }
                }
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            // Look into tag field
            if ("layer" in keybindings && keybindings["layer"].includes(e.key)) {
                console.log("Change layer");
                // Update current layer
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "tag" in layer.options && "tagId" in layer.options) {
                        var tag = layer.options.tag;
                        var tagId = layer.options.tagId;
                        if (e.key == keybindings["layer"][0])
                            tagId = (tagId + 1) % this.layer_groups[tag].length;
                        if (e.key == keybindings["layer"][1])
                            tagId = (tagId - 1) % this.layer_groups[tag].length;

                        if (tagId == -1) tagId += this.layer_groups[tag].length;
                        this.addLayer(this.layer_groups[tag][tagId]);
                    }
                }
            }
        }
        // Apply base DOMEvent
        this.baseFireDOMEvent(e, type, targets);

    },
    removeAllLayers: function() {
        var map = this;
        this.eachLayer(function(layer) {
            if (layer.options && "tag" in layer.options) {
                map.removeLayer(layer);
            }
        });
    },
    baseAddLayer: L.Map.prototype.addLayer,
    addLayer: function (layer) {
        console.log("Add layer");

        if (!("layer_groups" in this))
	    this.layer_groups = {};

        if (layer.options && "tag" in layer.options) {
            var tag = layer.options.tag;
            console.log("Layer tag", tag);

            if (!(tag in this.layer_groups)) {
                this.layer_groups[tag] = [];
            }

            var tagId = this.layer_groups[tag].length;
            if (!("tagId" in layer.options)) {
                layer.options.tagId = tagId;
                this.layer_groups[tag].push(layer);
                layer.setCache(cache);
                if (tagId == 0)
                    this.baseAddLayer(layer);
            } else {
                // First remove all layers from map
                this.removeAllLayers();
                this.baseAddLayer(layer);
            }
        } else {
            // Anything else (graticule for instance)
            this.baseAddLayer(layer);
        }
        this.fire("recolor");
    },

});

export class LeafletKeyBindingControlModel extends control.LeafletControlModel {
    defaults() {
        return {
            ...super.defaults(),
            _view_name: 'LeafletKeyBindingControlView',
            _model_name: 'LeafletKeyBindingControlModel',
            _view_module: 'jupyter-leaflet-car',
            _model_module: 'jupyter-leaflet-car',
        };
    }
}

export class LeafletKeyBindingControlView extends control.LeafletControlView {
    initialize(parameters) {
        super.initialize(parameters);
        keybindings = this.get_options()["keybindings"];
    }

    create_obj() {
    }
}
