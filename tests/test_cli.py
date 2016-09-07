import re

import click
from click.testing import CliRunner
import pytest
import rasterio
from rio_pansharpen.scripts.cli import pansharpen


# test raise exception
def test_exception(tmpdir):
    output = str(tmpdir.join('wrong_customwindow.TIF'))
    runner = CliRunner()
    result = runner.invoke(
        pansharpen,
        ['tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B8.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B4.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B3.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B2.tif',
         output, '-c', '100'])

    assert result.exit_code != 0
    assert 'Error: Invalid value for --customwindow: ' \
        'custom blocksize must be greater than 150' in result.output


# test raise exception2
def test_exception2(tmpdir):
    output = str(tmpdir.join('wrong_customwindow.TIF'))
    runner = CliRunner()
    result = runner.invoke(
        pansharpen,
        ['tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B8.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B4.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B3.tif',
         'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
         'LC81070352015122LGN00_B2.tif',
         output, '-c', 'boo'])

    assert result.exit_code != 0
    assert 'Error: Invalid value for "--customwindow" ' \
        '/ "-c": boo is not a valid integer' in result.output


def test_prompts_success1(tmpdir):
    @click.command()
    @click.option('--src', prompt=True)
    def test(src):
        src_bands = re.findall(r"_B(?P<num_band>\d+).tif", src)
        click.echo(src_bands)

    output = str(tmpdir.join('test_src.TIF'))
    runner = CliRunner()
    result = runner.invoke(
        test,
        input="'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/" +
        "LC81070352015122LGN00_B8.tif tests/fixtures/tiny_20_tiffs/" +
        "LC81070352015122LGN00/LC81070352015122LGN00_B4.tif " +
        "tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/" +
        "LC81070352015122LGN00_B3.tif tests/fixtures/" +
        "tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B2.tif'" +
        output
        )
    assert result.exit_code == 0
    assert re.findall(r"'(?P<band_num>\d+)'", result.output)[0] == '8'


def test_prompt_success2(tmpdir):
    output = str(tmpdir.join('test_src.TIF'))
    runner = CliRunner()
    result = runner.invoke(
            pansharpen,
            ['tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
             'LC81070352015122LGN00_B8.tif',
             'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
             'LC81070352015122LGN00_B4.tif',
             'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
             'LC81070352015122LGN00_B3.tif',
             'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
             'LC81070352015122LGN00_B2.tif',
             output])
    assert result.exit_code == 0


@pytest.mark.parametrize('opt,expected', (
    ('--out-alpha', 4),
    ('--no-out-alpha', 3)))
def test_out_alpha_bands(tmpdir, opt, expected):
    output = str(tmpdir.join('test_src.TIF'))
    runner = CliRunner()
    result = runner.invoke(
        pansharpen, [
            'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
            'LC81070352015122LGN00_B8.tif',
            'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
            'LC81070352015122LGN00_B4.tif',
            'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
            'LC81070352015122LGN00_B3.tif',
            'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
            'LC81070352015122LGN00_B2.tif',
            opt,
            output])

    assert result.exit_code == 0

    with rasterio.open(output) as src:
        assert src.count == expected


def test_creation_opts(tmpdir):
    output = str(tmpdir.join('test_src.TIF'))
    runner = CliRunner()
    result = runner.invoke(
            pansharpen, [
                'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
                'LC81070352015122LGN00_B8.tif',
                'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
                'LC81070352015122LGN00_B4.tif',
                'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
                'LC81070352015122LGN00_B3.tif',
                'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/'
                'LC81070352015122LGN00_B2.tif',
                '--co', 'compress=jpeg',
                output])

    assert result.exit_code == 0
    with rasterio.open(output) as src:
        assert src.compression.value == 'JPEG'
