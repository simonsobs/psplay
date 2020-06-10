const L = require('../leaflet-car.js');
const control = require('jupyter-leaflet');

var keybindings = {};

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
            if (!("all_keys" in this)) {
                this.all_keys = [];
                for (var key in keybindings) {
                    var keys = keybindings[key];
                    if (keys.length == undefined)
                        keys = keys.keys;
                    for (var i = 0; i < keys.length; i++)
                        this.all_keys.push(keys[i]);
                }
                console.log("all keys =", this.all_keys);
            }

            if (! this.all_keys.includes(e.key)) {
                console.log("Key not recognized");
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            console.log("Overload fireDOM: key press");
            console.log("e.key =", e.key);

            if ("cache" in keybindings && keybindings["cache"].includes(e.key)) {
                console.log("Clean cache");
                cache.data = {};
                return;
            }

            // Find the layer the event is propagating from and its parents.
	    targets = (targets || []).concat(this._findEventTargets(e, type));

	    if (!targets.length) { return; }
            var layers = targets[0]._layers;

            // Update color map or color scale
            if (("colormap" in keybindings && keybindings["colormap"].includes(e.key)) ||
                ("colorscale" in keybindings && keybindings["colorscale"].includes(e.key))) {
                if (this.layers_group) {
                    for (var key in this.layers_group) {
                        this._updateColors(e, this.layers_group[key]);
                    }
                }
                // Update current base layer (not overlays if any)
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "base" in layer.options && layer.options.base) {
                        console.log("update tiles", layer.options.tagId);
                        layer._updateTiles();
                    }
                }
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            // Overlay opacity
            if (("opacity" in keybindings && keybindings["opacity"].includes(e.key))) {
                if (this.overlays_group) {
                    for (var key in this.overlays_group) {
                        var layer = this.overlays_group[key];
                        for (var i = 0; i < keybindings["opacity"].length; i++) {
                            var opacity = layer.options.opacity;
                            if (e.key == keybindings["opacity"][i])
                                opacity *= Math.pow(1.1, 2*i-1);
                            if (opacity > 1.0) opacity = 1.0;
                            if (opacity < 0.0) opacity = 0.0;
                            layer.setOpacity(opacity);
                        }
                    }
                }
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            // Overlay masking
            if ("overlay" in keybindings && keybindings["overlay"].includes(e.key)) {
                var overlays = [];
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "tagId" in layer.options && "base" in layer.options && !(layer.options.base)) {
                        overlays.push(layer);
                    }
                }
                if (overlays.length == 0) {
                    for (key in this.overlays_group) {
                        this.baseAddLayer(this.overlays_group[key]);
                    }
                } else {
                    for (var i = 0; i < overlays.length; i++) {
                        this.removeLayer(overlays[i]);
                    }
                }
                this.baseFireDOMEvent(e, type, targets);
                return;
            }

            // Finally switch between (base) layers
            for (var key in layers) {
                var layer = layers[key];
                if (layer.options && "tagId" in layer.options) {
                    var found = false;
                    for (var key in keybindings) {
                        var keys = keybindings[key];
                        if (keys.length == undefined) keys = keys.keys;
                        for (var i = 0; i < keys.length; i++) {
                            if (e.key != keys[i]) continue;
                            var tagId = layer.options.tagId;
                            if (key == "layer") {
                                tagId = parseInt(tagId.toString()[keybindings[key].level]) + 1;
                                if (!(tagId in this.layers_group)) {
                                    tagId = 0;
                                }
                            } else {
                                tagId += (2*i-1) * Math.pow(10, keybindings[key].level);
                                if (!(tagId in this.layers_group)) {
                                    tagId -= (2*i-1) * Math.pow(10, keybindings[key].level) * keybindings[key].depth;
                                }
                            }
                            if (tagId in this.layers_group) {
                                this.addLayer(this.layers_group[tagId]);
                            }
                            found = true;
                            break;
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
        this.overlays = [];
        this.eachLayer(function(layer) {
            if (layer.options && "tagId" in layer.options) {
                console.log("Removing layer with tag", layer.options.tagId);
                if ("base" in layer.options && !(layer.options.base)) {
                    map.overlays.push(layer);
                }
                map.removeLayer(layer);
            }
        });
    },
    baseAddLayer: L.Map.prototype.addLayer,
    addLayer: function (layer) {
        if (!("overlays" in this))
            this.overlays = [];
        if (!("layers_group" in this))
	    this.layers_group = {};
        if (!("overlays_group" in this))
	    this.overlays_group = {};

        if (layer.options && "tagId" in layer.options) {
            var tagId = layer.options.tagId;
            console.log("Add layer with tag id", tagId);

            var groups = this.overlays_group;
            if ("base" in layer.options && layer.options.base) {
                groups = this.layers_group;
            }
            if (!(tagId in groups)) {
                groups[tagId] = layer;
                if ("base" in layer.options && layer.options.base) {
                    layer.setCache(cache);
                }
                // Only load the first one
                if (Object.keys(groups).length == 1)
                    this.baseAddLayer(layer);
            } else {
                // First remove all layers from map
                this.removeAllLayers();
                this.baseAddLayer(layer);
                // Add back activated overlays
                for (var i = 0; i < this.overlays.length; i++)
                    this.baseAddLayer(this.overlays[i]);
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
                else if (key == "opacity")
                    text += " to change overlay opacity by &plusmn; 10%";
                else if (key == "overlay")
                    text += " to show/hide overlays";
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
