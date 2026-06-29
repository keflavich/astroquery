# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os
import sqlite3

import pytest
import requests

from astropy import units as u

from astroquery import splatalogue
from astroquery.splatalogue import conf, local
from astroquery.splatalogue.core import SplatalogueWebFailWarning
from astroquery.splatalogue.local import SplatalogueDBError


# A small synthetic database that mimics the CASA Splatalogue SQLite schema.
# Frequencies are in MHz, matching the web service's ``orderedfreq`` field.
_ROWS = [
    # species_id, name, chemical_name, resolved_QNs, linelist, orderedfreq(MHz),
    # aij, sijmu2, lower_state_energy, upper_state_energy,
    # lower_state_energy_K, upper_state_energy_K
    ('990', 'CO v=1', 'Carbon Monoxide', ' 1- 0', 'CDMS', 114221.7523,
     -7.37879, 0.00723, 2143.27, 2147.08, 3083.67, 3089.15),
    ('204', 'CO', 'Carbon Monoxide', ' 1- 0', 'CDMS', 115271.2018,
     -7.142, 0.012, 0.0, 3.845, 0.0, 5.53),
    ('204', 'CO', 'Carbon Monoxide', ' 2- 1', 'SLAIM', 230538.0,
     -6.0, 0.024, 3.845, 11.06, 5.53, 16.6),
    ('1343', 'CCO', 'Dicarbon monoxide', ' 5- 4', 'JPL', 115275.0,
     -5.0, 1.0, 10.0, 20.0, 14.4, 28.8),
]

_COLUMNS = ['species_id', 'name', 'chemical_name', 'resolved_QNs', 'linelist',
            'orderedfreq', 'aij', 'sijmu2', 'lower_state_energy',
            'upper_state_energy', 'lower_state_energy_K', 'upper_state_energy_K']


@pytest.fixture
def local_db(tmp_path):
    db = tmp_path / "splatalogue_v3.db"
    conn = sqlite3.connect(str(db))
    _text_cols = ('species_id', 'name', 'chemical_name', 'resolved_QNs', 'linelist')
    coldefs = ", ".join(f"{c} {'TEXT' if c in _text_cols else 'REAL'}"
                        for c in _COLUMNS)
    conn.execute(f"CREATE TABLE main ({coldefs})")
    conn.executemany(
        "INSERT INTO main VALUES ({})".format(",".join("?" * len(_COLUMNS))), _ROWS)
    conn.commit()
    conn.close()
    with conf.set_temp('db_path', str(db)):
        yield str(db)


def test_find_local_db_explicit(local_db):
    assert local.find_local_db() == local_db
    assert local.find_local_db(local_db) == local_db


def test_find_local_db_missing(tmp_path, monkeypatch):
    # nothing configured and nothing discoverable -> informative error
    monkeypatch.delenv('CASA_SPLATALOGUE_DB', raising=False)
    monkeypatch.setattr(local, '_discover_casa_db', lambda: None)
    with conf.set_temp('db_path', ''):
        with pytest.raises(SplatalogueDBError, match="Could not locate"):
            local.find_local_db()


def test_describe_db(local_db, capsys):
    info = local.describe_db()
    assert info['table'] == 'main'
    assert info['resolved']['orderedfreq'] == 'orderedfreq'
    assert set(_COLUMNS).issubset(info['columns'])
    assert "Resolved canonical" in capsys.readouterr().out


def test_frequency_filter(local_db):
    t = local.query_local(min_frequency=114 * u.GHz, max_frequency=116 * u.GHz)
    # three lines fall in 114-116 GHz (114221, 115271, 115275 MHz)
    assert len(t) == 3
    assert set(t.colnames) == set(_COLUMNS)
    # output frequency is in MHz, matching the web service
    assert min(t['orderedfreq']) == pytest.approx(114221.7523)
    # ordered by frequency
    assert list(t['orderedfreq']) == sorted(t['orderedfreq'])


def test_frequency_filter_reversed(local_db):
    t = local.query_local(min_frequency=116 * u.GHz, max_frequency=114 * u.GHz)
    assert len(t) == 3


def test_species_filter(local_db):
    t = local.query_local(min_frequency=0 * u.GHz, max_frequency=300 * u.GHz,
                          species_ids=['204'])
    assert set(t['species_id']) == {'204'}
    assert len(t) == 2


def test_line_list_filter(local_db):
    t = local.query_local(min_frequency=0 * u.GHz, max_frequency=300 * u.GHz,
                          line_lists=['SLAIM'])
    assert list(t['linelist']) == ['SLAIM']


def test_energy_filter(local_db):
    t = local.query_local(min_frequency=0 * u.GHz, max_frequency=300 * u.GHz,
                          energy_max=10, energy_min=0, energy_type='eu_k')
    assert t['upper_state_energy_K'].max() <= 10


def test_get_query_payload(local_db):
    sql, params = local.query_local(min_frequency=114 * u.GHz,
                                    max_frequency=116 * u.GHz,
                                    get_query_payload=True)
    assert 'BETWEEN ? AND ?' in sql
    assert params[:2] == [114000.0, 116000.0]


def test_column_mapping_override(tmp_path):
    # a database with non-standard column names is handled via column_mapping
    db = tmp_path / "weird.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE lines (FREQUENCY REAL, SPECIES TEXT)")
    conn.executemany("INSERT INTO lines VALUES (?,?)",
                     [(115271.2, 'CO'), (230538.0, 'CO')])
    conn.commit()
    conn.close()
    t = local.query_local(min_frequency=115 * u.GHz, max_frequency=116 * u.GHz,
                          db_path=str(db), table='lines',
                          column_mapping={'orderedfreq': 'FREQUENCY',
                                          'name': 'SPECIES'})
    assert len(t) == 1
    assert 'orderedfreq' in t.colnames and 'name' in t.colnames


# --- integration with the SplatalogueClass routing -----------------------

def test_query_lines_always_local(local_db):
    t = splatalogue.Splatalogue.query_lines(
        min_frequency=114 * u.GHz, max_frequency=116 * u.GHz, use_local='always')
    assert len(t) == 3
    assert 'orderedfreq' in t.colnames


def test_query_lines_always_local_chemical_name(local_db):
    # chemical_name is resolved to species ids entirely offline
    t = splatalogue.Splatalogue.query_lines(
        min_frequency=114 * u.GHz, max_frequency=300 * u.GHz,
        chemical_name=' CO ', use_local='always')
    assert set(t['species_id']).issubset({'204', '990', '991', '1343'})


def test_fallback_on_timeout(local_db, monkeypatch):
    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectTimeout("simulated timeout")

    monkeypatch.setattr(splatalogue.Splatalogue, 'query_lines_async', boom)
    with pytest.warns(SplatalogueWebFailWarning, match="falling back"):
        t = splatalogue.Splatalogue.query_lines(
            min_frequency=114 * u.GHz, max_frequency=116 * u.GHz,
            use_local='fallback')
    assert len(t) == 3


def test_never_reraises_timeout(local_db, monkeypatch):
    def boom(*args, **kwargs):
        raise requests.exceptions.ReadTimeout("simulated timeout")

    monkeypatch.setattr(splatalogue.Splatalogue, 'query_lines_async', boom)
    with pytest.raises(requests.exceptions.Timeout):
        splatalogue.Splatalogue.query_lines(
            min_frequency=114 * u.GHz, max_frequency=116 * u.GHz,
            use_local='never')


def test_fallback_unavailable_reraises(monkeypatch):
    # web fails AND no local db -> original web error surfaces
    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("no network")

    monkeypatch.setattr(splatalogue.Splatalogue, 'query_lines_async', boom)
    monkeypatch.setattr(local, '_discover_casa_db', lambda: None)
    monkeypatch.delenv('CASA_SPLATALOGUE_DB', raising=False)
    with conf.set_temp('db_path', ''):
        with pytest.raises(requests.exceptions.ConnectionError):
            splatalogue.Splatalogue.query_lines(
                min_frequency=114 * u.GHz, max_frequency=116 * u.GHz,
                use_local='fallback')


def test_resolve_use_local():
    s = splatalogue.Splatalogue
    assert s._resolve_use_local(True) == 'always'
    assert s._resolve_use_local(False) == 'never'
    assert s._resolve_use_local('fallback') == 'fallback'
    with pytest.raises(ValueError):
        s._resolve_use_local('bogus')


# --- the real CASA schema: main + species join, integer ll_id line lists ----

@pytest.fixture
def casa_like_db(tmp_path):
    """A database that mirrors CASA's schema (separate species table, ll_id)."""
    db = tmp_path / "splatalogue.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE species (species_id INTEGER, name TEXT, "
                 "chemical_name TEXT)")
    conn.executemany("INSERT INTO species VALUES (?,?,?)", [
        (990, 'CO v=1', 'Carbon Monoxide'),
        (204, 'CO', 'Carbon Monoxide'),
        (638, 'NH3 v=0', 'Ammonia')])
    conn.execute("CREATE TABLE main (ll_id INTEGER, species_id INTEGER, "
                 "orderedfreq REAL, aij REAL, resolved_QNs TEXT, "
                 "upper_state_energy_K REAL, upper_state_degeneracy INTEGER)")
    conn.executemany("INSERT INTO main VALUES (?,?,?,?,?,?,?)", [
        (14, 990, 114221.757, -7.15, ' 1- 0', 3089.15, 3),    # SLAIM
        (10, 204, 115271.202, -7.14, ' 1- 0', 5.53, 3),       # CDMS
        (12, 204, 230538.0, -6.0, ' 2- 1', 16.6, 5),          # JPL
        (18, 638, 15231.6896, -8.0, ' 8(1)0a-8(1)0s', 1500.0, 1)])  # TopModel
    conn.commit()
    conn.close()
    with conf.set_temp('db_path', str(db)):
        yield str(db)


def test_casa_schema_join_and_linelist(casa_like_db):
    info = local.describe_db()
    assert info['table'] == 'main'
    assert info['species_table'] == 'species'
    assert info['resolved']['linelist_id'] == 'll_id'

    t = local.query_local(min_frequency=114 * u.GHz, max_frequency=116 * u.GHz)
    # name/chemical_name come from the joined species table
    assert 'name' in t.colnames and 'chemical_name' in t.colnames
    assert set(t['chemical_name']) == {'Carbon Monoxide'}
    # ll_id is mapped to a web-style line-list name
    assert set(t['linelist']) == {'SLAIM', 'CDMS'}
    # upper_state_degeneracy is renamed to the web column name
    assert 'upperStateDegen' in t.colnames


def test_casa_schema_linelist_name_filter(casa_like_db):
    # filtering by name maps to the integer ll_id
    t = local.query_local(min_frequency=100 * u.GHz, max_frequency=300 * u.GHz,
                          line_lists=['JPL'])
    assert list(t['linelist']) == ['JPL']
    # case-insensitive alias: 'Lovas' -> LovasNIST (none here -> empty, no error)
    t2 = local.query_local(min_frequency=100 * u.GHz, max_frequency=300 * u.GHz,
                           line_lists=['CDMS'])
    assert set(t2['linelist']) == {'CDMS'}


def test_casa_schema_unknown_linelist_warns(casa_like_db):
    with pytest.warns(UserWarning, match="Unknown line list"):
        local.query_local(min_frequency=100 * u.GHz, max_frequency=300 * u.GHz,
                          line_lists=['NotAList'])


def test_casa_schema_payload_has_join(casa_like_db):
    sql, params = local.query_local(min_frequency=114 * u.GHz,
                                    max_frequency=116 * u.GHz,
                                    get_query_payload=True)
    assert 'LEFT JOIN "species"' in sql


def test_linelist_id_mapping_is_complete():
    # the six line lists present in the CASA casadata splatalogue.db
    assert local.LINELIST_ID_TO_NAME == {
        10: 'CDMS', 11: 'LovasNIST', 12: 'JPL',
        14: 'SLAIM', 15: 'Recombination', 18: 'TopModel'}


# --- validation against a real CASA database, if one is installed -----------

# exercise the production discovery (fast: exact paths + precise globs)
_REAL_DB = (os.environ.get('CASA_SPLATALOGUE_DB')
            if os.path.isfile(os.environ.get('CASA_SPLATALOGUE_DB') or '')
            else local._discover_casa_db())


@pytest.mark.skipif(_REAL_DB is None,
                    reason="no local CASA Splatalogue database found")
def test_real_casa_db():
    from astroquery.splatalogue.utils import minimize_table
    with conf.set_temp('db_path', _REAL_DB):
        t = splatalogue.Splatalogue.query_lines(
            114 * u.GHz, 116 * u.GHz, chemical_name=' CO ', use_local='always')
        assert len(t) > 0
        assert set(t['chemical_name']) == {'Carbon Monoxide'}
        # frequencies are reported in MHz, within the requested band
        assert t['orderedfreq'].min() >= 114000
        assert t['orderedfreq'].max() <= 116000
        # line lists are mapped to known names
        assert set(t['linelist']).issubset(set(local.LINELIST_ID_TO_NAME.values()))
        # the result is a drop-in for the web table
        assert 'Freq' in minimize_table(t).colnames
