import pytest
import numpy as np
from hypothesis import given
import hypothesis.strategies as st
from hypothesis.extra.numpy import arrays
from rasterio.warp import reproject
from rio_pansharpen.methods import(
    calculateRatio, Brovey)
from rio_pansharpen.utils import(
    _adjust_block_size, _check_crs, _simple_mask,
    _pad_window, _create_apply_mask, _rescale,
    _make_windows, _make_affine, _half_window)


# Testing _calculateRatio function from methods
@given(arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max)
              ),
       arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max)
              ),
       st.floats(min_value=0.2, max_value=1.0))
def test_calculateRatio(rgb, pan, weight):
    output = pan / ((rgb[0] + rgb[1] + rgb[2] * weight) / (2 + weight))
    assert np.array_equal(output, calculateRatio(rgb, pan, weight))


# Testing Brovey function from methods
@given(arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max)
              ),
       arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max)
              ),
       st.floats(min_value=0.2, max_value=1.0),
       st.sampled_from(('uint8', 'uint16')))
def test_Brovey(rgb, pan, weight, pan_dtype):
    brovey_output, brovey_ratio = Brovey(rgb, pan, weight, pan_dtype)
    ratio = pan / ((rgb[0] + rgb[1] + rgb[2] * weight) / (2 + weight))
    output = np.clip(
                    ratio * rgb,
                    0,
                    np.iinfo(pan_dtype).max
                ).astype(pan_dtype)
    assert np.array_equal(brovey_output, output)
    assert np.array_equal(brovey_ratio, ratio)


# Testing _fix_window_size function from utils
@given(
    st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_fix_window_size(w, h, blocksize):
    if (w % blocksize == 1) or (h % blocksize == 1):
        assert _adjust_block_size(w, h, blocksize) == blocksize + 1
    else:
        assert _adjust_block_size(w, h, blocksize) == blocksize


# Testing _check_crs_function from utils
crs_strategy = st.lists(
                elements=st.dictionaries(
                    st.sampled_from(['crs']),
                    st.sampled_from(
                        ('EPSG:32654', 'EPSG:25832', 'EPSG:3857')
                    ),
                    min_size=1),
                min_size=2, max_size=2)


@given(crs_strategy)
def test_check_crs(crs_list):
        if crs_list[0]['crs'] != crs_list[1]['crs']:
            with pytest.raises(RuntimeError):
                _check_crs(crs_list)


# Testing _create_apply_mask function from utils
@given(arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max
                )
              )
       )
def test_create_apply_mask(rgb):
    color_mask = np.all(
            np.rollaxis(rgb, 0, 3) != 0,
            axis=2
        ).astype(np.uint16) * np.iinfo(np.uint16).max
    masked_rgb = _create_apply_mask(rgb)
    assert np.all(color_mask[color_mask != 0] <= np.iinfo(np.uint16).max)
    assert np.all(masked_rgb <= rgb)


# Testing _simple_mask function from utils
@given(arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max
                )
              ),
       st.integers(0, 0))
def test_simple_mask(data, ndv):
    '''Exact nodata masking'''
    nd = np.iinfo(data.dtype).max
    assert np.array_equal(
            _simple_mask(data, ndv),
            np.invert(
                np.all(
                    np.dstack(data) == ndv, axis=2
                    )
                ).astype(data.dtype) * nd)


# Testing _pad_window function from utils
@given(
        st.tuples(
            st.tuples(
                st.integers(), st.integers()),
            st.tuples(
                st.integers(), st.integers())
            ),
        st.integers()
    )
def test_pad_window(wnd, pad):
    assert _pad_window(wnd, pad)[0] == (wnd[0][0] - pad, wnd[0][1] + pad)
    assert _pad_window(wnd, pad)[1] == (wnd[1][0] - pad, wnd[1][1] + pad)


# Testing _rescale function from utils
@given(arrays(np.uint16, (3, 8, 8),
              elements=st.integers(
                min_value=1,
                max_value=np.iinfo('uint16').max
                )
              ),
       st.integers(0, 0),
       st.sampled_from(('uint16',
                        'uint8',
                        'int16',
                        'int8')))
def test_rescale(arr, ndv, dst_dtype):
    if dst_dtype == 'uint16':
        assert np.array_equal(
                _rescale(arr, ndv, dst_dtype),
                np.concatenate(
                    [
                        (arr).astype(dst_dtype),
                        _simple_mask(
                            arr.astype(dst_dtype),
                            (ndv, ndv, ndv)
                        ).reshape(1, arr.shape[1], arr.shape[2])
                    ]
                )
            )

    elif dst_dtype == 'int16':
        assert np.array_equal(
                _rescale(arr, ndv, dst_dtype),
                np.concatenate(
                    [
                        (arr / 2.000030518509476).astype(dst_dtype),
                        _simple_mask(
                            arr.astype(dst_dtype),
                            (ndv, ndv, ndv)
                        ).reshape(1, arr.shape[1], arr.shape[2])
                    ]
                )
            )

    elif dst_dtype == 'uint8':
        assert np.array_equal(
                _rescale(arr, ndv, dst_dtype),
                np.concatenate(
                    [
                        (arr / 257.0).astype(dst_dtype),
                        _simple_mask(
                            arr.astype(dst_dtype),
                            (ndv, ndv, ndv)
                        ).reshape(1, arr.shape[1], arr.shape[2])
                    ]
                )
            )

    elif dst_dtype == 'int8':
        assert np.array_equal(
                _rescale(arr, ndv, dst_dtype),
                np.concatenate(
                    [
                        (arr / 516.0236220472441).astype(dst_dtype),
                        _simple_mask(
                            arr.astype(dst_dtype),
                            (ndv, ndv, ndv)
                        ).reshape(1, arr.shape[1], arr.shape[2])
                    ]
                )
            )


# Testing make_windows_block function's random element
wh = st.integers(min_value=2, max_value=3500)


@given(
    wh,
    wh,
    wh)
def test_make_windows_full_block(w, h, blocksize):
    windows = list(_make_windows(w, h, blocksize))
    wind = np.random.randint(len(windows)/2 + 1)
    if wind < 2:
        assert windows[wind][0][1] - windows[wind][0][0] <= blocksize \
            and windows[wind][1][1] - windows[wind][1][0] <= blocksize
    else:
        assert windows[wind][0][1] - windows[wind][0][0] == blocksize \
            or windows[wind][1][1] - windows[wind][1][0] == blocksize


# Testing make_windows_block functon's last element
@given(
    wh,
    wh,
    wh)
def test_make_windows_last_block(w, h, blocksize):
    windows = list(_make_windows(w, h, blocksize))
    assert windows[-1][0][1] == h and windows[-1][1][1] == w
    assert windows[-1][0][1] - windows[-1][0][0] <= blocksize \
        and windows[-1][1][1] - windows[-1][1][0] <= blocksize


# Testing make_affine function
@given(
    st.tuples(st.integers(min_value=2), st.integers(min_value=2)),
    st.tuples(st.integers(min_value=2), st.integers(min_value=2)))
def test_make_affine(fr_shape, to_shape):
    fr_affine, to_affine = _make_affine(fr_shape, to_shape)
    assert to_affine[4] == -(fr_shape[0] / float(to_shape[0]))
    assert fr_affine[2] == float(0) and to_affine[2] == float(0)
    assert fr_affine[0] == float(1) and fr_affine[4] == -float(1)


# Testing _half_window function from utils
@given(
    st.tuples(
        st.tuples(
            st.integers(min_value=2),
            st.integers(min_value=2)).filter(lambda x: x[0] < x[1]),
        st.tuples(
            st.integers(min_value=2),
            st.integers(min_value=2)).filter(lambda x: x[0] < x[1])
        ).filter(lambda x: x[0] != x[1])
    )
def test_half_window(window):
    half_window = np.array(_half_window(window))
    assert np.all(map(lambda x: x[0] <= x[1], half_window))
    assert np.all((np.array(window) % half_window) <= 1)
    assert window[0][0]/half_window[0][0] == 2
    assert window[-1][-1]/half_window[-1][-1] == 2
