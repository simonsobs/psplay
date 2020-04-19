const L = require('leaflet');

/*
 * @namespace CRS
 * @crs L.CRS.CAR
 *
 * A simple CRS that maps longitude and latitude into `x` and `y` directly.
 * `distance()` returns simple euclidean distance.
 */

export var CAR = L.extend({}, L.CRS, {
	projection: L.Projection.LonLat,

        // lat increases upwards, lon leftwards
        // lower-left corner is at (lat=-90,lon=180)
	transformation: new L.Transformation(-1, 180, -1, 90),

        // 120 pixels per degree at full resolution
	scale: function (zoom) {
		return 120 * Math.pow(2, zoom);
	},

	zoom: function (scale) {
		return Math.log(scale / 120) / Math.LN2;
	},

        // Simple euclidian distance to get circle radius
	distance: function (latlng1, latlng2) {
		var dx = latlng2.lng - latlng1.lng,
		    dy = latlng2.lat - latlng1.lat;

		return Math.sqrt(dx * dx + dy * dy);
	},

        wrapLng: [180, -180],

	infinite: false
});

L.CRS.CAR = CAR;
