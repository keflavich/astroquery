# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Offline tests: ADQL generation, argument validation and downloads."""

from unittest.mock import MagicMock

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table

from astroquery.exceptions import InvalidQueryError
from .. import LamostClass, LamostPreDR10Class, conf
from .helpers import DATA, create_mock_response

COORD = SkyCoord(160.5, 29.1, unit='deg')


@pytest.fixture
def client():
    return LamostClass(token='')


@pytest.fixture
def tap(client, monkeypatch):
    """Replace the TAP service by a mock that records the query."""
    service = MagicMock()
    service.run_sync.return_value.to_table.return_value = Table({'obsid': [1]})
    monkeypatch.setattr(client, '_tap', service)
    return service


def last_query(tap):
    return tap.run_sync.call_args.args[0]


def test_urls():
    lamost = LamostClass(data_release='dr11', sub_version='v1.0')
    assert lamost.tap_url == 'https://www.lamost.org/dr11/v1.0/voservice/tap'
    assert lamost.ssa_url == 'https://www.lamost.org/dr11/v1.0/voservice/ssap'


def test_defaults_from_conf():
    lamost = LamostClass()
    assert (lamost.data_release, lamost.sub_version) == (conf.data_release, conf.sub_version)


def test_query_tap(client, tap):
    client.query_tap('SELECT 1', maxrec=5)
    tap.run_sync.assert_called_once_with('SELECT 1', language='ADQL', maxrec=5)
    client.query_tap('SELECT 1', async_job=True)
    tap.run_async.assert_called_once()


def test_query_region(client, tap):
    result = client.query_region(COORD, 5 * u.arcsec)
    assert result['obsid'][0] == 1
    adql = last_query(tap)
    assert adql.startswith('SELECT TOP 1000 t.*, DISTANCE(')
    assert 'FROM "public".catalogue AS t' in adql
    assert "CIRCLE('ICRS', 160.5, 29.1, " in adql
    assert adql.endswith('ORDER BY separation')


def test_query_region_medium_and_columns(client):
    adql = client.query_region('10 +20', 0.1, resolution='medium', columns=['obsid', 'snr'],
                               max_rows=None, get_query_payload=True)
    assert adql.startswith('SELECT obsid, snr, DISTANCE(')
    assert '"public".med_catalogue' in adql and 'TOP' not in adql
    assert "CIRCLE('ICRS', 10.0, 20.0, 0.1)" in adql


def test_query_catalog_constraints(client):
    adql = client.query_catalog('stellar', constraints={'teff': (5000, 6000), 'snrg': (30, None), 'class': 'STAR'},
                                where="logg > 4", sort_by='teff', sort_order='desc', max_rows=7,
                                get_query_payload=True)
    assert adql == ('SELECT TOP 7 * FROM "public".stellar WHERE teff >= 5000 AND teff <= 6000 '
                    "AND snrg >= 30 AND class = 'STAR' AND (logg > 4) ORDER BY teff DESC")


def test_string_literals_are_escaped(client):
    adql = client.query_catalog('catalogue', constraints={'designation': "a'b"}, get_query_payload=True)
    assert "designation = 'a''b'" in adql


@pytest.mark.parametrize('kwargs', [
    {'catalog_name': 'x; DROP'},
    {'catalog_name': 'stellar', 'columns': ['a b']},
    {'catalog_name': 'stellar', 'columns': ['a', 'a']},
    {'catalog_name': 'stellar', 'constraints': {'a;': 1}},
    {'catalog_name': 'stellar', 'constraints': {'a': (None, None)}},
    {'catalog_name': 'stellar', 'constraints': {'a': float('nan')}},
    {'catalog_name': 'stellar', 'constraints': {'a': True}},
    {'catalog_name': 'stellar', 'coordinates': COORD},
    {'catalog_name': 'stellar', 'radius': 1},
    {'catalog_name': 'stellar', 'sort_by': 'a b'},
    {'catalog_name': 'stellar', 'sort_order': 'up'},
    {'catalog_name': 'stellar', 'page': 0},
    {'catalog_name': 'stellar', 'page': 2, 'max_rows': None},
    {'catalog_name': 'stellar', 'max_rows': 'some'},
    {'catalog_name': 'stellar', 'max_rows': 0},
])
def test_query_catalog_rejects_bad_input(client, kwargs):
    with pytest.raises(InvalidQueryError):
        client.query_catalog(get_query_payload=True, **kwargs)


@pytest.mark.parametrize('radius', [0, -1, float('nan'), 'abc', [1, 2]])
def test_bad_radius(client, radius):
    with pytest.raises(InvalidQueryError):
        client.query_region(COORD, radius, get_query_payload=True)


def test_bad_resolution(client):
    with pytest.raises(InvalidQueryError):
        client.query_region(COORD, 1, resolution='high', get_query_payload=True)


def test_query_spectra_low(client):
    adql = client.query_spectra(snr_min=20, teff_range=(5000, 6000), logg_range=(4, None),
                                get_query_payload=True)
    assert '"public".stellar' in adql
    assert 'snrg >= 20' in adql and 'teff >= 5000' in adql and 'logg >= 4' in adql


def test_query_spectra_medium(client):
    adql = client.query_spectra(COORD, 1, resolution='medium', snr_min=20, feh_range=(-1, 0),
                                get_query_payload=True)
    assert '"public".med_stellar' in adql
    assert 'snr >= 20' in adql and 'feh_lasp >= -1' in adql and 'feh_lasp <= 0' in adql


def test_query_spectra_without_stellar_cuts_uses_catalogue(client):
    adql = client.query_spectra(snr_min=20, get_query_payload=True)
    assert '"public".catalogue' in adql


def test_query_spectra_explicit_catalog(client):
    assert '"public".qso' in client.query_spectra(catalog_name='qso', get_query_payload=True)


def test_query_stellar_parameters(client):
    adql = client.query_stellar_parameters(resolution='medium', get_query_payload=True)
    assert adql.startswith('SELECT TOP 1000 obsid, ra, dec, teff_lasp, logg_lasp, feh_lasp, snr FROM')
    assert '"public".med_stellar' in adql


def test_get_metadata(client):
    adql = client.get_metadata(16011237, get_query_payload=True)
    assert adql == 'SELECT * FROM "public".catalogue WHERE obsid = 16011237'
    with pytest.raises(InvalidQueryError):
        client.get_metadata('1 OR 1=1', get_query_payload=True)


def test_repeat_observations_by_obsid(client):
    adql = client.query_repeat_observations(obsid='5', get_query_payload=True)
    assert 'uid IN (SELECT uid FROM "public".catalogue WHERE obsid = 5)' in adql


def test_repeat_observations_by_position(client):
    adql = client.query_repeat_observations(coordinates=COORD, radius=1 * u.arcsec, get_query_payload=True)
    assert 'CONTAINS' in adql


@pytest.mark.parametrize('kwargs', [
    {}, {'obsid': 1, 'coordinates': COORD}, {'coordinates': COORD}, {'obsid': 1, 'radius': 1},
])
def test_repeat_observations_validation(client, kwargs):
    with pytest.raises(InvalidQueryError):
        client.query_repeat_observations(get_query_payload=True, **kwargs)


def test_query_ssa(client, monkeypatch):
    service = MagicMock()
    service.search.return_value.to_table.return_value = Table({'accref': ['http://x']})
    monkeypatch.setattr(client, '_ssa', service)
    result = client.query_ssa(COORD, 0.025)
    assert result['accref'][0] == 'http://x'
    kwargs = service.search.call_args.kwargs
    assert kwargs['diameter'].to_value(u.deg) == pytest.approx(0.05)


def test_get_tables(client, tap):
    tap.tables = {'"public".catalogue': object()}
    assert list(client.get_tables()) == ['"public".catalogue']


# --------------------------------------------------------------- downloads
def test_spectrum_url_and_token():
    url = LamostClass(token='').get_spectrum_list(5)[0]
    assert url == 'https://www.lamost.org/openapi/dr10/v2.0/lrs/spectrum/fits?obsid=5'
    url = LamostClass(token='secret').get_spectrum_list(5, resolution='medium')[0]
    assert '/mrs/spectrum/fits?obsid=5&token=secret' in url


def test_get_spectra(client, monkeypatch):
    content = (DATA / 'spec-57278-EG224429N215706B01_sp01-001.fits.gz').read_bytes()
    request = MagicMock(return_value=create_mock_response(content=content, content_type='application/gzip'))
    monkeypatch.setattr(client, '_request', request)
    (hdul,) = client.get_spectra(5, verify='ignore')
    try:
        assert isinstance(hdul, fits.HDUList)
    finally:
        hdul.close()
    assert request.call_args.args[:2] == ('GET', client.get_spectrum_list(5)[0])


def test_get_spectra_http_error(client, monkeypatch):
    monkeypatch.setattr(client, '_request', MagicMock(return_value=create_mock_response(status_code=404)))
    with pytest.raises(Exception, match='404'):
        client.get_spectra(5)


def _download_response(content):
    response = create_mock_response(content=content)
    response.iter_content = lambda chunk_size: iter([content[:10], content[10:]])
    return response


def test_download_catalog(client, monkeypatch, tmp_path):
    content = (DATA / 'mrs_dr10_excerpt.fits.gz').read_bytes()
    monkeypatch.setattr(client, '_request', MagicMock(return_value=_download_response(content)))
    path = client.download_catalog('dr10_v2.0_LRS_plan.fits.gz', save_dir=tmp_path / 'sub')
    assert path.endswith('dr10_v2.0_LRS_plan.fits.gz')
    with open(path, 'rb') as f:
        assert f.read() == content


def test_download_catalog_rejects_non_fits(client, monkeypatch, tmp_path):
    monkeypatch.setattr(client, '_request', MagicMock(return_value=_download_response(b'{"error": "nope"}')))
    with pytest.raises(OSError):
        client.download_catalog('x.fits.gz', save_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_catalog_no_overwrite(client, monkeypatch, tmp_path):
    existing = tmp_path / 'x.fits.gz'
    existing.write_bytes(b'old')
    request = MagicMock()
    monkeypatch.setattr(client, '_request', request)
    assert client.download_catalog('x.fits.gz', save_dir=tmp_path, overwrite=False) == str(existing)
    request.assert_not_called()


# -------------------------------------------------------------- pagination
def test_pagination_offset_and_default_order(client):
    adql = client.query_catalog('catalogue', max_rows=50, page=3, get_query_payload=True)
    assert adql == 'SELECT TOP 50 * FROM "public".catalogue ORDER BY obsid OFFSET 100'


def test_first_page_has_no_offset(client):
    adql = client.query_catalog('catalogue', max_rows=50, page=1, get_query_payload=True)
    assert adql == 'SELECT TOP 50 * FROM "public".catalogue ORDER BY obsid'


def test_pagination_respects_sort_and_cone(client):
    adql = client.query_catalog('catalogue', max_rows=5, page=2, sort_by='snrg', sort_order='desc',
                                get_query_payload=True)
    assert adql.endswith('ORDER BY snrg DESC OFFSET 5')
    adql = client.query_region(COORD, 1, max_rows=5, page=2, get_query_payload=True)
    assert adql.endswith('ORDER BY separation OFFSET 5')


def test_no_page_means_no_forced_order(client):
    assert 'ORDER BY' not in client.query_catalog('catalogue', get_query_payload=True)


def test_max_rows_all(client):
    assert 'TOP' not in client.query_catalog('catalogue', max_rows='all', get_query_payload=True)


def test_nearest_only(client):
    adql = client.query_spectra(COORD, 1, nearest_only=True, snr_min=10, max_rows=50, get_query_payload=True)
    assert adql.startswith('SELECT TOP 1 ') and 'ORDER BY separation' in adql and 'snrg >= 10' in adql


@pytest.mark.parametrize('kwargs', [{'nearest_only': True}, {'nearest_only': 1},
                                    {'nearest_only': True, 'coordinates': COORD, 'radius': 1, 'page': 2}])
def test_nearest_only_validation(client, kwargs):
    with pytest.raises(InvalidQueryError):
        client.query_spectra(get_query_payload=True, **kwargs)


# --------------------------------------------------------- pre-DR10 fallback
LEGACY = dict(data_release='dr7', sub_version='v2.0')


@pytest.mark.parametrize('release, version, legacy', [
    ('dr10', 'v2.0', False), ('dr11', 'v1.0', False), ('dr12', 'v1.0', False),
    ('dr10', 'v1.0', True), ('dr9', 'v2.0', True), ('dr3', 'v2.0', True), ('dr7', 'v0', True),
])
def test_release_dispatch(release, version, legacy):
    assert LamostClass(token='', data_release=release, sub_version=version)._use_legacy is legacy


def test_legacy_property_is_synced():
    lamost = LamostClass(token='', **LEGACY)
    assert isinstance(lamost.legacy, LamostPreDR10Class)
    lamost.data_release, lamost.sub_version = 'dr8', 'v1.1'
    assert (lamost.legacy.data_release, lamost.legacy.sub_version) == ('dr8', 'v1.1')


def test_token_precedence_is_shared(monkeypatch):
    monkeypatch.setenv('ASTROQUERY_NADC_LAMOST_TOKEN', 'envtoken')
    assert LamostClass().token == 'envtoken'
    assert LamostClass(token='explicit').token == 'explicit'
    assert LamostClass(token='').token is None


@pytest.mark.parametrize('method, args', [
    ('query_tap', ('SELECT 1',)), ('get_tables', ()), ('query_ssa', (COORD, 1)),
])
def test_vo_only_methods_raise_for_legacy_releases(method, args):
    with pytest.raises(NotImplementedError, match='VO service'):
        getattr(LamostClass(token='', **LEGACY), method)(*args)


def test_legacy_query_region_payload():
    payload = LamostClass(token='', **LEGACY).query_region(COORD, 5 * u.arcsec, get_query_payload=True)
    assert payload['ra'] == pytest.approx(160.5)
    assert payload['sr'] == pytest.approx(5 / 3600)


def test_legacy_query_region_results(monkeypatch):
    lamost = LamostClass(token='', **LEGACY)
    seen = {}

    def fake(coordinates, radius, *, resolution, get_query_payload=False):
        seen.update(radius=radius, resolution=resolution)
        return Table({'obsid': [1, 2, 3], 'ra': [1., 2., 3.]})

    monkeypatch.setattr(lamost.legacy, 'query_region', fake)
    result = lamost.query_region(COORD, 0.5, resolution='medium', columns='obsid', max_rows=2)
    assert result.colnames == ['obsid'] and len(result) == 2
    assert seen['radius'].to_value(u.deg) == 0.5 and seen['resolution'] == 'medium'
    with pytest.raises(InvalidQueryError, match='page'):
        lamost.query_region(COORD, 0.5, page=2)


def test_legacy_query_catalog_translates_arguments(monkeypatch):
    lamost = LamostClass(token='', **LEGACY)
    calls = []
    monkeypatch.setattr(lamost.legacy, 'query_catalog', lambda name, **kw: calls.append((name, kw)) or Table())
    lamost.query_catalog('catalogue', coordinates=COORD, radius=5 * u.arcsec,
                         constraints={'snrg': (30, None), 'class': 'STAR'}, columns=['obsid'],
                         sort_by='snrg', sort_order='desc', max_rows=None, page=2)
    name, kw = calls[0]
    assert name == 'catalogue'
    assert kw['column_constraints'] == [
        {'column_name': 'snrg', 'operation': 'between', 'min': 30},
        {'column_name': 'class', 'operation': 'equal', 'constraint': 'STAR'}]
    assert kw['position_constraints']['cone']['radius'] == pytest.approx(5.0)
    assert (kw['max_rows'], kw['page'], kw['sort_by'], kw['sort_order']) == ('all', 2, 'snrg', 'desc')
    with pytest.raises(InvalidQueryError, match='TAP'):
        lamost.query_catalog('catalogue', where='x > 1')


def test_legacy_query_spectra_and_stellar_delegate(monkeypatch):
    lamost = LamostClass(token='', **LEGACY)
    calls = []
    for name in ('query_spectra', 'query_stellar_parameters'):
        monkeypatch.setattr(lamost.legacy, name, lambda *a, _n=name, **kw: calls.append((_n, a, kw)) or Table())
    lamost.query_spectra(COORD, 1, snr_min=10, teff_range=(5000, 6000), nearest_only=True)
    lamost.query_stellar_parameters(snr_min=10)
    assert calls[0][0] == 'query_spectra' and calls[0][2]['teff_range'] == (5000, 6000)
    assert calls[0][1][1].to_value(u.deg) == 1 and calls[0][2]['nearest_only'] is True
    assert calls[1][0] == 'query_stellar_parameters'
    assert calls[1][2]['columns'][:3] == ['obsid', 'ra', 'dec']


def test_legacy_metadata_and_repeat(monkeypatch):
    lamost = LamostClass(token='', **LEGACY)
    monkeypatch.setattr(lamost.legacy, 'get_metadata', lambda obsid, **kw: Table({'obsid': [obsid]}))
    assert lamost.get_metadata('12')['obsid'][0] == 12
    monkeypatch.setattr(lamost.legacy, 'query_repeat_observations',
                        lambda **kw: {'unique_id': 'L1', 'related_obsids': ['5', '6']})
    result = lamost.query_repeat_observations(obsid=5)
    assert list(result['obsid']) == [5, 6] and list(result['uid']) == ['L1', 'L1']
    monkeypatch.setattr(lamost.legacy, 'query_repeat_observations',
                        lambda **kw: {'unique_id': None, 'related_obsids': []})
    assert len(lamost.query_repeat_observations(obsid=5)) == 0


def test_legacy_downloads_delegate(monkeypatch):
    lamost = LamostClass(token='', **LEGACY)
    url = lamost.get_spectrum_list(5, resolution='medium')[0]
    assert url == lamost.legacy.get_spectrum_list(5, resolution='medium')[0]
    monkeypatch.setattr(lamost.legacy, 'get_spectra', lambda *a, **kw: ['spectrum'])
    monkeypatch.setattr(lamost.legacy, 'download_catalog', lambda *a, **kw: 'path')
    assert lamost.get_spectra(5) == ['spectrum']
    assert lamost.download_catalog('x') == 'path'
