## Comparison of Different Pansharpening Methods

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

#### IHS
The IHS transformation first converts the color image to IHS color space. It then replaces the intensity band by the a weighted version of the panchromatic image. Finally, the fused image is converted back to RGB space. IHS fused images generally experience spectral distortion from the original multispectral image. 

#### PCA:
The Principle Component Analysis (PCA) is a common statistical procedure that is used to reduce the dimensionality of multi-dimensional space. It is used for numerous applications in fields like statistics, machine learning, and signal processing.It is an orthogonal transformation that converts a set of correlated observations into a set of linearly uncorrelated values called principal components. This transformation leads to an interesting result - the first principal component accounts for the greatest proportion of variability in the data. 
In this case, it can be used to convert intercorrelated multispectral bands into a set of uncorrelated components.  The first band, which has the highest variance, is then replaced by the Panchromatic image.  We can then obtain the high-resolution pansharpened image by applying an inverse PCA on the PCA.


#### P+XS:
The P+XS is a variational method, which calculates the pansharpened image by minimizing an energy functional. It obtains the edge information of the panchromatic image by using the gradient. The spectral information is obtained by approximating the panchromatic image as a linear combination of the multispectral bands (Ballester, 2007). 

#### Wavelet:
The Wavelet method uses Discrete Wavelet Transforms (DWT) to decompose the original multispectral and panchromatic image into components. For each of the images, there is one component that contains low-resolution information, while the others contain more detailed local spatial information. The low-resolution component of the panchromatic image is replaced by the low-resolution multispectral component. The final image is created by performing an inverse wavelet transformation. 
Runtime in Theory: O(n)

![dwt1](https://cloud.githubusercontent.com/assets/4450007/7141344/da8b2cec-e285-11e4-9253-a3040b076bd2.jpg)

where cJk are the scaling coefficients and djk are the wavelet coefficients. The first term in Eq. (8) gives the low-resolution approximation of the signal while the second term gives the detailed information at resolutions from the original down to the current resolution J. The process of applying the DWT can be represented as a bandk of filters, as in the figure below.

![dwt_components](https://cloud.githubusercontent.com/assets/4450007/7141354/e990abcc-e285-11e4-984b-b35c22e18f6f.jpg)


In case of a 2D image, a single level decomposition can be performed resulting in four different frequency bands namely LL, LH, HL and HH sub band and an N level decomposition can be performed resulting in 3N+1 different frequency bands and it is shown in figure 3. At each level of decomposition, the image is split into high frequency and low frequency components; the low frequency components can be further decomposed until the desired resolution is reached.

#### VWP: 
VWP combines the Wavelet method with P+XS. It uses the geometry matching term from P+XS and spectral information from wavelet decomposition. This method outperforms others by preserving the highest spectral quality (Moeller, 2008).

#### Wavelet + Canny Edge Detector:
Combining DWT with Canny Edge Detectors. More details [here](http://link.springer.com/chapter/10.1007%2F978-3-642-21783-8_6).
