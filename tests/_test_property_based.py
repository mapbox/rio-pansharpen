import pansharpen
import numpy as np
from hypothesis import given
import hypothesis.strategies as st


# Testing fix_window_size function
@given(
    st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_fix_window_size(w, h, blocksize):
    if (w % blocksize == 1) or (h % blocksize == 1):
        assert pansharpen.adjust_block_size(w, h, blocksize) == blocksize + 1
    else:
        assert pansharpen.adjust_block_size(w, h, blocksize) == blocksize

# Testing make_windows_block function's randow element
@given(
    st.integers(min_value=1),
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
@given(
    st.integers(min_value=1),
    st.integers(min_value=1),
    st.integers(min_value=1))
def test_make_windows_last_block(w, h, blocksize):
    windows = list(pansharpen.make_windows(w, h, blocksize))
    assert windows[-1][0][1] == h and windows[-1][1][1] == w
    assert windows[-1][0][1] - windows[-1][0][0] <= blocksize \
        and windows[-1][1][1] - windows[-1][1][0] <= blocksize

# Testing make_affine function
@given(
    st.tuples(st.integers(min_value=2), st.integers(min_value=2)),
    st.tuples(st.integers(min_value=2), st.integers(min_value=2)))
def test_make_affine(fr_shape, to_shape):
    fr_affine, to_affine = pansharpen.make_affine(fr_shape, to_shape)
    assert to_affine[4] == -(fr_shape[0] / float(to_shape[0]))
    assert fr_affine[2] == float(0) and to_affine[2] == float(0)
    assert fr_affine[0] == float(1) and fr_affine[4] == -float(1)

# Testing load_half_window function
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
def test_load_half_window(window):
    half_window = np.array(pansharpen.load_half_window(window))
    assert np.all(map(lambda x: x[0] <= x[1], half_window))
    assert np.all((window % half_window) <= 1)
