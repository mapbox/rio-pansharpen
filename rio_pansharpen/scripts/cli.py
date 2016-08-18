#!/usr/bin/env python

import click
from rio_pansharpen.worker import calculate_landsat_pansharpen


@click.command('pansharpen')
@click.argument('src_paths', type=click.Path(exists=True), nargs=-1)
@click.argument('dst_path', type=click.Path(exists=False), nargs=1)
@click.option('--dst-dtype',
              type=click.Choice(['int16', 'int8', 'uint16', 'uint8']),
              default='uint16')
@click.option('--ndv', default=None)
@click.option('--weight', '-w', default=0.2,
              help="Weight of blue band [default = 0.2]")
@click.option('--verbosity', '-v', is_flag=True)
@click.option('--jobs', '-j', default=1,
              help="Number of processes [default = 1]")
@click.option('--half-window',
              default=False,
              is_flag=True,
              help="Use a half window assuming pan "
              "in aligned with rgb bands, "
              "default: False")
@click.option('--customwindow', '-c',
              default=0,
              help="Specify blocksize for custom windows > 150"
              "[default=src_blockswindows]")
def pansharpen(src_paths, dst_path, dst_dtype,
               ndv, weight, verbosity, jobs,
               half_window, customwindow):
    """Pansharpens a landsat scene.
    Input is a panchromatic band, plus 3 color bands

       pansharpen B8.tif B4.tif B3.tif B2.tif out.tif

    Or with shell expansion

       pansharpen LC80410332015283LGN00_B{8,4,3,2}.tif out.tif
    """
    if customwindow != 0 and customwindow < 150:
        raise click.BadParameter(
            'custom blocksize must be greater than 150',
            param=customwindow, param_hint='--customwindow')

    return calculate_landsat_pansharpen(
        src_paths, dst_path, dst_dtype, ndv, weight, verbosity,
        jobs, half_window, customwindow
      )
