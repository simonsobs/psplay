const L = require('./leaflet-car.js');

// Print distance in degrees
var orgReadbleDistance = L.GeometryUtil.readableDistance;
L.GeometryUtil.readableDistance = function (distance, isMetric, isFeet, isNauticalMile, precision) {
    if (isMetric||isNauticalMile||!isFeet) return orgReadbleDistance(distance, isMetric, isFeet, isNauticalMile, precision);
    return L.GeometryUtil.formattedNumber(distance, 1) + ' degrees';
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
