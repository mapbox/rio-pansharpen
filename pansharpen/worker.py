#!/usr/bin/env python
from __future__ import division

import click
import numpy as np
import rasterio
import riomucho
from pansharpen.methods import Brovey
from rasterio.transform import guard_transform

from . utils import (
    _pad_window, _upsample, _simple_mask,
    _calc_windows, _check_crs, _create_apply_mask,
    _half_window, _rescale)


def pansharpen(vis, vis_transform, pan, pan_transform,
               pan_dtype, r_crs, dst_crs, weight,
               method="Brovey", src_nodata=0):
    """Pansharpen a lower-resolution visual band

    Parameters
    =========
    vis: ndarray, 3D with shape == (3, vh, vw)
        Visual band array with RGB bands
    vis_transform: Affine
        affine transform defining the georeferencing of the vis array
    pan: ndarray, 2D with shape == (ph, pw)
        Panchromatic band array
    pan_transform: Affine
        affine transform defining the georeferencing of the pan array
    method: string
        Algorithm for pansharpening; default Brovey

    Returns:
    ======
    pansharp: ndarray, 3D with shape == (3, ph, pw)
        pansharpened visual band
        affine transform is identical to `pan_transform`
    """
    rgb = _upsample(_create_apply_mask(vis), pan.shape, vis_transform, r_crs,
                    pan_transform, dst_crs)

    # Main Pansharpening Processing
    if method == Brovey:
        pansharp, _ = Brovey(rgb, pan, weight, pan_dtype)
    # TODO: add other methods

    return pansharp


def _pansharpen_worker(open_files, pan_window, _, g_args):
    """rio mucho worker for pansharpening. It reads input
    files and performing pansharpening on each window.

    Parameters
    ------------
    open_files: list of rasterio open files
    pan_window: tuples
    g_args: dictionary

    Returns
    ---------
    out: None
        Output is written to dst_path

    """
    pan = open_files[0].read(1, window=pan_window).astype(np.float32)
    pan_dtype = open_files[0].meta['dtype']

    # Get the rgb window that covers the pan window
    if g_args.get("half_window"):
        rgb_window = half_window(pan_window)
    else:
        padding = 2
        pan_bounds = open_files[0].window_bounds(pan_window)
        rgb_base_window = open_files[1].window(*pan_bounds)
        rgb_window = _pad_window(rgb_base_window, padding)

    # Determine affines for those windows
    pan_affine = open_files[0].window_transform(pan_window)
    rgb_affine = open_files[1].window_transform(rgb_window)

    rgb = riomucho.utils.array_stack(
        [src.read(window=rgb_window, boundless=True).astype(np.float32)
         for src in open_files[1:]])

    if g_args["verb"]:
        click.echo('pan shape: %s, rgb shape %s' % (pan.shape, rgb.shape))

    pansharpened = pansharpen(
                        rgb, rgb_affine, pan, pan_affine, pan_dtype,
                        g_args["r_crs"], g_args["dst_crs"],
                        g_args["weight"], method=Brovey
                    )

    pan_rescale = _rescale(pansharpened,
                           g_args["src_nodata"],
                           g_args["dst_dtype"])

    return pan_rescale


def calculate_landsat_pansharpen(src_paths, dst_path, dst_dtype,
                                 weight, verbosity, jobs, half_window,
                                 customwindow):
    """Parameters
    ------------
    src_paths: list of string (pan_path, r_path, g_path, b_path)
    dst_path: string
    dst_dtype: 'uint16', 'uint8'. [Default] 'uint8'
    weight: float
    jobs: integer
    half_window: True/False. [Default] False
    customwindow: integer. [Default] 0

    Returns
    ---------
    out: None
        Output is written to dst_path
    """

    with rasterio.open(src_paths[0]) as pan_src:
        windows = _calc_windows(pan_src, customwindow)
        profile = pan_src.profile

        if profile['count'] > 1:
            raise RuntimeError(
                "Pan band must be 1 band - is {}".format(profile['count']))

        dst_dtype = np.__dict__[dst_dtype]

        profile.update(
            transform=guard_transform(pan_src.transform),
            compress='DEFLATE',
            blockxsize=512,
            blockysize=512,
            dtype=dst_dtype,
            tiled=True,
            count=4,
            photometric='rgb')

    with rasterio.open(src_paths[1]) as r_src:
        r_meta = r_src.meta

    if profile['width'] <= r_meta['width'] or \
       profile['height'] <= r_meta['height']:
        raise RuntimeError(
            "Pan band must be larger than RGB bands")

    _check_crs([r_meta, profile])

    g_args = {
        "verb": verbosity,
        "half_window": half_window,
        "dst_dtype": dst_dtype,
        "weight": weight,
        "dst_aff": guard_transform(profile['transform']),
        "dst_crs": profile['crs'],
        "r_aff": guard_transform(r_meta['transform']),
        "r_crs": r_meta['crs'],
        "src_nodata": 0}

    with riomucho.RioMucho(src_paths, dst_path, _pansharpen_worker,
                           windows=windows, global_args=g_args,
                           options=profile, mode='manual_read') as rm:
        rm.run(jobs)
