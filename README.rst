.. raw:: html

      <img src="https://user-images.githubusercontent.com/2495611/80969621-33593680-8e1a-11ea-9692-39e63e9804d8.png" height="400px">

A tool to visualize and play with CMB maps. ``psplay`` is a ``jupyter`` extension to allow
interactive visualization of CMB maps through `Leaflet <leafletjs.com>`_ library. ``psplay`` also
provides a set of tools based on `pspy <https://github.com/simonsobs/pspy>`_ to compute and to show
CMB power spectra. You can have a better idea of what ``psplay`` can do by watching this short
`video <https://www.youtube.com/watch?v=5IpHZ4WWf2Q>`_.

All the specific javascript library developed for ``psplay`` is done by `Sigurd Naess
<https://github.com/amaurea>`_.  The build process and javascript architecture is highly inspired by
`ipyleaflet <https://github.com/jupyter-widgets/ipyleaflet>`_ project.

.. image:: https://img.shields.io/pypi/v/psplay.svg?style=flat
   :target: https://pypi.python.org/pypi/psplay/
.. image:: https://img.shields.io/npm/v/jupyter-leaflet-car
   :target: https://www.npmjs.com/package/jupyter-leaflet-car
.. image:: https://travis-ci.com/xgarrido/psplay.svg?branch=master
   :target: https://travis-ci.com/xgarrido/psplay

Examples
--------

* `From simulated CAR map to psplay <https://github.com/xgarrido/psplay/blob/master/examples/car_simulation_to_analysis.ipynb>`_
* `From HEALPIX map file to psplay <https://github.com/xgarrido/psplay/blob/master/examples/healpix_simulation_to_analysis.ipynb>`_

Installation
------------

To install, you will need to have or to install ``numpy``. Then, run

.. code:: shell

   $ pip install psplay [--user]

``psplay`` runs within a Jupyter notebook and we recommend to use JupyterLab to fully enjoy ``psplay``

To enable the extension within Jupyter, you will need to install several JupyterLab extensions
especially the Python ``plotly`` `library <https://plotly.com/python>`_ and the Jupyter `widgets
<https://github.com/jupyter-widgets/ipywidgets>`_. You will also need `nodejs library
<https://nodejs.org/en>`_ and its package manager ``npm``. For JupyterLab > 2.0.0, you can do

.. code:: shell

   $ jupyter labextension install plotlywidget jupyterlab-plotly
   $ jupyter labextension install @jupyter-widgets/jupyterlab-manager @jupyter-widgets/jupyterlab-sidecar


Finally, you need to install the `jupyter-leaflet-car <https://www.npmjs.com/package/jupyter-leaflet-car>`_ extension

.. code:: shell

   $ jupyter labextension install jupyter-leaflet jupyter-leaflet-car

Using ``docker``
----------------

Given the number of requirements, you can use a ``docker`` image already made with the needed
libraries and everything compiled and installed. You should first install `docker
<https://docs.docker.com/install/>`_ for your operating system.

Then, you can run the ``simonsobs/psplay`` image by doing

.. code:: shell

   $ docker run --rm -p 8888:8888 simonsobs/psplay

After pulling the ``docker`` image, a JupyterLab instance should start. If your web browser does not
automatically load the web page, you can copy-paste the JupyterLab URL.

You can bind a local directory to make it available within the ``docker`` container with the ``-v``
flag (see https://docs.docker.com/storage/bind-mounts for more details).

Using at ``NERSC``
------------------

On NERSC machines, you can install ``psplay`` within a ``conda`` environment but you can also use a
common installation for Simons Observatory people (*i.e.* people belonging to ``sobs`` group)
without need to redo the long installation process.

First you need to log to ``cori.nersc.gov`` machines by enabling port forward to your local machine

.. code:: shell

   $ ssh -L 8888:localhost:8888 user@cori.nersc.gov

Everything passing *via* port 8888 in ``NERSC`` will be forward to your local machine and you will
be able to grab the JupyterLab instance within your local web browser.

Given a successful connection, you must load the latest ``python`` module

.. code:: shell

   $ module load python

and then you can load the ``conda`` environment with the whole software suite for ``psplay``

.. code:: shell

   $ source activate /global/cscratch1/sd/xgarrido/psplay/env

Finally, you can go into ``/global/cscratch1/sd/xgarrido/psplay/examples`` directory where
simulation files have been already processed. Then, fire a JupyterLab instance by typing

.. code:: shell

   $ jupyter lab --port 8888 --no-browser minimal_working_example.ipynb

Copy-paste the URL into your local browser and run the Jupyter notebook.

Installation from sources
-------------------------

For a development installation (requires `npm <https://www.npmjs.com/get-npm>`_)

.. code:: shell

   $ git clone https://github.com/xgarrido/psplay.git
   $ cd psplay
   $ pip install -e .

If you are using the classic Jupyter Notebook you need to install the nbextension:

.. code:: shell

   $ jupyter nbextension install --py --symlink --sys-prefix psplay
   $ jupyter nbextension enable --py --sys-prefix psplay

If you are using JupyterLab, you need to install the labextension:

.. code:: shell

   $ jupyter labextension install @jupyter-widgets/jupyterlab-manager js

Note for developers:

- the ``-e`` pip option allows one to modify the Python code in-place. Restart the kernel in order
  to see the changes.
- the ``--symlink`` argument on Linux or OS X allows one to modify the JavaScript code
  in-place. This feature is not available with Windows.

For automatically building the JavaScript code every time there is a change, run the following
command from the ``psplay/js/`` directory:

.. code:: shell

   $ npm run watch


If you are on JupyterLab you also need to run the following in a separate terminal:

.. code:: shell

   $ jupyter lab --watch


Every time a JavaScript build has terminated you need to refresh the Notebook page in order to load
the JavaScript code again.

Authors
-------

* Xavier Garrido
* Thibaut Louis
* Sigurd Naess

The code is part of `PSpipe <https://github.com/simonsobs/PSpipe>`_ the Simons Observatory power spectrum pipeline.
