import click
from click.testing import CliRunner
from pansharpen.scripts.pan_cli import cli
import re


# test raise exception
def test_exception():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        input="'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B8.tif'\
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B4.tif'\
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B3.tif'\
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B2.tif'\
        'tests/expected/tiny_pan_sharp_output/tiny_20_LC81070352015122LGN00_output.tif' -c 100"
        )

    assert result.exception


def test_prompts():
    @click.command()
    @click.option('--src', prompt=True)
    def test(src):
        src_bands = re.findall(r"_B(?P<num_band>\d+).tif", src)
        click.echo(src_bands)

    runner = CliRunner()
    result = runner.invoke(
        test,
        input="'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B8.tif'"
        + " 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B4.tif'"
        + " 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B3.tif'"
        + " 'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B2.tif'"
        +" 'tests/expected/tiny_20_LC81070352015122LGN00_output.tif'"
        )
    assert not result.exception
    assert re.findall(r"'(?P<band_num>\d+)'", result.output)[0] == '8'

def test_prompts2():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B8.tif',
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B4.tif',
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B3.tif',
        'tests/fixtures/tiny_20_tiffs/LC81070352015122LGN00/LC81070352015122LGN00_B2.tif',
        'tests/expected/tiny_20_LC81070352015122LGN00_output.tif'])
    assert not result.exception
