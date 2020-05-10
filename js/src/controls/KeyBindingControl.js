const L = require('../leaflet-car.js');
const control = require('jupyter-leaflet');

var keybindings = {};
var all_keys = [];

var cache = {};
L.Map.include({
    _updateColors: function (e, layer) {
        if (layer.options && "colormap" in layer.options) {
            if (keybindings["colormap"].includes(e.key)) {
                console.log("Change colormap");
                var colormap = layer.options.colormap;
                var colormaps = Object.keys(L.ColorizableUtils.colormaps);
                for (var i = 0; i < colormaps.length; i++) {
                    if (colormap === colormaps[i]) {
                        layer.options.colormap = colormaps[(i+1) % colormaps.length];
                        break;
                    }
                }
            } else {
                console.log("Change color scale");
                for (var i = 0; i < keybindings["colorscale"].length; i++) {
                    if (e.key == keybindings["colorscale"][i])
                        layer.options.scale *= Math.pow(1. + layer.options.scaleAmplitude, 2*i-1);
                }
            }
        }
    },
    baseFireDOMEvent: L.Map.prototype._fireDOMEvent,
    _fireDOMEvent: function (e, type, targets) {
        if (e.type === 'keypress') {

            // Initialize all keys
            if (all_keys.length == 0) {
                for (var key in keybindings) {
                    var keys = keybindings[key];
                    if (keys.length == undefined)
                        keys = keys.keys;
                    for (var i = 0; i < keys.length; i++)
                        all_keys.push(keys[i]);
                }
                console.log("all keys =", all_keys);
            }

            if (! all_keys.includes(e.key)) {
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
                ("colorscale" in keybindings && keybindings["colorscale"].includes(e.key))) {
                if (this.layer_groups) {
                    console.log("Update color");
                    for (var key in this.layer_groups) {
                        this._updateColors(e, this.layer_groups[key]);
                    }
                }
                // Update current layer
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "tagId" in layer.options) {
                        layer._updateTiles();
                    }
                }
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            for (var key in layers) {
                var layer = layers[key];
                if (layer.options && "tagId" in layer.options) {
                    var found = false;
                    for (var key in keybindings) {
                        var keys = keybindings[key];
                        if (keys.length != undefined) continue;
                        keys = keys.keys;
                        for (var i = 0; i < keys.length; i++) {
                            if (e.key == keys[i]) {
                                var tagId = layer.options.tagId;
                                tagId += (2*i-1) * Math.pow(10, keybindings[key].level);
                                if (!(tagId in this.layer_groups)) {
                                    tagId -= (2*i-1) * Math.pow(10, keybindings[key].level) * keybindings[key].depth;
                                }
                                this.addLayer(this.layer_groups[tagId]);
                                found = true;
                                break;
                            }
                        }
                        if (found) break;
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
            if (layer.options && "tagId" in layer.options) {
                map.removeLayer(layer);
            }
        });
    },
    baseAddLayer: L.Map.prototype.addLayer,
    addLayer: function (layer) {

        if (!("layer_groups" in this))
	    this.layer_groups = {};

        if (layer.options && "tagId" in layer.options) {
            var tagId = layer.options.tagId;
            console.log("Add layer with tag id", tagId);

            if (!(tagId in this.layer_groups)) {
                layer.setCache(cache);
                this.layer_groups[tagId] = layer;
                // Only load the first one
                if (Object.keys(this.layer_groups).length == 1)
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

L.Control.KeyBinding = L.Control.extend({
    options: {
	position: "topright",
        iconText: "?",
        hoverText: "Help",
        helpText: undefined,
    },

    onAdd: function (map) {
	var container = L.DomUtil.create("div", "leaflet-control-zoom leaflet-bar"),
	    options = this.options;

	this._helpButton = this._createButton(options.iconText, options.hoverText,
		                              "leaflet-control-zoom-in", container, this._toggleHelp);

        this._help = L.DomUtil.create("div", "leaflet-help", container);
	L.DomEvent.on(this._help, "click", this._onClose, this);

        var content = L.DomUtil.create("div", "leaflet-help-content", this._help);
        var text = "<span class=\"close\">&times;</span>";
        if (options.helpText !== "") {
            text += options.helpText;
        } else {
            text += "<p>Default keybindings are:</p>";
	    text += "<ul>";
            for (var key in keybindings) {
                var keys = keybindings[key];
                if (keys.length == undefined)
                    keys = keys.keys;
                text += "<li> Use ";
                if (keys.length == 2)
                    text += "<b>" + keys[0] + "/" + keys[1] + "</b> keys";
                else
                    text += "<b>" + keys[0] + "</b> key";
                if (key == "cache")
                    text += " to clean the cache";
                else if (key == "colorscale")
                    text += " to change color scale by &plusmn; 10%";
                else
                    text += " to change <b>" + key + "</b>";
                text += "</li>";
            }
            text += "</ul>"
        }
        content.innerHTML = text;

	return container;
    },

    onRemove: function (map) {
    },

    _onClose: function (e) {
        this._help.style.display = "none";
    },

    _toggleHelp: function (e) {
        this._help.style.display = "block";
    },

    _createButton: function (icon, hover, className, container, fn) {
	var link = L.DomUtil.create("a", className, container);
	link.innerHTML = icon;
	link.href = "#";
	link.title = hover;

	/*
	 * Will force screen readers like VoiceOver to read this as "Zoom in - button"
	 */
	link.setAttribute("role", "button");
	link.setAttribute("aria-label", hover);

	L.DomEvent.disableClickPropagation(link);
	L.DomEvent.on(link, "click", L.DomEvent.stop);
	L.DomEvent.on(link, "click", fn, this);
	L.DomEvent.on(link, "click", this._refocusOnMap, this);

	return link;
    },

});

L.control.keyBinding = function (options) {
    return new L.Control.KeyBinding(options);
};


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
        this.obj = L.control.keyBinding(this.get_options());
    }
}
