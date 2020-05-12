const L = require('../leaflet-car.js');

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
            layer.options.color = patchColors[ipatch % patchColors.length];
        }
        this.baseInitPath(layer);
    },
});

// Increase patch number and store patch id with color
L.Draw.Feature.include({
    baseFire: L.Draw.Feature.prototype._fireCreatedEvent,
    _fireCreatedEvent: function (layer) {
        // console.log("Fire created event");
        if (layer.options) {
            layer.options.color = patchColors[ipatch % patchColors.length];
            layer.options.id = "patch #" + ipatch;
        }
        this.baseFire(layer);
        ipatch++;
    },
});

// Update circle radius
L.EditToolbar.Edit.include({
    baseSave: L.EditToolbar.Edit.prototype.save,
    save: function () {
	var editedLayers = new L.LayerGroup();
	this._featureGroup.eachLayer(function (layer) {
	    if (layer.edited) {
                if (layer instanceof L.Circle) {
                    layer.options.radius = layer.getRadius();
                }
		editedLayers.addLayer(layer);
		layer.edited = false;
	    }
	});
	this._map.fire(L.Draw.Event.EDITED, {layers: editedLayers});
        // Remove buffers
        var map = this._map;
        map.eachLayer(function(layer) {
            if (layer instanceof L.Circle || layer instanceof L.Polygon) {
                if (layer.options && layer.options.fill == false)
                    map.removeLayer(layer);
            }
        });
    },
});

L.EditToolbar.Delete.include({
    baseRemoveAllLayers: L.EditToolbar.Delete.prototype.removeAllLayers,
    removeAllLayers: function () {
        console.log("Remove all layers");
        this.baseRemoveAllLayers();
        var map = this._map;
        map.eachLayer(function(layer) {
            if (layer instanceof L.Circle || layer instanceof L.Polygon) {
                map.removeLayer(layer);
            }
        });

    },
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
