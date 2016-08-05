# pansharpening
pansharpens Landsat 8 scenes.

## What is pansharpening?
Pansharpening is a process of using the spatial information in the high-resolution grayscale band (panchromatic, or pan-band) and color information in the multispectral bands to create a single high-resolution color image.

  ```P pan-pixel cluster + M single multispectral pixel = M pan-sharpened pixel```

Read more about pansharpening on the [Mapbox blog](https://www.mapbox.com/blog/l8-pansharpening/).

## Install

We highly recommend installing in a virtualenv. Once activated,
```
pip install -U pip
pip install pansharpening
```
Or install from source
```
git checkout https://github.com/mapbox/pansharpening.git
cd rio-toa
pip install -U pip
pip install -r requirements.txt
pip install -e .
```
## Python API
### `pansharpen.worker`
The `worker` module pansharpens Landsat 8. See more info on band designations for Landsat 8 on the [USGS Landsat page](http://landsat.usgs.gov/band_designations_landsat_satellites.php)

#### 1. `worker.pansharpen`
The `worker.pansharpen` function accepts the following as inputs:  
- numpy 3D array with shape == (3, vis_height, vis_width)
- affine transform defining the georeferencing of the vis array 
- numpy 2D with shape == (pan_height, pan_width)
- affine transform defining the georeferencing of the pan array 
- pansharpening method

and outputs:
- numpy 3D array with shape == (3, pan_height, pan_width)

```
>>> from pansharpen import worker
>>> from pansharpen.methods import Brovey
...
>>> pansharpened = worker.pansharpen(vis, vis_transform, pan, pan_transform,
                       pan_dtype, r_crs, dst_crs, weight,
                       method="Brovey", src_nodata=0)

```
#### 2.`worker.calculate_landsat_pansharpen`
```
>>> from pansharpen import worker
>>> from pansharpen.utils import _calc_windows
>>> import riomucho
...
>>> worker.calculate_landsat_pansharpen(src_paths, dst_path, dst_dtype,
        weight, verbosity, jobs, half_window,
        customwindow)
```

## `CLI`

### `pansharpen`

```
Usage: pansharpen [OPTIONS] [SRC_PATHS]... DST_PATH

  Pansharpens a landsat scene. Input is a panchromatic band (B8), plus 3 color
  bands (B4, B3, B2)

     pansharpen B8.tif B4.tif B3.tif B2.tif out.tif

  Or with shell expansion

     pansharpen LC80410332015283LGN00_B{8,4,3,2}.tif out.tif

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
```

======

## Comparison of Different Pansharpening Methods
We've implemented the Weighted Brovey Transform for pansharpening, which is appropriate for data like Landsat where the panchromatic band is relatively similar in resolution to the color bands.

For more information on other pansharpening methods such as IHS, PCA, P+XS, Wavelet, VWP, Wavelet with Canny Edge Detector etc, please read our notes [here]().

#### Brovey

The Brovey transformation is a sharpening method that uses a mathematical combination of the color image and high resolution data. Each resampled, multispectral pixel is multiplied by the ratio of the corresponding panchromatic pixel intensity to the sum of all the multispectral intensities. It assumes that the spectral range spanned by the panchromatic image is the same as that covered by the multispectral channels. This is done essentially by increasing the resolution of the color information in the data set to match that of the panchromatic band. Therefore, the output RGB images will have the pixel size of the input high-resolution panchromatic data. Various resampling methods include bilinear, lanczos, cubic, average, mode, min, and max.

#### Weighted Brovey

Particularly for Landsat 8 imagery data, we know that the pan-band does not include the full blue band, so we take a fraction of blue (optimal weight computed in this sprint) in the pan-band and use this weight to compute the sudo_pan_band, which is a weighted average of the three bands. We then compute the ratio between the pan-band and the sudo-band and adjust each of the three bands by this ratio.

```
sudo_pan = (R + B + B * weight)/(2 + weight)
ratio = pan / sudo_pan
R_out = R * ratio
G_out = G * ratio
B_out = B * ratio
```
![screen shot 2015-04-13 at 10 14 29 pm](https://cloud.githubusercontent.com/assets/4450007/7141761/7a277a88-e288-11e4-9dd7-39e3f970603f.png)






