const L = require('./leaflet-car.js');

// Print distance in degrees
L.GeometryUtil.readableDistance = function (distance, isMetric, isFeet, isNauticalMile, precision) {
    return L.GeometryUtil.formattedNumber(distance, 1) + ' degrees';
};

// Print area in degrees²
L.GeometryUtil.geodesicArea = function (latLngs) {
    var pointsCount = latLngs.length,
	area = 0.0;
    if (pointsCount == 4) {
	var p1 = latLngs[0],
	    p2 = latLngs[2];
	area += (p2.lng - p1.lng) * (p2.lat - p1.lat);
    }
    return Math.abs(area);
};

// Print area in degrees²
L.GeometryUtil.readableArea = function (area, isMetric, precision) {
    return L.GeometryUtil.formattedNumber(area, 2) + ' deg.²';
};

// Fix radius sign for CAR projection
// https://leafletjs.com/examples/extending/extending-1-classes.html#lclassinclude
L.Circle.include({
    baseProject: L.Circle.prototype._project,
    _project: function () {
        this.baseProject();
        this._radius = Math.abs(this._radius);
    }
});

// Patch number
var ipatch = 0;

// Patch color from plotly
var patchColorPalette = {
    "Plotly": ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']
}
var colorPalette = "Plotly";
var patchColors = patchColorPalette[colorPalette];

// Change patch color
L.SVG.include({
    baseInitPath: L.SVG.prototype._initPath,
    _initPath: function (layer) {
        if (layer.options) {
            // console.log("Color", patchColors[ipatch % patchColors.length]);
            layer.options.color = patchColors[ipatch % patchColors.length];
        }
        this.baseInitPath(layer);
    },
});

// Increase patch number
L.Draw.Feature.include({
    baseFire: L.Draw.Feature.prototype._fireCreatedEvent,
    _fireCreatedEvent: function (layer) {
        // console.log("Fire created event");
        this.baseFire(layer);
        ipatch++;
    },
    // baseInitialize: L.Draw.Feature.prototype.initialize,
    // initialize: function (map, options) {
    //     console.log("Initialise", options);
    //     this.baseInitialize(map, options);
    // },
    // baseEnable: L.Draw.Feature.prototype.enable,
    // enable: function () {
    //     console.log("Enable");
    //     this.baseEnable();
    // },
    // baseAddHooks: L.Draw.Feature.prototype.addHooks,
    // addHooks: function () {
    //     console.log("Add hooks");
    //     this.baseAddHooks();
    // }
});



// Truncate value based on number of decimals
var _round = function(num, len) {
    return Math.round(num*(Math.pow(10, len)))/(Math.pow(10, len));
};
// Helper method to format LatLng object (x.xxxxxx, y.yyyyyy)
var _strLatLng = function(latlng) {
    return _round(latlng.lat, 6) + "°, " + _round(latlng.lng, 6) + "°";
};

// Add popup to layer
L.FeatureGroup.include({
    baseAddLayer: L.FeatureGroup.prototype.addLayer,
    addLayer: function (layer) {
        var area = null, center = null;
        var content = "<p style=\"color:" + patchColors[ipatch % patchColors.length] + "\"><b>patch #" + ipatch + "</b><br/>";

        if (layer instanceof L.Circle) {
            center = layer.getLatLng();
            area = L.GeometryUtil.formattedNumber(Math.PI * layer.getRadius()**2, 2);
        } else if (layer instanceof L.Rectangle) {
            var latlngs = layer._defaultShape ? layer._defaultShape() : layer.getLatLngs(),
                area = L.GeometryUtil.geodesicArea(latlngs);
            area = L.GeometryUtil.formattedNumber(area, 2);
            center = L.latLng((latlngs[0].lat + latlngs[2].lat)/2, (latlngs[0].lng + latlngs[2].lng)/2);
        }
        if (area) {
            content += "<font size=\"-3\">Area: " + area + " deg.²<br/>"
        }
        if (content) {
            content += "Center: " + _strLatLng(center);
        }
        content += "</font></p>";
        // layer.bindTooltip(content, {permanent: true, direction: "top", offset: [0, 0]});
        layer.bindTooltip(content, {sticky: true});
        return this.baseAddLayer(layer);
    },
    baseRemoveLayer: L.FeatureGroup.prototype.removeLayer,
    removeLayer: function (layer) {
        console.log("Remove patch");
        ipatch = 0;
        return this.baseRemoveLayer(layer);
    }
});

L.Control.Layers.include({
    baseInitialize: L.Control.Layers.prototype.initialize,
    initialize: function (baseLayers, overlays, options) {
        options.collapsed = false;
        this.baseInitialize(baseLayers, overlays, options);
    },
    // baseOnLayerChange: L.Control.Layers.prototype._onLayerChange,
    // _onLayerChange: function (e) {
    //     this.baseOnLayerChange(e);
    //     this._map.fire("recolor");
    //     console.log("Fire recolor");
    // }
});

var icolormaps = [];
for (var cmap in L.ColorizableUtils.colormaps) {
    icolormaps.push(cmap);
}

var cache = {};
L.Map.include({
    _updateColors: function (e, layer) {
        if (layer.options && "colormap" in layer.options) {
            if (e.key == "g") {
                console.log("Colormap");
                var colormap = layer.options.colormap;
                for (var i = 0; i < icolormaps.length; i++) {
                    if (colormap === icolormaps[i]) {
                        layer.options.colormap = icolormaps[(i+1) % icolormaps.length];
                        break;
                    }
                }
            } else if (e.key == "u") {
                console.log("increase color");
                var scale = layer.options.scale;
                layer.options.scale *= 1.1;
            } else if (e.key == "i") {
                console.log("decrease color");
                var scale = layer.options.scale;
                layer.options.scale /= 1.1;
            }
        }
    },
    baseFireDOMEvent: L.Map.prototype._fireDOMEvent,
    _fireDOMEvent: function (e, type, targets) {
        if (e.type === 'keypress') {

            console.log("Overload fireDOM: key press");
            console.log("e.key=", e.key);
            console.log("type=", type)

            if (e.key == "z") {
                console.log("Clean cache");
                cache.data = {};
                return;
            }

            // Find the layer the event is propagating from and its parents.
	    targets = (targets || []).concat(this._findEventTargets(e, type));

	    if (!targets.length) { return; }
            window.target = targets;
            var layers = targets[0]._layers;
            console.log("Layers length =", layers.length);

            if (["g", "u", "i"].includes(e.key)) {
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
            }
            if (["j", "k"].includes(e.key)) {
                console.log("Change layer");
                // Update current layer
                for (var key in layers) {
                    var layer = layers[key];
                    if (layer.options && "tag" in layer.options && "tagId" in layer.options) {
                        var tag = layer.options.tag;
                        var tagId = layer.options.tagId;
                        if (e.key == "j")
                            tagId = (tagId + 1) % this.layer_groups[tag].length;
                        if (e.key == "k")
                            tagId = (tagId - 1) % this.layer_groups[tag].length;

                        if (tagId == -1) tagId += this.layer_groups[tag].length;
                        this.addLayer(this.layer_groups[tag][tagId]);
                    }
                }
            }
        }
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
            // console.log("Layer tag", tag);

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
    },

});
