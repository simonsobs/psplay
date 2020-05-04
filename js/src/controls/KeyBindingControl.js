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

        if (!("layer_groups" in this))
	    this.layer_groups = {};

        if (layer.options && "tag" in layer.options) {
            var tag = layer.options.tag;
            console.log("Add layer with tag", tag);

            if (!(tag in this.layer_groups)) {
                this.layer_groups[tag] = [];
            }

            var tagId = this.layer_groups[tag].length;
            if (!("tagId" in layer.options)) {
                layer.options.tagId = tagId;
                this.layer_groups[tag].push(layer);
                layer.setCache(cache);
                // Only load the first one
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
                text += "<li> Use ";
                if (keys.length == 2)
                    text += "<b>" + keys[0] + "/" + keys[1] + "</b> keys";
                else
                    text += "<b>" + keys[0] + "</b> key";
                text += " to change " + key + "</li>";
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
