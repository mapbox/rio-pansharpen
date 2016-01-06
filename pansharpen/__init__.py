#!/usr/bin/env python

import click
import numpy as np
import rasterio as rio
import riomucho as rios
from pansharpen.scripts.pansharp_methods import Brovey
from rasterio.warp import reproject, RESAMPLING
from rasterio import Affine


class NoRetry(click.ClickException):
    """Do not retry"""
    exit_code = 3



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
           yield (
               (y, min((y + blocksize), height)),
               (x, min((x + blocksize), width))
               )

def make_affine(fr_shape, to_shape):
    fr_window_affine = Affine(1, 0, 0,
        0, -1, 0)

    to_window_affine = Affine((fr_shape[1] / float(to_shape[1])), 0, 0,
        0, -(fr_shape[0] / float(to_shape[0])), 0)

    return fr_window_affine, to_window_affine


def load_half_window(window):
    return tuple((w[0] / 2, w[1] / 2) for w in window)

def check_crs(inputs):
    for i in range(1, len(inputs)):
        if inputs[i-1]['crs'] != inputs[i]['crs']:
            raise NoRetry('CRS of inputs must be the same: received %s and %s' % (inputs[i-1]['crs'], inputs[i]['crs'] ))


def upsample(rgb, panshape, src_aff, src_crs, to_aff, to_crs):
    up_rgb = np.empty((rgb.shape[0], panshape[0], panshape[1]), dtype=rgb.dtype)

    reproject(
        rgb, up_rgb,
        src_transform=src_aff,
        src_crs=src_crs,
        dst_transform=to_aff,
        dst_crs=to_crs,
        resampling=RESAMPLING.bilinear)

    return up_rgb

def simple_mask(data, ndv):
    '''Exact nodata masking'''
    depth, rows, cols = data.shape
    nd = np.iinfo(data.dtype).max
    alpha = np.invert(np.all(np.dstack(data) == ndv, axis=2)).astype(data.dtype) * nd

    return alpha

def run_pansharpen(open_files, window, ij, g_args):
    """
    Reading input files and performing pansharpening on each window
    """
    pan = open_files[0].read(1, window=window).astype(np.float32)
    pan_dtype = open_files[0].meta['dtype']

    half_window = load_half_window(window)
    rgb = rios.utils.array_stack(
        [src.read(window=half_window).astype(np.float32) 
        for src in open_files[1:]])

    # Create a mask of pixels where any channel is 0 (nodata):
    color_mask = np.minimum(
        rgb[0],
        np.minimum(rgb[1], rgb[2])
    ) * 2 ** 16

    # Apply the mask:
    rgb = np.array([
        np.minimum(band, color_mask) for band in rgb
    ])

    if g_args["verb"]:
        click.echo('pan shape: %s, rgb shape %s' % (pan.shape, rgb[0].shape))

    fr_window_affine, to_window_affine = make_affine(pan.shape, rgb[0].shape)

    rgb = upsample(rgb, pan.shape, to_window_affine, g_args["r_crs"], fr_window_affine, g_args['dst_crs'])

    # Main Pansharpening Processing
    pan_sharpened, ratio = Brovey(rgb, pan, g_args["weight"], pan_dtype)

    ## convert to 8bit value range in place
    pan_sharpened /= (np.iinfo(np.uint16).max / np.iinfo(np.uint8).max)

    pan_sharpened = np.concatenate([pan_sharpened.astype(np.uint8), simple_mask(pan_sharpened.astype(np.uint8), (0, 0, 0)).reshape(1, pan_sharpened.shape[1], pan_sharpened.shape[2])])

    return pan_sharpened


def pansharpen(src_path, dst_path, weight, verbosity, processes, customwindow):
    """
    Pansharpening a landsat scene --
    Opening files, reading input meta data and writing the result
    of pansharpening into each window respentively.
    """
    with rio.open(src_path[0]) as pan_src:
        if customwindow:
            blocksize = adjust_block_size(pan_src.meta['width'], pan_src.meta['height'], int(customwindow))
            windows = [(window, (0,0)) for window in make_windows(pan_src.meta['width'], pan_src.meta['height'], blocksize)]
        else:
            windows = [(window, ij) for ij, window in pan_src.block_windows()]

        kwargs = pan_src.meta

        if kwargs['count'] > 1:
            raise NoRetry("Pan band must be 1 band - %s is %s" % (src_path[0], kwargs['count']))

        kwargs.update(transform=pan_src.affine)
        kwargs.update(compress='DEFLATE')
        kwargs.update(blockxsize=512)
        kwargs.update(blockysize=512)
        kwargs.update(dtype=np.uint8)
        kwargs.update(tiled=True)
        kwargs.update(count=4)
        kwargs.update(photometric='rgb')


    with rio.open(src_path[1]) as r_src:
        r_meta = r_src.meta

    if kwargs['width'] <= r_meta['width'] or kwargs['height'] <= r_meta['height']:
        raise NoRetry("Pan band %s is the same size (%s, %s) or smaller than RGB bands (%s, %s)" % (src_path[0], kwargs['height'], kwargs['width'], r_meta['height'], r_meta['width']))

    check_crs([r_meta, kwargs])

    g_args = {
        "verb": verbosity,
        "weight": weight,
        "dst_aff": kwargs['affine'],
        "dst_crs": kwargs['crs'],
        "r_aff": r_meta['affine'],
        "r_crs": r_meta['crs']
        }

    with rios.RioMucho(src_path, dst_path, run_pansharpen,
        windows=windows, global_args=g_args,
        options=kwargs, mode='manual_read') as rm:
        rm.run(10)


if __name__ == '__main__':
    pansharpen()