// Copyright (c) Simons Observatory.
// Distributed under the terms of the Modified BSD License.

// Layers
var graticule = require('./layers/Graticule.js');
var colorizabletilelayer = require('./layers/ColorizableTileLayer.js');

//Controls
var status = require('./controls/StatusBarControl.js');

//Geo
var car = require('./geo/crs/CRS.CAR.js')


//Exports
module.exports = {
    // views
    LeafletGraticuleView : graticule.LeafletGraticuleView,
    LeafletColorizableTileLayerView : colorizabletilelayer.LeafletColorizableTileLayerView,
    LeafletStatusBarControlView : status.LeafletStatusBarControlView,

    // models
    LeafletGraticuleModel : graticule.LeafletGraticuleModel,
    LeafletColorizableTileLayerModel : colorizabletilelayer.LeafletColorizableTileLayerModel,
    LeafletStatusBarControlModel : status.LeafletStatusBarControlModel,
};
