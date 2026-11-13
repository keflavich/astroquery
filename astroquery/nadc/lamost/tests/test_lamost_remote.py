# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Tests against the live LAMOST DR10 services."""

import pytest
from astropy.coordinates import SkyCoord
from astropy.table import Table

from .. import LamostClass, parse_lrs_spectrum

pytestmark = pytest.mark.remote_data

COORD = SkyCoord(160.5, 29.1, unit='deg')
OBSID = 16011237


@pytest.fixture(scope='module')
def lamost():
    return LamostClass(data_release='dr10', sub_version='v2.0')


def test_tap_tables(lamost):
    assert '"public".catalogue' in lamost.get_tables()


def test_query_region(lamost):
    result = lamost.query_region(COORD, 0.05, columns=['obsid', 'ra', 'dec'])
    assert isinstance(result, Table)
    assert OBSID in result['obsid']
    assert result['separation'][0] <= result['separation'][-1] <= 0.05


def test_query_region_medium(lamost):
    result = lamost.query_region(COORD, 0.5, resolution='medium', max_rows=5)
    assert 'obsid' in result.colnames


def test_query_stellar_parameters(lamost):
    result = lamost.query_stellar_parameters(teff_range=(5000, 5100), snr_min=50, max_rows=5)
    assert 0 < len(result) <= 5
    assert (result['teff'] >= 5000).all() and (result['snrg'] >= 50).all()


def test_get_metadata(lamost):
    assert lamost.get_metadata(OBSID)['obsid'][0] == OBSID


def test_repeat_observations(lamost):
    result = lamost.query_repeat_observations(obsid=OBSID)
    assert OBSID in result['obsid'] and len(set(result['uid'])) == 1


def test_query_ssa(lamost):
    result = lamost.query_ssa(COORD, 0.025)
    assert OBSID in result['obsid']
    assert result['accref'][0].startswith('http')


def test_get_spectra_and_reader(lamost, tmp_path):
    (hdul,) = lamost.get_spectra(OBSID, verify='ignore')
    path = tmp_path / 'spec.fits'
    hdul.writeto(path, output_verify='ignore')
    hdul.close()
    wavelength, flux = parse_lrs_spectrum(path)
    assert wavelength.shape == flux.shape and wavelength.size > 1000


def test_tap_dr12():
    lamost = LamostClass(data_release='dr12', sub_version='v1.0')
    assert any('catalogue' in name for name in lamost.get_tables())
