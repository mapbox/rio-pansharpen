#!/usr/bin/env python
from __future__ import division

import click
import numpy as np
from affine import Affine
import rasterio
import riomucho
from pansharpen.scripts.pansharp_methods import Brovey
from rasterio.enums import Resampling
from rasterio.transform import guard_transform
from rasterio.warp import reproject


def adjust_block_size(width, height, blocksize):
    if width % blocksize == 1:
        blocksize += 1
    elif height % blocksize == 1:
        blocksize += 1
    return blocksize


def make_windows(width, height, blocksize):
    """
    Manually makes windows of size equivalent to
    pan band image
    """
    for x in range(0, width, blocksize):
        for y in range(0, height, blocksize):
            yield ((y, min((y + blocksize), height)),
                   (x, min((x + blocksize), width)))


def make_affine(fr_shape, to_shape):
    fr_window_affine = Affine(
        1, 0, 0,
        0, -1, 0)

    to_window_affine = Affine(
        (fr_shape[1] / float(to_shape[1])), 0, 0,
        0, -(fr_shape[0] / float(to_shape[0])), 0)

    return fr_window_affine, to_window_affine


def load_half_window(window):
    return tuple((w[0] / 2, w[1] / 2) for w in window)


def check_crs(inputs):
    for i in range(1, len(inputs)):
        if inputs[i-1]['crs'] != inputs[i]['crs']:
            raise RuntimeError(
                'CRS of inputs must be the same: '
                'received %s and %s' % (inputs[i-1]['crs'],
                                        inputs[i]['crs']))


def upsample(rgb, panshape, src_aff, src_crs, to_aff, to_crs):
    up_rgb = np.empty((rgb.shape[0], panshape[0], panshape[1]), dtype=rgb.dtype)

    reproject(
        rgb, up_rgb,
        src_transform=src_aff,
        src_crs=src_crs,
        dst_transform=to_aff,
        dst_crs=to_crs,
        resampling=Resampling.bilinear)

    return up_rgb


def simple_mask(data, ndv):
    '''Exact nodata masking'''
    nd = np.iinfo(data.dtype).max
    alpha = np.invert(np.all(np.dstack(data) == ndv, axis=2)).astype(data.dtype) * nd

    return alpha


def run_pansharpen(open_files, pan_window, _, g_args):
    """
    Reading input files and performing pansharpening on each window
    """
    pan = open_files[0].read(1, window=pan_window).astype(np.float32)
    pan_dtype = open_files[0].meta['dtype']

    # Get the rgb window that covers the pan window
    padding = 2
    pan_bounds = open_files[0].window_bounds(pan_window)
    rgb_base_window = open_files[1].window(*pan_bounds)
    rgb_window = pad_window(rgb_base_window, padding)

    # Determine affines for those windows
    pan_affine = open_files[0].window_transform(pan_window)
    rgb_affine = open_files[1].window_transform(rgb_window)

    rgb = riomucho.utils.array_stack(
        [src.read(window=rgb_window, boundless=True).astype(np.float32)
         for src in open_files[1:]])

    # Create a mask of pixels where any channel is 0 (nodata):
    color_mask = np.minimum(
        rgb[0],
        np.minimum(rgb[1], rgb[2])) * 2 ** 16

    # Apply the mask:
    rgb = np.array([
        np.minimum(band, color_mask) for band in rgb])

    if g_args["verb"]:
        click.echo('pan shape: %s, rgb shape %s' % (pan.shape, rgb[0].shape))

    rgb = upsample(rgb, pan.shape, rgb_affine, g_args["r_crs"],
                   pan_affine, g_args['dst_crs'])

    # Main Pansharpening Processing
    pan_sharpened, _ = Brovey(rgb, pan, g_args["weight"], pan_dtype)

    # convert to 8bit value range in place
    scale = float(np.iinfo(np.uint16).max) / float(np.iinfo(np.uint8).max)

    pan_sharpened = np.concatenate(
        [(pan_sharpened / scale).astype(np.uint8),
         simple_mask(
             pan_sharpened.astype(np.uint8),
             (0, 0, 0)).reshape(
                 1, pan_sharpened.shape[1], pan_sharpened.shape[2])])

    return pan_sharpened


def pad_window(wnd, pad):
    return (
        (wnd[0][0] - pad, wnd[0][1] + pad),
        (wnd[1][0] - pad, wnd[1][1] + pad))


def pansharpen(src_paths, dst_path, weight, verbosity, processes, customwindow):
    """
    Pansharpening a landsat scene --
    Opening files, reading input meta data and writing the result
    of pansharpening into each window respentively.
    """
    with rasterio.open(src_paths[0]) as pan_src:
        if customwindow:
            blocksize = adjust_block_size(pan_src.meta['width'],
                                          pan_src.meta['height'],
                                          int(customwindow))
            windows = [(window, (0, 0))
                       for window in make_windows(pan_src.meta['width'],
                                                  pan_src.meta['height'],
                                                  blocksize)]
        else:
            windows = [(window, ij) for ij, window in pan_src.block_windows()]

        kwargs = pan_src.meta

        if kwargs['count'] > 1:
            raise RuntimeError(
                "Pan band must be 1 band - %s is %s" % (src_paths[0],
                                                        kwargs['count']))

        kwargs.update(transform=guard_transform(pan_src.transform))
        kwargs.update(compress='DEFLATE')
        kwargs.update(blockxsize=512)
        kwargs.update(blockysize=512)
        kwargs.update(dtype=np.uint8)
        kwargs.update(tiled=True)
        kwargs.update(count=4)
        kwargs.update(photometric='rgb')

    with rasterio.open(src_paths[1]) as r_src:
        r_meta = r_src.meta

    if kwargs['width'] <= r_meta['width'] or kwargs['height'] <= r_meta['height']:
        raise RuntimeError(
            "Pan band %s is the same size (%s, %s) "
            "or smaller than RGB bands (%s, %s)" % (src_paths[0],
                                                    kwargs['height'],
                                                    kwargs['width'],
                                                    r_meta['height'],
                                                    r_meta['width']))

    check_crs([r_meta, kwargs])

    g_args = {
        "verb": verbosity,
        "weight": weight,
        "dst_aff": guard_transform(kwargs['transform']),
        "dst_crs": kwargs['crs'],
        "r_aff": guard_transform(r_meta['transform']),
        "r_crs": r_meta['crs']}

    with riomucho.RioMucho(src_paths, dst_path, run_pansharpen,
                           windows=windows, global_args=g_args,
                           options=kwargs, mode='manual_read') as rm:
        rm.run(1)


if __name__ == '__main__':
    pansharpen()
