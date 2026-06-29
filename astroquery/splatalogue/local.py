# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Offline Splatalogue queries against a local, CASA-hosted SQLite database.

CASA ships a curated SQLite snapshot of the Splatalogue database that its
``slsearch``/``sltotable`` tasks query entirely offline.  This module lets
astroquery point at that ``.db`` file directly (via :mod:`sqlite3`), so that
line searches keep working when ``splatalogue.online`` is slow or unreachable.

The snapshot is derived from the same Splatalogue database that backs the web
service.  Its line data lives in a ``main`` table, with species metadata
(``name``, ``chemical_name``) in a separate ``species`` table joined on
``species_id``, and the line list is stored as an integer ``ll_id`` rather than
a name.  This module introspects that layout at query time, performs the join,
maps ``ll_id`` onto the line-list names used by the web service, and returns a
table whose columns match an online query (so downstream helpers such as
`~astroquery.splatalogue.utils.minimize_table` work unchanged).

The exact table/column names vary between CASA releases; everything is
introspected and is overridable through ``table``/``column_mapping``.  Use
`describe_db` to print what was detected for a particular database.

Notes
-----
The bundled database is a snapshot and therefore lags the live site; it will
not contain the most recent CDMS/JPL updates.
"""
import os
import glob
import sqlite3

import numpy as np
from astropy import units as u
from astropy.table import Table

from . import conf

__all__ = ['find_local_db', 'query_local', 'describe_db',
           'LINELIST_ID_TO_NAME']


# Candidate names for the table holding the line data and the species metadata,
# tried in order when not configured explicitly.
MAIN_TABLE_CANDIDATES = ('main', 'lines', 'splatalogue')
SPECIES_TABLE_CANDIDATES = ('species',)

# The frequency column in the Splatalogue-derived database is stored in MHz
# (matching the web service's ``orderedfreq`` field, e.g. CO 1-0 = 115271 MHz).
DEFAULT_FREQUENCY_UNIT = u.MHz

# Splatalogue line-list id -> name. Determined against CASA's
# casadata splatalogue.db (verified line-by-line via slsearch and the live web
# service): ids 10/12/14/15 from slsearch, 11/18 from the web service.
LINELIST_ID_TO_NAME = {
    10: 'CDMS',
    11: 'LovasNIST',
    12: 'JPL',
    14: 'SLAIM',
    15: 'Recombination',
    18: 'TopModel',
}

# accepted spellings (case-insensitive) when filtering by line-list name
_LINELIST_NAME_ALIASES = {
    'lovas': 'lovasnist',
    'lovas/nist': 'lovasnist',
    'recomb': 'recombination',
}

# Mapping from the canonical (web) column name to candidate database column
# names.  The first candidate present in the database wins (case-insensitive).
COLUMN_CANDIDATES = {
    'species_id': ('species_id', 'SPECIES_ID'),
    'name': ('name', 'NAME', 'chemical_formula', 'SPECIES', 'formula'),
    'chemical_name': ('chemical_name', 'CHEMICAL_NAME'),
    'resolved_QNs': ('resolved_QNs', 'RESOLVED_QNS', 'quantum_numbers', 'QNS'),
    'linelist': ('linelist', 'LINELIST', 'catalog', 'CATALOG'),
    'linelist_id': ('ll_id', 'linelist_id', 'LL_ID'),
    'orderedfreq': ('orderedfreq', 'orderedFreq', 'frequency', 'FREQUENCY',
                    'freq', 'FREQ'),
    'measfreq': ('measfreq', 'measFreq', 'measured_freq', 'MEASURED_FREQ'),
    'lower_state_energy': ('lower_state_energy', 'LOWER_STATE_ENERGY', 'el'),
    'upper_state_energy': ('upper_state_energy', 'UPPER_STATE_ENERGY', 'eu'),
    'lower_state_energy_K': ('lower_state_energy_K', 'EL_K'),
    'upper_state_energy_K': ('upper_state_energy_K', 'EU_K'),
    'sijmu2': ('sijmu2', 'SIJMU2'),
    'sij': ('sij', 'SIJ'),
    'aij': ('aij', 'AIJ', 'log10_aij', 'LOG10_AIJ'),
    'intintensity': ('intintensity', 'INTINTENSITY', 'intensity'),
    'upperStateDegen': ('upperStateDegen', 'upper_state_degeneracy',
                        'UPPER_STATE_DEGENERACY'),
    'moleculeTag': ('moleculeTag', 'molecule_tag', 'MOLECULE_TAG'),
    'qnCode': ('qnCode', 'quantum_number_code', 'QUANTUM_NUMBER_CODE'),
}

# Map the public ``energy_type`` values onto the canonical energy columns.
_ENERGY_TYPE_TO_COLUMN = {
    'el_cm1': 'lower_state_energy',
    'eu_cm1': 'upper_state_energy',
    'el_k': 'lower_state_energy_K',
    'eu_k': 'upper_state_energy_K',
}

# Map the public ``intensity_type`` values onto the canonical intensity columns.
_INTENSITY_TYPE_TO_COLUMN = {
    'CDMS/JPL (log)': 'intintensity',
    'Sij-mu2': 'sijmu2',
    'Aij (log)': 'aij',
}


class SplatalogueDBError(IOError):
    """Raised when a local Splatalogue database cannot be found or read."""


def find_local_db(db_path=None):
    """
    Resolve the path to a local CASA-hosted Splatalogue SQLite database.

    The search order is:

    1. the ``db_path`` argument, if given;
    2. ``conf.db_path``;
    3. the ``CASA_SPLATALOGUE_DB`` environment variable;
    4. auto-discovery from a CASA / ``casaconfig`` installation.

    Parameters
    ----------
    db_path : str, optional
        Explicit path to the ``.db`` file.

    Returns
    -------
    path : str
        Path to an existing SQLite database file.

    Raises
    ------
    SplatalogueDBError
        If no database could be located.
    """
    candidates = []
    if db_path:
        candidates.append(db_path)
    if conf.db_path:
        candidates.append(conf.db_path)
    if os.environ.get('CASA_SPLATALOGUE_DB'):
        candidates.append(os.environ['CASA_SPLATALOGUE_DB'])

    for path in candidates:
        path = os.path.expanduser(path)
        if os.path.isfile(path):
            return path

    discovered = _discover_casa_db()
    if discovered:
        return discovered

    searched = '\n  '.join(candidates) if candidates else '(none provided)'
    raise SplatalogueDBError(
        "Could not locate a local Splatalogue SQLite database.\n"
        "Explicit candidates that were tried:\n  {searched}\n"
        "Set ``Splatalogue.conf.db_path`` (or the ``CASA_SPLATALOGUE_DB`` "
        "environment variable) to the CASA Splatalogue ``.db`` file, or "
        "install CASA/casaconfig so it can be discovered automatically. The "
        "file ships with CASA (casadata) under ``ephemerides/splatalogue.db``."
        .format(searched=searched))


def _candidate_data_roots():
    """Yield directories that may contain the CASA Splatalogue database."""
    roots = []
    # casadata ships the database; if importable, use its data directory
    try:
        import casadata
        roots.append(os.path.dirname(casadata.__file__))
    except Exception:
        pass
    # casaconfig exposes the measures/data path in a few different ways
    # depending on the version; try them all defensively.
    try:
        import casaconfig
        cfg = getattr(casaconfig, 'config', casaconfig)
        for attr in ('measurespath', 'datapath', 'rundata'):
            val = getattr(cfg, attr, None)
            if isinstance(val, str):
                roots.append(val)
            elif isinstance(val, (list, tuple)):
                roots.extend([v for v in val if isinstance(v, str)])
    except Exception:
        pass

    # common default locations
    roots += [os.path.expanduser('~/.casa/data'),
              os.path.expanduser('~/.casa'),
              os.path.expanduser('~/casadata')]
    seen = set()
    for r in roots:
        if r and r not in seen and os.path.isdir(r):
            seen.add(r)
            yield r


# the database sits at one of these subpaths relative to a CASA data root
# (the casadata package layout, the measures-data layout, or the root itself)
_DB_SUBPATHS = (
    ('__data__', 'ephemerides', 'splatalogue.db'),
    ('ephemerides', 'splatalogue.db'),
    ('splatalogue.db',),
)


def _fallback_glob_patterns():
    """Precise glob patterns (no recursive ``**``) for common CASA layouts."""
    home = os.path.expanduser('~')
    tail = ('lib/python*/site-packages/casadata/__data__/ephemerides/'
            'splatalogue.db')
    return [
        # macOS CASA application bundle
        '/Applications/CASA*.app/Contents/Frameworks/Python.framework/'
        'Versions/*/' + tail,
        # unpacked modular-CASA / monolithic distributions
        os.path.join(home, 'casa*', 'lib', 'py', tail),
        os.path.join(home, 'casa*', tail),
        os.path.join('/opt', 'casa*', 'lib', 'py', tail),
    ]


def _discover_casa_db():
    """Locate the Splatalogue ``.db`` file shipped with CASA.

    Tries the fast, known default locations first (exact paths under an
    importable ``casadata``/``casaconfig`` install or the usual data
    directories), then precise globs for common CASA install layouts, and
    only as a last resort does a recursive search of the data roots.
    """
    # 1. exact default locations -- no globbing
    for root in _candidate_data_roots():
        for sub in _DB_SUBPATHS:
            path = os.path.join(root, *sub)
            if os.path.isfile(path):
                return path

    # 2. precise globs for common CASA install layouts
    for pattern in _fallback_glob_patterns():
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]

    # 3. last resort: recursive search of the known data roots
    for root in _candidate_data_roots():
        for pattern in ('**/splatalogue*.db', '**/splat*.db'):
            hits = sorted(glob.glob(os.path.join(root, pattern), recursive=True))
            if hits:
                return hits[0]
    return None


def _list_tables(conn):
    return [row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]


def _columns(conn, table):
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def _detect_table(conn, configured=None):
    """Return the name of the table holding the line data."""
    tables = _list_tables(conn)
    if configured:
        if configured in tables:
            return configured
        raise SplatalogueDBError(
            f"Configured table {configured!r} not found in database; "
            f"available tables: {tables}")
    lower = {t.lower(): t for t in tables}
    for cand in MAIN_TABLE_CANDIDATES:
        if cand.lower() in lower:
            return lower[cand.lower()]
    # fall back to the largest non-species table
    non_species = [t for t in tables if t.lower() not in SPECIES_TABLE_CANDIDATES]
    if len(non_species) == 1:
        return non_species[0]
    raise SplatalogueDBError(
        "Could not determine which table holds the Splatalogue line data "
        f"(available tables: {tables}). Set ``Splatalogue.conf.local_table`` "
        "or pass ``table=`` explicitly.")


def _detect_species_table(conn, main_table):
    """Find a species-metadata table providing name/chemical_name, if any."""
    for table in _list_tables(conn):
        if table == main_table:
            continue
        cols = {c.lower() for c in _columns(conn, table)}
        if 'species_id' in cols and ('name' in cols or 'chemical_name' in cols):
            return table
    return None


def _resolve_columns(available, column_mapping=None):
    """Map canonical column name -> actual column name for ``available``."""
    lower = {c.lower(): c for c in available}
    candidates = dict(COLUMN_CANDIDATES)
    if column_mapping:
        for canonical, value in column_mapping.items():
            candidates[canonical] = (value,) if isinstance(value, str) else tuple(value)

    resolved = {}
    for canonical, options in candidates.items():
        for opt in options:
            if opt in available:
                resolved[canonical] = opt
                break
            if opt.lower() in lower:
                resolved[canonical] = lower[opt.lower()]
                break
    return resolved


def _linelist_names_to_ids(names):
    """Translate line-list names to ``ll_id`` integers (case-insensitive)."""
    inverse = {name.lower(): llid for llid, name in LINELIST_ID_TO_NAME.items()}
    ids, unknown = [], []
    for name in names:
        key = str(name).lower()
        key = _LINELIST_NAME_ALIASES.get(key, key)
        if key in inverse:
            ids.append(inverse[key])
        else:
            unknown.append(name)
    return ids, unknown


def describe_db(db_path=None, *, table=None):
    """
    Print and return the schema of a local Splatalogue database.

    Useful for confirming or building a ``column_mapping`` for an unfamiliar
    CASA database.

    Returns
    -------
    info : dict
        ``{'path', 'table', 'species_table', 'columns', 'resolved'}``.
    """
    path = find_local_db(db_path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tbl = _detect_table(conn, table or conf.local_table or None)
        cols = _columns(conn, tbl)
        resolved = _resolve_columns(cols)
        species_tbl = None
        if 'name' not in resolved or 'chemical_name' not in resolved:
            species_tbl = _detect_species_table(conn, tbl)
            if species_tbl:
                resolved = _resolve_columns(cols + _columns(conn, species_tbl))
    finally:
        conn.close()
    print(f"Splatalogue database: {path}")
    print(f"Line table: {tbl}" + (f"  (+ species table: {species_tbl})"
                                  if species_tbl else ""))
    print(f"Columns ({len(cols)}): {', '.join(cols)}")
    print("Resolved canonical -> database columns:")
    for canonical, actual in resolved.items():
        print(f"  {canonical:24s} -> {actual}")
    missing = [c for c in COLUMN_CANDIDATES if c not in resolved]
    if missing:
        print(f"Unmapped canonical columns: {', '.join(missing)}")
    return {'path': path, 'table': tbl, 'species_table': species_tbl,
            'columns': cols, 'resolved': resolved}


def query_local(*, min_frequency=None, max_frequency=None, species_ids=None,
                energy_min=None, energy_max=None, energy_type=None,
                intensity_lower_limit=None, intensity_type=None,
                line_lists=None, export_limit=None,
                db_path=None, table=None, column_mapping=None,
                frequency_unit=DEFAULT_FREQUENCY_UNIT,
                get_query_payload=False):
    """
    Query a local CASA-hosted Splatalogue SQLite database.

    The accepted filters mirror the subset of `SplatalogueClass.query_lines`
    parameters that map cleanly onto columns of the local database.  The
    returned table uses the same (web) column names as an online query.

    Parameters
    ----------
    min_frequency, max_frequency : `~astropy.units.Quantity`, optional
        Frequency (or spectral-equivalent) bounds.
    species_ids : list of (str or int), optional
        Restrict to these Splatalogue species id numbers.
    energy_min, energy_max : float, optional
        Energy bounds; the column they apply to is selected by ``energy_type``.
    energy_type : {'el_cm1', 'eu_cm1', 'el_k', 'eu_k'}, optional
    intensity_lower_limit : float, optional
        Lower limit on the intensity column selected by ``intensity_type``.
    intensity_type : {'CDMS/JPL (log)', 'Sij-mu2', 'Aij (log)'}, optional
    line_lists : list of str, optional
        Restrict to these line lists (names, e.g. ``['CDMS', 'JPL']``).
    export_limit : int, optional
        Maximum number of rows to return.
    db_path, table, column_mapping : optional
        Database location and schema overrides; see `find_local_db`/`describe_db`.
    frequency_unit : `~astropy.units.Unit`, optional
        Unit of the database frequency column (default MHz).
    get_query_payload : bool, optional
        If `True`, return ``(sql, parameters)`` instead of executing the query.

    Returns
    -------
    `~astropy.table.Table`
    """
    path = find_local_db(db_path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        main = _detect_table(conn, table or conf.local_table or None)
        main_cols = _columns(conn, main)
        cols = _resolve_columns(main_cols, column_mapping)

        # join a species table if name/chemical_name are not in the main table
        species_tbl, species_cols = None, []
        if 'name' not in cols or 'chemical_name' not in cols:
            species_tbl = _detect_species_table(conn, main)
            if species_tbl:
                species_cols = _columns(conn, species_tbl)
                cols = _resolve_columns(main_cols + species_cols, column_mapping)

        select, joins = _build_select(main, species_tbl, main_cols,
                                      species_cols, cols)
        where, params = _build_where(cols, frequency_unit,
                                     main_cols=main_cols,
                                     min_frequency=min_frequency,
                                     max_frequency=max_frequency,
                                     species_ids=species_ids,
                                     energy_min=energy_min,
                                     energy_max=energy_max,
                                     energy_type=energy_type,
                                     intensity_lower_limit=intensity_lower_limit,
                                     intensity_type=intensity_type,
                                     line_lists=line_lists)

        sql = f'SELECT {select} FROM "{main}" AS m{joins}'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        if 'orderedfreq' in cols:
            sql += f' ORDER BY m."{cols["orderedfreq"]}"'
        limit = export_limit if export_limit is not None else conf.lines_limit
        if limit:
            sql += ' LIMIT ?'
            params = params + [int(limit)]

        if get_query_payload:
            return sql, params

        cur = conn.execute(sql, params)
        names = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()

    return _rows_to_table(names, rows, cols, frequency_unit)


def _build_select(main, species_tbl, main_cols, species_cols, cols):
    """Build the SELECT column list and any JOIN clause."""
    select = 'm.*'
    joins = ''
    if species_tbl is not None:
        extra = []
        for canonical in ('name', 'chemical_name'):
            actual = cols.get(canonical)
            if actual and actual in species_cols and actual not in main_cols:
                extra.append(f's."{actual}" AS "{actual}"')
        if extra:
            select = 'm.*, ' + ', '.join(extra)
            joins = (f' LEFT JOIN "{species_tbl}" AS s '
                     f'ON m."{cols["species_id"]}" = s."{cols["species_id"]}"')
    return select, joins


def _build_where(cols, frequency_unit, *, main_cols, min_frequency,
                 max_frequency, species_ids, energy_min, energy_max,
                 energy_type, intensity_lower_limit, intensity_type, line_lists):
    where, params = [], []

    def mcol(canonical):
        # qualify main-table columns to avoid ambiguity with the species join
        return f'm."{cols[canonical]}"'

    if min_frequency is not None and max_frequency is not None:
        if 'orderedfreq' not in cols:
            raise SplatalogueDBError(
                "No frequency column found in the local database; cannot apply "
                f"a frequency filter. Resolved columns: {sorted(cols)}")
        fmin = min_frequency.to(frequency_unit, u.spectral()).value
        fmax = max_frequency.to(frequency_unit, u.spectral()).value
        if fmin > fmax:
            fmin, fmax = fmax, fmin
        where.append(f'{mcol("orderedfreq")} BETWEEN ? AND ?')
        params += [fmin, fmax]

    if species_ids and 'species_id' in cols:
        ids = [int(i) if str(i).lstrip('-').isdigit() else i for i in species_ids]
        placeholders = ','.join('?' * len(ids))
        where.append(f'{mcol("species_id")} IN ({placeholders})')
        params += ids

    if energy_type is not None and (energy_min is not None or energy_max is not None):
        canonical = _ENERGY_TYPE_TO_COLUMN.get(energy_type)
        if canonical in cols:
            if energy_min is not None:
                where.append(f'{mcol(canonical)} >= ?')
                params.append(float(energy_min))
            if energy_max is not None:
                where.append(f'{mcol(canonical)} <= ?')
                params.append(float(energy_max))

    if intensity_lower_limit is not None and intensity_type is not None:
        canonical = _INTENSITY_TYPE_TO_COLUMN.get(intensity_type)
        if canonical in cols:
            where.append(f'{mcol(canonical)} >= ?')
            params.append(float(intensity_lower_limit))

    if line_lists:
        if 'linelist' in cols:  # text line-list column present
            names = [str(ll).lower() for ll in line_lists]
            placeholders = ','.join('?' * len(names))
            where.append(f'LOWER({mcol("linelist")}) IN ({placeholders})')
            params += names
        elif 'linelist_id' in cols:  # integer ll_id, map names -> ids
            ids, unknown = _linelist_names_to_ids(line_lists)
            if unknown:
                import warnings
                warnings.warn(f"Unknown line list(s) ignored for the local "
                              f"database: {unknown}. Known: "
                              f"{sorted(LINELIST_ID_TO_NAME.values())}")
            if ids:
                placeholders = ','.join('?' * len(ids))
                where.append(f'{mcol("linelist_id")} IN ({placeholders})')
                params += ids

    return where, params


def _rows_to_table(names, rows, cols, frequency_unit):
    """Build a web-compatible Table from raw SQLite rows."""
    if rows:
        columns = {name: [row[i] for row in rows] for i, name in enumerate(names)}
    else:
        columns = {name: [] for name in names}
    table = Table(columns)

    # derive a web-style ``linelist`` name column from the integer ``ll_id``
    llid_col = cols.get('linelist_id')
    if llid_col and llid_col in table.colnames and 'linelist' not in table.colnames:
        table['linelist'] = [LINELIST_ID_TO_NAME.get(int(x), str(x))
                             if x is not None else x
                             for x in table[llid_col]]

    # rename database columns to their canonical (web) equivalents
    for canonical, actual in cols.items():
        if (actual in table.colnames and canonical != actual
                and canonical not in table.colnames):
            table.rename_column(actual, canonical)

    # express the frequency in MHz to match the web service's ``orderedfreq``
    if 'orderedfreq' in table.colnames and len(table) > 0:
        scale = (1 * frequency_unit).to(u.MHz).value
        if scale != 1:
            try:
                table['orderedfreq'] = np.asarray(table['orderedfreq'],
                                                  dtype=float) * scale
            except (TypeError, ValueError):
                pass

    return table
