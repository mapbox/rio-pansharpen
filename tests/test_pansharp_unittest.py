import pytest
from rio_pansharpen import utils
import numpy as np
import rio_pansharpen.methods as pansharp_methods
import rasterio
from affine import Affine
from rio_pansharpen.worker import _pansharpen_worker
from rio_pansharpen.utils import _calc_windows


# Creating random test fixture for advance functions
@pytest.fixture
def test_data():
    test_data_pan = np.array([
        (np.random.rand(60, 60) * 255).astype(np.uint8)
        ])
    test_data_pan = test_data_pan[0]
    test_data_rgb = np.array([
        (np.random.rand(30, 30) * 255).astype(np.uint8)
        for i in range(3)
        ])
    test_data_src_aff = rasterio.Affine(2.0, 0.0, 0.0, 0.0, - 2.0, 0.0)
    test_data_src_crs = {'init': 'EPSG:3857'}
    test_data_dst_aff = rasterio.Affine(1.0, 0.0, 0.0, 0.0, - 1.0, 0.0)
    test_data_dst_crs = {'init': 'EPSG:3857'}

    return test_data_pan, test_data_rgb, test_data_src_aff,\
        test_data_src_crs, test_data_dst_aff, test_data_dst_crs


@pytest.fixture
def test_pansharp_data():
    b8_path = 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'\
              'LC81070352015122LGN00_B8.tif'
    b4_path = 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'\
              'LC81070352015122LGN00_B4.tif'
    b3_path = 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'\
              'LC81070352015122LGN00_B3.tif'
    b2_path = 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'\
              'LC81070352015122LGN00_B2.tif'
    band_paths = [b8_path, b4_path, b3_path, b2_path]
    pan_window = ((1536, 1792), (1280, 1536))
    g_args = {'half_window': False,
              'dst_aff': Affine(75.00483870967741, 0.0, 300892.5,
                                0.0, -75.00475285171103, 4107007.5),
              'verb': False, 'weight': 0.2,
              'dst_crs': {'init': u'epsg:32654'},
              'r_crs': {'init': u'epsg:32654'},
              'dst_dtype': 'uint16',
              'r_aff': Affine(150.0193548387097, 0.0, 300885.0,
                              0.0, -150.0190114068441, 4107015.0),
              'src_nodata': 0}

    return [rasterio.open(f) for f in band_paths],\
        pan_window, (6, 5), g_args


def test_calc_windows_customwindows(test_pansharp_data):
    open_files, pan_window, _, g_args = test_pansharp_data

    w = _calc_windows(open_files[0], 1024)
    assert w[0] == (((0, 1024), (0, 1024)), (0, 0))
    assert w[1] == (((1024, 2048), (0, 1024)), (0, 0))


def test_pansharpen_worker_uint16(test_pansharp_data):
    open_files, pan_window, _, g_args = test_pansharp_data
    pan_output = _pansharpen_worker(open_files, pan_window, _, g_args)
    assert pan_output.dtype == np.uint16
    assert np.max(pan_output) <= 2**16
    assert np.max(pan_output) >= 2**8


def test_pansharpen_worker_uint8(test_pansharp_data):
    open_files, pan_window, _, g_args = test_pansharp_data
    g_args.update(dst_dtype='uint8')
    pan_output = _pansharpen_worker(open_files, pan_window, _, g_args)
    assert pan_output.dtype == np.uint8
    assert np.max(pan_output) <= 2**8


# Testing reproject function
def test_reproject():
    from rasterio.warp import reproject
    from rasterio.enums import Resampling

    with rasterio.Env():
        # As source: a 1024 x 1024 raster centered on 0 degrees E and 0
        # degrees N, each pixel covering 15".
        rows, cols = src_shape = (1024, 1024)
        # decimal degrees per pixel
        d = 1.0 / 240

        # The following is equivalent to
        # A(d, 0, -cols*d/2, 0, -d, rows*d/2).
        src_transform = rasterio.Affine.translation(
                    -cols*d/2,
                    rows*d/2) * rasterio.Affine.scale(d, -d)
        src_crs = {'init': 'EPSG:4326'}
        source = np.ones(src_shape, np.uint8) * 255

        # Destination: a 2048 x 2048 dataset in Web Mercator (EPSG:3857)
        # with origin at 0.0, 0.0.
        dst_shape = (2048, 2048)
        dst_transform = Affine.from_gdal(
            -237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0)
        dst_crs = {'init': 'EPSG:3857'}
        destination = np.zeros(dst_shape, np.uint8)

        reproject(
            source,
            destination,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)

        # Assert that the destination is only partly filled.
        assert destination.any()
        assert not destination.all()


# Testing upsample function
def test_upsample(test_data):

    with rasterio.Env():

        pan, rgb, src_aff, src_crs, dst_aff, dst_crs = test_data
        up_rgb = utils._upsample(rgb, pan.shape, src_aff,
                                 src_crs, dst_aff, dst_crs)

        # test upsampled shape
        assert up_rgb.shape[0] == 3
        assert up_rgb.shape[1] / rgb.shape[1] == 2
        assert up_rgb.shape[2] / rgb.shape[2] == 2

        # test upsampled dtype
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
        (np.random.rand(60, 60) * 255).astype(np.uint8)
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
