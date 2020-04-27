# psplay

A tool to visualize and play with CMB maps. `psplay` is a `jupyter` extension to allow interactive
visualization of CMB maps through [Leaflet](leafletjs.com) library. `psplay` also provides a set of
tools based on [`pspy`](https://github.com/simonsobs/pspy) to compute and to show CMB power spectra.

![PyPI](https://img.shields.io/pypi/v/psplay)

All the javascript library developed for `psplay` is done by [Sigurd
Naess](https://github.com/amaurea). To convert CMB map from `FITS` format to tile images you will
also need this kind of [program](https://github.com/thibautlouis/sigurds_plot).

## Installation

Using pip:

```
pip install psplay
```

To enable the extension within Jupyter, you will need to install several JupyterLab extensions
especially the Python `plotly` [library](https://plotly.com/python/). For JupyterLab > 2.0.0, you
can do

```
jupyter labextension install @jupyter-widgets/jupyterlab-manager @plotlywidget@4.6.0 jupyterlab-plotly@4.6.0
```

Finally, you need to install the
[jupyter-leaflet-car](https://www.npmjs.com/package/jupyter-leaflet-car) and the support for widgets
in Jupyter

```
jupyter labextension install jupyter-leaflet-car
```

## Installation from sources

For a development installation (requires [npm](https://www.npmjs.com/get-npm))

```
git clone https://github.com/xgarrido/psplay.git
cd psplay
pip install -e .
```

If you are using the classic Jupyter Notebook you need to install the nbextension:

```
jupyter nbextension install --py --symlink --sys-prefix psplay
jupyter nbextension enable --py --sys-prefix psplay
```

If you are using JupyterLab, you need to install the labextension:

```
jupyter labextension install @jupyter-widgets/jupyterlab-manager js
```

Note for developers:

- the ``-e`` pip option allows one to modify the Python code in-place. Restart the kernel in order
  to see the changes.
- the ``--symlink`` argument on Linux or OS X allows one to modify the JavaScript code
  in-place. This feature is not available with Windows.

    For automatically building the JavaScript code every time there is a change, run the following
    command from the ``psplay/js/`` directory:

    ```
    npm run watch
    ```

    If you are on JupyterLab you also need to run the following in a separate terminal:

    ```
    jupyter lab --watch
    ```

    Every time a JavaScript build has terminated you need to refresh the Notebook page in order to
    load the JavaScript code again.

<!-- ## Documentation -->

<!-- To get started with using `ipyleaflet`, check out the full documentation -->

<!-- https://ipyleaflet.readthedocs.io/ -->
