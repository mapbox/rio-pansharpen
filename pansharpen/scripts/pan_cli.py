#!/usr/bin/env python

import click
import pansharpen

@click.command('Pansharpen')
@click.argument('src_path', type=click.Path(exists=True), nargs=-1)
@click.argument('dst_path', type=click.Path(exists=False), nargs=1)
@click.option('--weight', '-w', default=0.2, help="Weight of blue ban [default = 0.2]")
@click.option('--verbosity', '-v', is_flag=True)
@click.option('--processes', '-p', default=4, help="Number of processes [default = 4]")
@click.option('--customwindow', '-c', default=1024, help="Specify blocksize for custom windows [default=src_blockswindows]")
def cli(src_path, dst_path, weight, verbosity, processes, customwindow):
    """Pansharpens a landsat scene"""
    if customwindow < 150:
    	raise click.BadParameter('custom blocksize must be greater than 150',
    		param=customwindow, param_hint='--customwindow')

    return pansharpen.pansharpen(src_path, dst_path, weight, verbosity, processes, customwindow)

if __name__ == '__main__':
    cli()