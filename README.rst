==============
rio-pansharpen
==============
.. image:: https://img.shields.io/pypi/v/rio-pansharpen.svg
   :target: https://img.shields.io/pypi/v/rio-pansharpen.svg

.. image:: https://circleci.com/gh/mapbox/rio-pansharpen.svg?style=shield&circle
   :target: https://circleci.com/gh/mapbox/rio-pansharpen

pansharpens Landsat 8 scenes.

What is pansharpening?
======================
Pansharpening is a process of using the spatial information in the high-resolution grayscale band (panchromatic, or pan-band) and color information in the multispectral bands to create a single high-resolution color image.

::
 
    P pan-pixel cluster + M single multispectral pixel = M pan-sharpened pixel

Find more examples and information in the `Mapbox pansharpening blog post <https://www.mapbox.com/blog/l8-pansharpening/>`_.

Install
=======

We highly recommend installing in a virtualenv. Once activated,
::

    pip install -U pip
    pip install rio-pansharpen

Or install from source
::

    git checkout https://github.com/mapbox/rio-pansharpen.git
    cd rio-pansharpen
    pip install -U pip
    pip install -r requirements.txt
    pip install -e .



Python API
==========

pansharpen.worker
-----------------
The ``worker`` module pansharpens Landsat 8. Visit the `USGS Landsat page <http://landsat.usgs.gov/band_designations_landsat_satellites.php>`_ page for more information on Landsat 8 band designations.

1. ``worker.pansharpen``
------------------------
The ``worker.pansharpen`` function accepts the following as inputs:

- numpy 3D array with shape == (3, vis_height, vis_width)
- affine transform defining the georeferencing of the vis array 
- numpy 2D array with shape == (pan_height, pan_width)
- affine transform defining the georeferencing of the pan array 
- pansharpening method

and outputs:

- numpy 3D array with shape == (3, pan_height, pan_width)

::

    >>> from pansharpen import worker
    >>> from pansharpen.methods import Brovey
    ...
    >>> pansharpened = worker.pansharpen(vis, vis_transform, pan, pan_transform,
                           pan_dtype, r_crs, dst_crs, weight,
                           method="Brovey", src_nodata=0)



2. ``worker.calculate_landsat_pansharpen``
------------------------------------------
::

    >>> from pansharpen import worker
    >>> from pansharpen.utils import _calc_windows
    >>> import riomucho
    ...
    >>> worker.calculate_landsat_pansharpen(src_paths, dst_path, dst_dtype,
            weight, verbosity, jobs, half_window,
            customwindow)



CLI
===


pansharpen
----------


::

    Usage: rio pansharpen [OPTIONS] [SRC_PATHS]... DST_PATH

      Pansharpens a landsat scene. Input is a panchromatic band (B8), plus 3 color
      bands (B4, B3, B2)

         rio pansharpen B8.tif B4.tif B3.tif B2.tif out.tif

      Or with shell expansion

         rio pansharpen LC80410332015283LGN00_B{8,4,3,2}.tif out.tif

    Options:
      --dst-dtype [uint16|uint8]
      -w, --weight FLOAT          Weight of blue band [default = 0.2]
      -v, --verbosity
      -j, --jobs INTEGER          Number of processes [default = 1]
      --half-window               Use a half window assuming pan in aligned with
                                  rgb bands, default: False
      -c, --customwindow INTEGER  Specify blocksize for custom windows >
                                  150[default=src_blockswindows]
      --help                      Show this message and exit.
      --help                 Show this message and exit.




Comparison of Different Pansharpening Methods
---------------------------------------------
We've implemented the Weighted Brovey Transform for pansharpening, which is appropriate for data like Landsat where the panchromatic band is relatively similar in resolution to the color bands.

For more information on other pansharpening methods such as IHS, PCA, P+XS, Wavelet, VWP, Wavelet with Canny Edge Detector etc, please read our notes `here <https://github.com/mapbox/pansharpening/blob/master/docs/pansharpening_methods.rst>`_.
