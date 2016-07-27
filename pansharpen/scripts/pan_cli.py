#!/usr/bin/env python

import click
from pansharpen.worker import pansharpen

@click.command('pansharpen')
@click.argument('src_paths', type=click.Path(exists=True), nargs=-1)
@click.argument('dst_path', type=click.Path(exists=False), nargs=1)
@click.option('--weight', '-w', default=0.2, help="Weight of blue ban [default = 0.2]")
@click.option('--verbosity', '-v', is_flag=True)
@click.option('--jobs', '-j', default=1, help="Number of processes [default = 1]")
@click.option('--customwindow', '-c', default=512,
              help="Specify blocksize for custom windows [default=src_blockswindows]")
def cli(src_paths, dst_path, weight, verbosity, jobs, customwindow):
    """Pansharpens a landsat scene.
    Input is a panchromatic band, plus 3 color bands

       pansharpen B8.tif B4.tif B3.tif B2.tif out.tif

    Or with shell expansion

       pansharpen LC80410332015283LGN00_B{8,4,3,2}.tif out.tif
    """
    if customwindow < 150:
        raise click.BadParameter(
            'custom blocksize must be greater than 150',
            param=customwindow, param_hint='--customwindow')

    return pansharpen(src_paths, dst_path, weight, verbosity, jobs, customwindow)

if __name__ == '__main__':
    cli()
