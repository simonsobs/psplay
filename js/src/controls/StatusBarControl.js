// Sigurd's modified version of this control. Behaves normally for normal layers,
// but for colorizable layers also prints value at mouse position

const L = require('../leaflet-car.js');
const control = require('jupyter-leaflet');

function format_coord(x) { return x.toFixed(5); }

L.Control.StatusBar = L.Control.extend({
	options: {
		position: 'bottomleft',
		separator: ' : ',
		emptyString: 'Unavailable',
		lngFirst: false,
		numDigits: 5,
	        valDigits: 1,
                mapRangeUnit: ' µK',
                positionUnit: '°',
		lngFormatter: format_coord,
		latFormatter: format_coord,
	        valFormatter: undefined,
		prefix: ''
	},

	onAdd: function (map) {
		this._container = L.DomUtil.create('div', 'leaflet-control-attribution');
		L.DomEvent.disableClickPropagation(this._container);
		map.on('mousemove', this._onMouseMove, this);
		map.on('recolor', this._onMouseMove, this);
		this._container.innerHTML = this.options.emptyString;
		return this._container;
	},

	onRemove: function (map) {
		map.off('mousemove', this._onMouseMove)
		map.off('recolor', this._onMouseMove)
	},

	_onMouseMove: function (e) {
		var innerHTML = this.options.prefix;
		// Add map value if available
		var layer = null;
		e.target.eachLayer(function (l) {
		    if (!layer && "options" in l && "colormap" in l.options) {
			layer = l;
                    }

		});
                if (layer) {
                    var cmap = layer.options.colormap;
		    var ndig = this.options.valDigits;
	            var [min,max] = L.ColorizableUtils.apply_scale(layer.options.valueMin, layer.options.valueMax, layer.options.scale, layer.options.skew);
		    if (min == -max) {
                        innerHTML += " Colormap " + cmap + " ± " +  max.toFixed(ndig) + this.options.mapRangeUnit + " | ";
		    } else {
			innerHTML += " Colormap " + cmap + " " +  min.toFixed(ndig) + this.options.separator + max.toFixed(ndig) + this.options.mapRangeUnit + " | ";
		    }
                }
                var latlng = e.latlng;
                if (latlng) {
  	            var lng = (this.options.lngFormatter ? this.options.lngFormatter(latlng.lng) : L.Util.formatNum(latlng.lng, this.options.numDigits)) + this.options.positionUnit;
      	            var lat = (this.options.latFormatter ? this.options.latFormatter(latlng.lat) : L.Util.formatNum(latlng.lat, this.options.numDigits)) + this.options.positionUnit;
	            var value = this.options.lngFirst ? lng + this.options.latlngUnit + this.options.separator + lat : lat + this.options.separator + lng;
                    innerHTML += value
                }
	        if (false && layer) {
		    var val = layer.getValueAtLayerPoint(e.layerPoint);
		    innnerHTML += this.options.separator + (this.options.valFormatter ? this.options.valFormatter(val) : L.Util.formatNum(val, this.options.valDigits)) + this.options.positionUnit;
		}
		this._container.innerHTML = innerHTML;
	}

});

L.Map.mergeOptions({
    statusbarControl: false
});

L.control.statusBar = function (options) {
    return new L.Control.StatusBar(options);
};

export class LeafletStatusBarControlModel extends control.LeafletControlModel {
    defaults() {
        return {
            ...super.defaults(),
            _view_name: 'LeafletStatusBarControlView',
            _model_name: 'LeafletStatusBarControlModel',
            _view_module: 'jupyter-leaflet-car',
            _model_module: 'jupyter-leaflet-car',
        };
    }
}

export class LeafletStatusBarControlView extends control.LeafletControlView {
    initialize(parameters) {
        super.initialize(parameters);
        this.map_view = this.options.map_view;
    }

    create_obj() {
        this.obj = L.control.statusBar(this.get_options());
    }
}
