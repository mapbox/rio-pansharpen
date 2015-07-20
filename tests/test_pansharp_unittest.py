import pytest
import pansharpen
import numpy as np
import pansharpen.scripts.pansharp_methods as pansharp_methods
import rasterio
from hypothesis import given
import hypothesis.strategies as st

"""
Test Basic functions
"""

# Testing fix_window_size function
@given(st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_fix_window_size(w, h, blocksize):
    if (w % blocksize == 1) or (h % blocksize == 1):
        assert pansharpen.adjust_block_size(w, h, blocksize) == blocksize + 1
    else: 
        assert pansharpen.adjust_block_size(w, h, blocksize) == blocksize

# Testing make_windows_block function's randow element
@given(st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_make_windows_full_block(w, h, blocksize):
    windows = list(pansharpen.make_windows(w, h, blocksize))
    wind = np.random.randint(len(windows)/2 + 1)
    if wind < 2:
        assert windows[wind][0][1] - windows[wind][0][0] <= blocksize \
            and windows[wind][1][1] - windows[wind][1][0] <= blocksize
    else:
        assert windows[wind][0][1] - windows[wind][0][0] == blocksize \
            or windows[wind][1][1] - windows[wind][1][0] == blocksize

# Testing make_windows_block functon's last element
@given(st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_make_windows_last_block(w, h, blocksize):
    windows = list(pansharpen.make_windows(w, h, blocksize))
    assert windows[-1][0][1] == h and windows[-1][1][1] == w
    assert windows[-1][0][1] - windows[-1][0][0] <= blocksize \
        and windows[-1][1][1] - windows[-1][1][0] <= blocksize

# Testing make_affine function
@given(st.tuples(st.integers(min_value=2), st.integers(min_value=2)),
    st.tuples(st.integers(min_value=2), st.integers(min_value=2)))
def test_make_affine(fr_shape, to_shape):
    fr_affine, to_affine = pansharpen.make_affine(fr_shape,to_shape)
    assert to_affine[4] == -(fr_shape[0] / float(to_shape[0]))
    assert fr_affine[2] == float(0) and to_affine[2] == float(0)
    assert fr_affine[0] == float(1) and fr_affine[4] == -float(1)

# Testing load_half_window function
@given(st.tuples(
        st.tuples(
            st.integers(min_value=2),
            st.integers(min_value=2)).filter(lambda x: x[0] < x[1]),
        st.tuples(
            st.integers(min_value=2),
            st.integers(min_value=2)).filter(lambda x: x[0] < x[1])
        ).filter(lambda x: x[0] != x[1])
    )
def test_load_half_window(window):
    half_window = np.array(pansharpen.load_half_window(window))
    assert np.all(map(lambda x: x[0] <= x[1], half_window))
    assert np.all((window % half_window) <= 1)


"""
Test advance functions
"""

# Creating random test fixture for advance functions
@pytest.fixture
def test_data():
    test_data_pan = np.array([
        (np.random.rand(60,60)* 255).astype(np.uint8)
        ])
    test_data_pan = test_data_pan[0]
    test_data_rgb = np.array([
        (np.random.rand(30,30)* 255).astype(np.uint8)
        for i in range(3)
        ])
    test_data_src_aff = rasterio.Affine(2.0, 0.0, 0.0, 0.0, -2.0, 0.0)
    test_data_src_crs =  {'init': 'EPSG:3857'}
    test_data_dst_aff = rasterio.Affine(1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    test_data_dst_crs =  {'init': 'EPSG:3857'}

    return test_data_pan, test_data_rgb, test_data_src_aff,\
            test_data_src_crs, test_data_dst_aff, test_data_dst_crs

# Testing reproject function
def test_reproject():
    from rasterio.warp import reproject, RESAMPLING

    with rasterio.drivers():
        # As source: a 1024 x 1024 raster centered on 0 degrees E and 0
        # degrees N, each pixel covering 15".
        rows, cols = src_shape = (1024, 1024)
        d = 1.0/240 # decimal degrees per pixel
        # The following is equivalent to
        # A(d, 0, -cols*d/2, 0, -d, rows*d/2).
        src_transform = rasterio.Affine.translation(-cols*d/2, rows*d/2)\
                        * rasterio.Affine.scale(d, -d)
        src_crs = {'init': 'EPSG:4326'}
        source = np.ones(src_shape, np.uint8)* 255

        # Destination: a 2048 x 2048 dataset in Web Mercator (EPSG:3857)
        # with origin at 0.0, 0.0.
        dst_shape = (2048, 2048)
        dst_transform = [-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0]
        dst_crs = {'init': 'EPSG:3857'}
        destination = np.zeros(dst_shape, np.uint8)

        reproject(
            source,
            destination,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)

        # Assert that the destination is only partly filled.
        assert destination.any()
        assert not destination.all()

# Testing upsample function
def test_upsample(test_data):

    with rasterio.drivers():

        pan, rgb, src_aff, src_crs, dst_aff, dst_crs = test_data
        up_rgb = pansharpen.upsample(rgb, pan.shape, src_aff, 
                                    src_crs, dst_aff, dst_crs)

        # test upsampled shape
        assert up_rgb.shape[0] == 3
        assert up_rgb.shape[1] / rgb.shape[1] == 2
        assert up_rgb.shape[2] / rgb.shape[2] == 2

        #test upsampled dtype
        assert up_rgb.dtype == np.uint8

        # test for seams. 1 px wide row/column with 0's
        assert np.all((up_rgb[0].max(axis=0)) != 0)
        assert np.all((up_rgb[0].max(axis=1)) != 0)
        assert np.all((up_rgb[1].max(axis=0)) != 0)
        assert np.all((up_rgb[1].max(axis=1)) != 0)
        assert np.all((up_rgb[2].max(axis=0)) != 0)
        assert np.all((up_rgb[2].max(axis=1)) != 0)

        # test upsampled values from reproject function
        assert up_rgb[0][0][0] == rgb[0][0][0]
        assert up_rgb[-1][-1][-1] == rgb[-1][-1][-1]

# Testing Brovey function from pansharp_methods
def test_brovey(test_data):
    pan, rgb, src_aff, src_crs, dst_aff, dst_crs = test_data
    up_rgb = np.array([
        (np.random.rand(60,60)* 255).astype(np.uint8)
        for i in range(3)
        ])
    pan_sharpened, ratio = pansharp_methods.Brovey(up_rgb, pan, 0.5, pan.dtype)
    # Testing pan_sharpened shape
    assert pan_sharpened.shape[0] == 3
    assert pan_sharpened.shape[1] / rgb.shape[1] == 2
    assert pan_sharpened.shape[2] / rgb.shape[2] == 2

    # Testing pan_sharpened shape
    assert pan_sharpened.dtype == np.uint8

    # Testing for seams on all 3 bands.
    # up_rgb does not contain 1 px wide row/column with 0's
    assert np.all((up_rgb[0].max(axis=0)) != 0)
    assert np.all((up_rgb[0].max(axis=1)) != 0)
    assert np.all((up_rgb[1].max(axis=0)) != 0)
    assert np.all((up_rgb[1].max(axis=1)) != 0)
    assert np.all((up_rgb[2].max(axis=0)) != 0)
    assert np.all((up_rgb[2].max(axis=1)) != 0)
