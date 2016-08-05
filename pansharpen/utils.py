#!/usr/bin/env python
# pylint: disable=E1120
from __future__ import division

import numpy as np
from affine import Affine
from rasterio.enums import Resampling
from rasterio.warp import reproject


def _adjust_block_size(width, height, blocksize):
    """Adjusts blocksize by adding 1 if the remainder
    from the division of height/width by blocksize is 1.
    """
    if width % blocksize == 1:
        blocksize += 1
    elif height % blocksize == 1:
        blocksize += 1
    return blocksize


def _make_windows(width, height, blocksize):
    """Manually makes windows of size equivalent to
    pan band image
    """
    for x in range(0, width, blocksize):
        for y in range(0, height, blocksize):
            yield ((y, min((y + blocksize), height)),
                   (x, min((x + blocksize), width)))


def _make_affine(fr_shape, to_shape):
    """Given from and to width and height,
    compute affine transform defining the
    georeferencing of the output array
    """
    fr_window_affine = Affine(
        1, 0, 0,
        0, -1, 0)

    to_window_affine = Affine(
        (fr_shape[1] / float(to_shape[1])), 0, 0,
        0, -(fr_shape[0] / float(to_shape[0])), 0)

    return fr_window_affine, to_window_affine


def _half_window(window):
    """Computes half window sizes
    """
    return tuple((w[0] / 2, w[1] / 2) for w in window)


def _check_crs(inputs):
    """Checks if crs of inputs are the same
    """
    for i in range(1, len(inputs)):
        if inputs[i-1]['crs'] != inputs[i]['crs']:
            raise RuntimeError(
                'CRS of inputs must be the same: '
                'received %s and %s' % (inputs[i-1]['crs'],
                                        inputs[i]['crs']))


def _create_apply_mask(rgb):
    """Create a mask of pixels where any channel is 0 (nodata),
    then apply the mask to input numpy array.
    """

    color_mask = np.all(
            np.rollaxis(rgb, 0, 3) != 0,
            axis=2
        ).astype(np.uint16) * np.iinfo(np.uint16).max

    masked_rgb = np.array([
        np.minimum(band, color_mask) for band in rgb])

    return masked_rgb


def _upsample(rgb, panshape, src_aff, src_crs, to_aff, to_crs):
    """upsamples rgb to the shape of the panchromatic band
    using reproject function from rasterio.warp
    """
    up_rgb = np.empty(
        (
            rgb.shape[0], panshape[0],
            panshape[1]), dtype=rgb.dtype
        )

    reproject(
        rgb, up_rgb,
        src_transform=src_aff,
        src_crs=src_crs,
        dst_transform=to_aff,
        dst_crs=to_crs,
        resampling=Resampling.bilinear)

    return up_rgb


def _simple_mask(data, ndv):
    '''Exact nodata masking'''
    nd = np.iinfo(data.dtype).max
    alpha = np.invert(
        np.all(np.dstack(data) == ndv, axis=2)
        ).astype(data.dtype) * nd

    return alpha


def _pad_window(wnd, pad):
    """Add padding to windows
    """
    return (
        (wnd[0][0] - pad, wnd[0][1] + pad),
        (wnd[1][0] - pad, wnd[1][1] + pad))


def _calc_windows(pan_src, customwindow):
    """Given raster data, pan_width, pan_height, and window size
    are used to compute and output appropriate windows
    """
    if customwindow != 0 and isinstance(customwindow, int):
        blocksize = _adjust_block_size(pan_src.meta['width'],
                                       pan_src.meta['height'],
                                       int(customwindow))
        windows = [(window, (0, 0))
                   for window in _make_windows(pan_src.meta['width'],
                                               pan_src.meta['height'],
                                               blocksize)]
    else:
        windows = [(window, ij) for ij, window in pan_src.block_windows()]

    return windows


def _rescale(arr, ndv, dst_dtype):
    """Convert an array from output dtype, scaling up linearly
    """
    if dst_dtype == np.__dict__['uint16']:
        scale = 1
    else:
        # convert to 8bit value range in place
        scale = float(np.iinfo(np.uint16).max) / float(np.iinfo(np.uint8).max)

    return np.concatenate(
                [
                    (arr / scale).astype(dst_dtype),
                    _simple_mask(
                        arr.astype(dst_dtype),
                        (ndv, ndv, ndv)
                    ).reshape(1, arr.shape[1], arr.shape[2])
                ]
            )
