// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

var jupyter_leaflet_car = require('./index');

var base = require('@jupyter-widgets/base');

module.exports = {
  id: 'jupyter.extensions.jupyter-leaflet-car',
  requires: [base.IJupyterWidgetRegistry],
  activate: function(app, widgets) {
    widgets.registerWidget({
      name: 'jupyter-leaflet-car',
      version: jupyter_leaflet_car.version,
      exports: jupyter_leaflet_car
    });
  },
  autoStart: true
};
