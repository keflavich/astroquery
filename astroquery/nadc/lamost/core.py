# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
LAMOST Spectroscopic Survey Query Tool
=======================================

Catalog queries use the IVOA services (TAP and SSAP) that LAMOST publishes for
each data release, accessed through `pyvo`. Spectrum and catalog-file
downloads use the LAMOST OpenAPI file endpoints.
"""

import os
import re
import tempfile
from io import BytesIO
from urllib.parse import urlencode

import astropy.coordinates as coord
import astropy.units as u
import numpy as np
from astropy.io import fits
from pyvo.dal import SSAService, TAPService

from ...exceptions import InvalidQueryError
from ...query import BaseQuery
from ...utils import commons
from . import conf


__all__ = ['Lamost', 'LamostClass',
           'parse_lrs_spectrum', 'parse_mrs_spectrum']


# Table names in the ``public`` TAP schema for each spectral resolution.
_CATALOGUE = {'low': 'catalogue', 'medium': 'med_catalogue'}
_STELLAR = {'low': 'stellar', 'medium': 'med_stellar'}

# Column names used by the quality filters of `LamostClass.query_spectra`.
_SPECTRAL_FIELDS = {
    'low': {'snr': 'snrg', 'teff': 'teff', 'logg': 'logg', 'feh': 'feh'},
    'medium': {'snr': 'snr', 'teff': 'teff_lasp', 'logg': 'logg_lasp', 'feh': 'feh_lasp'},
}

_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$')


def _identifier(name, what='column'):
    """Validate an ADQL identifier so user input cannot alter the query."""
    if not isinstance(name, str) or not _IDENTIFIER.match(name):
        raise InvalidQueryError(f'{what} must be a plain identifier, got {name!r}.')
    return name


def _literal(value):
    """Format a Python value as an ADQL literal."""
    if isinstance(value, (bool, np.bool_)):
        raise InvalidQueryError('Boolean constraint values are not supported.')
    if isinstance(value, (int, float, np.integer, np.floating)):
        if not np.isfinite(value):
            raise InvalidQueryError('Constraint values must be finite.')
        return repr(value.item() if hasattr(value, 'item') else value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise InvalidQueryError(f'Unsupported constraint value {value!r}.')


def _constraint_clauses(constraints):
    """Translate ``{column: value | (low, high)}`` into ADQL conditions."""
    clauses = []
    for column, value in (constraints or {}).items():
        column = _identifier(column)
        if isinstance(value, (tuple, list)):
            if len(value) != 2 or all(v is None for v in value):
                raise InvalidQueryError(f'{column}: ranges are (low, high) with at least one bound.')
            low, high = value
            if low is not None:
                clauses.append(f'{column} >= {_literal(low)}')
            if high is not None:
                clauses.append(f'{column} <= {_literal(high)}')
        else:
            clauses.append(f'{column} = {_literal(value)}')
    return clauses


class LamostClass(BaseQuery):
    """
    Class for querying the LAMOST spectroscopic survey.

    Tables are queried with ADQL through the TAP service of the selected data
    release, and positions with SSAP, using `pyvo`. Spectra and catalog
    files are downloaded from the LAMOST OpenAPI.

    The VO services exist for DR10 and later. Older releases can still be used
    for `get_spectra` and `download_catalog`.

    Parameters
    ----------
    token : str, optional
        Token appended to download requests for releases that require one.
        Defaults to ``conf.token``. TAP and SSAP queries are anonymous.
    data_release : str, optional
        Data release (e.g. ``'dr10'``). Defaults to ``conf.data_release``.
    sub_version : str, optional
        Release sub-version (e.g. ``'v2.0'``). Defaults to ``conf.sub_version``.

    Examples
    --------
    >>> from astroquery.nadc.lamost import LamostClass
    >>> lamost = LamostClass(data_release='dr10', sub_version='v2.0')
    """

    def __init__(self, *, token=None, data_release=None, sub_version=None):
        super().__init__()
        self.token = (conf.token if token is None else token) or None
        self.data_release = data_release or conf.data_release
        self.sub_version = sub_version or conf.sub_version
        self._tap = None
        self._ssa = None

    # ------------------------------------------------------------------ URLs
    @property
    def _release_url(self):
        return f'{conf.vo_server.rstrip("/")}/{self.data_release}/{self.sub_version}'

    @property
    def tap_url(self):
        """TAP endpoint of the selected data release."""
        return f'{self._release_url}/voservice/tap'

    @property
    def ssa_url(self):
        """SSAP endpoint of the selected data release."""
        return f'{self._release_url}/voservice/ssap'

    @property
    def tap(self):
        """`pyvo.dal.TAPService` for the selected data release."""
        if self._tap is None:
            self._tap = TAPService(self.tap_url, session=self._session)
        return self._tap

    @property
    def ssa(self):
        """`pyvo.dal.SSAService` for the selected data release."""
        if self._ssa is None:
            self._ssa = SSAService(self.ssa_url, session=self._session)
        return self._ssa

    @staticmethod
    def _normalize_resolution(resolution):
        normalized = str(resolution).strip().lower()
        if normalized not in _CATALOGUE:
            raise InvalidQueryError("resolution must be one of: low, medium.")
        return normalized

    @staticmethod
    def _radius_deg(radius):
        """Convert ``radius`` (bare numbers are degrees) to a positive float in degrees."""
        try:
            angle = coord.Angle(radius, unit=u.deg)
            value = angle.to_value(u.deg)
            if not angle.isscalar or not np.isfinite(value) or value <= 0:
                raise ValueError
        except (TypeError, ValueError, u.UnitsError) as error:
            raise InvalidQueryError(
                'radius must be a finite positive scalar angle; bare numbers are in degrees.'
            ) from error
        return float(value)

    # ------------------------------------------------------------------ TAP
    def query_tap(self, query, *, async_job=False, maxrec=None):
        """
        Send an ADQL query to the LAMOST TAP service.

        Parameters
        ----------
        query : str
            ADQL query. Table names in the main schema must be written
            ``"public".catalogue``, ``"public".stellar``, etc.
        async_job : bool, optional
            Run the query as an asynchronous TAP job (for long queries).
        maxrec : int, optional
            Maximum number of records to return.

        Returns
        -------
        result : `~pyvo.dal.TAPResults`
            Use ``.to_table()`` for an `~astropy.table.Table`.
        """
        if async_job:
            return self.tap.run_async(query, language='ADQL', maxrec=maxrec)
        return self.tap.run_sync(query, language='ADQL', maxrec=maxrec)

    def get_tables(self):
        """
        Describe the tables published by the TAP service.

        Returns
        -------
        dict
            Mapping of table name to `pyvo.io.vosi.vodataservice.VOSITable`,
            whose ``columns`` give column names, units and descriptions.
        """
        return dict(self.tap.tables)

    def _run(self, adql, *, get_query_payload, verbose=False):
        if get_query_payload:
            return adql
        table = self.query_tap(adql).to_table()
        self.table = table
        return table

    @staticmethod
    def _select(columns):
        if columns is None:
            return '*'
        columns = [columns] if isinstance(columns, str) else list(columns)
        if not columns or len(set(columns)) != len(columns):
            raise InvalidQueryError('columns must be a non-empty sequence of unique names.')
        return ', '.join(_identifier(c) for c in columns)

    @staticmethod
    def _top(max_rows):
        if max_rows is None:
            return ''
        if isinstance(max_rows, (bool, np.bool_)) or not isinstance(max_rows, (int, np.integer)) or max_rows < 1:
            raise InvalidQueryError('max_rows must be a positive integer or None.')
        return f'TOP {int(max_rows)} '

    @staticmethod
    def _contains(coordinates, radius_deg):
        c = commons.parse_coordinates(coordinates).icrs
        center = f'{c.ra.deg!r}, {c.dec.deg!r}'
        condition = (f"1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {center}, {radius_deg!r}))")
        separation = f"DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', {center}))"
        return condition, separation

    def query_catalog(self, catalog_name, *, coordinates=None, radius=None, constraints=None,
                      where=None, columns=None, order_by=None, descending=False,
                      max_rows=1000, get_query_payload=False):
        """
        Query a table of the LAMOST database with simple constraints.

        Parameters
        ----------
        catalog_name : str
            Table name in the ``public`` schema, e.g. ``'catalogue'``,
            ``'stellar'``, ``'med_catalogue'``; see `get_tables`.
        coordinates : str or `~astropy.coordinates.SkyCoord`, optional
            Cone center. Requires ``radius``. Without ``order_by`` the cone
            results are ordered by distance from the center.
        radius : str, float or `~astropy.units.Quantity`, optional
            Cone radius; bare numbers are degrees.
        constraints : dict, optional
            ``{column: value}`` for equality, or ``{column: (low, high)}`` for
            an inclusive range (either bound may be `None`). All are combined
            with AND.
        where : str, optional
            Additional raw ADQL condition, combined with AND.
        columns : str or sequence of str, optional
            Columns to return. Default: all.
        order_by : str, optional
            Column to sort by.
        descending : bool, optional
            Sort in descending order.
        max_rows : int or None, optional
            Maximum number of rows (default 1000); `None` for no limit.
        get_query_payload : bool, optional
            Return the ADQL query string instead of running it.

        Returns
        -------
        `~astropy.table.Table` or str
        """
        if (coordinates is None) != (radius is None):
            raise InvalidQueryError('coordinates and radius must be provided together.')
        table = f'"public".{_identifier(catalog_name, "catalog_name")}'
        clauses = _constraint_clauses(constraints)
        order = ''
        if order_by is not None:
            order = f' ORDER BY {_identifier(order_by)}{" DESC" if descending else ""}'
        select_extra = ''
        if coordinates is not None:
            condition, separation = self._contains(coordinates, self._radius_deg(radius))
            clauses.insert(0, condition)
            if order_by is None:
                select_extra = f', {separation} AS separation'
                order = ' ORDER BY separation'
        if where:
            clauses.append(f'({where})')
        select = self._select(columns)
        if select_extra and select != '*':
            select += select_extra
        elif select_extra:
            # ADQL 2.0 does not allow a bare ``*`` next to other select items.
            select = f't.*{select_extra}'
        adql = f'SELECT {self._top(max_rows)}{select} FROM {table}'
        if select.startswith('t.*'):
            adql += ' AS t'
        if clauses:
            adql += ' WHERE ' + ' AND '.join(clauses)
        adql += order
        return self._run(adql, get_query_payload=get_query_payload)

    def query_region(self, coordinates, radius, *, resolution='low', columns=None,
                     max_rows=1000, get_query_payload=False):
        """
        Cone search of the LAMOST spectral catalogue.

        Parameters
        ----------
        coordinates : str or `~astropy.coordinates.SkyCoord`
            Cone center.
        radius : str, float or `~astropy.units.Quantity`
            Cone radius; bare numbers are degrees.
        resolution : {"low", "medium"}, optional
            Low-resolution (LRS) or medium-resolution (MRS) catalogue.
        columns : str or sequence of str, optional
            Columns to return. Default: all.
        max_rows : int or None, optional
            Maximum number of rows (default 1000); `None` for no limit.
        get_query_payload : bool, optional
            Return the ADQL query string instead of running it.

        Returns
        -------
        `~astropy.table.Table` or str
            Rows sorted by distance, with a ``separation`` column in degrees.
        """
        return self.query_catalog(
            _CATALOGUE[self._normalize_resolution(resolution)],
            coordinates=coordinates, radius=radius, columns=columns,
            max_rows=max_rows, get_query_payload=get_query_payload)

    def query_spectra(self, coordinates=None, radius=None, *, resolution='low', catalog_name=None,
                      snr_min=None, teff_range=None, logg_range=None, feh_range=None,
                      columns=None, order_by=None, descending=False, max_rows=1000,
                      get_query_payload=False):
        """
        Query spectral catalog rows with common quality filters.

        Parameters
        ----------
        coordinates, radius : optional
            Cone search; see `query_catalog`.
        resolution : {"low", "medium"}, optional
            Selects the catalogue (and the names of the SNR and stellar
            parameter columns). Stellar-parameter cuts use the ``stellar`` /
            ``med_stellar`` table, otherwise ``catalogue`` / ``med_catalogue``.
        catalog_name : str, optional
            Explicit table name, overriding the default choice.
        snr_min : float, optional
            Minimum signal-to-noise ratio (``snrg`` for LRS, ``snr`` for MRS).
        teff_range, logg_range, feh_range : (low, high), optional
            Inclusive ranges in K, dex (log10 cm/s2) and dex ([Fe/H]).
        columns, order_by, descending, max_rows, get_query_payload : optional
            See `query_catalog`.

        Returns
        -------
        `~astropy.table.Table` or str
        """
        resolution = self._normalize_resolution(resolution)
        fields = _SPECTRAL_FIELDS[resolution]
        constraints = {}
        if snr_min is not None:
            constraints[fields['snr']] = (snr_min, None)
        stellar = False
        for key, rng in (('teff', teff_range), ('logg', logg_range), ('feh', feh_range)):
            if rng is not None:
                constraints[fields[key]] = tuple(rng)
                stellar = True
        if catalog_name is None:
            catalog_name = (_STELLAR if stellar else _CATALOGUE)[resolution]
        return self.query_catalog(
            catalog_name, coordinates=coordinates, radius=radius, constraints=constraints,
            columns=columns, order_by=order_by, descending=descending,
            max_rows=max_rows, get_query_payload=get_query_payload)

    def query_stellar_parameters(self, coordinates=None, radius=None, *, resolution='low',
                                 columns=None, **kwargs):
        """
        Query stellar atmospheric parameters (``stellar`` / ``med_stellar``).

        Accepts the arguments of `query_spectra`. By default only ``obsid``,
        ``ra``, ``dec``, the effective temperature, surface gravity,
        metallicity and SNR columns are returned.
        """
        resolution = self._normalize_resolution(resolution)
        fields = _SPECTRAL_FIELDS[resolution]
        if columns is None:
            columns = ['obsid', 'ra', 'dec', fields['teff'], fields['logg'], fields['feh'], fields['snr']]
        kwargs.setdefault('catalog_name', _STELLAR[resolution])
        return self.query_spectra(coordinates, radius, resolution=resolution, columns=columns, **kwargs)

    def get_metadata(self, obsid, *, resolution='low', get_query_payload=False):
        """
        Catalogue row(s) of one observation.

        Parameters
        ----------
        obsid : str or int
            LAMOST observation ID.
        resolution : {"low", "medium"}, optional
            Catalogue to search.
        get_query_payload : bool, optional
            Return the ADQL query string instead of running it.

        Returns
        -------
        `~astropy.table.Table` or str
        """
        return self.query_catalog(
            _CATALOGUE[self._normalize_resolution(resolution)],
            constraints={'obsid': self._obsid(obsid)}, max_rows=None,
            get_query_payload=get_query_payload)

    def query_repeat_observations(self, *, obsid=None, coordinates=None, radius=None,
                                  resolution='low', get_query_payload=False):
        """
        Find all observations of the same target.

        LAMOST assigns each target a ``uid``; observations sharing it are
        repeats. Give either an ``obsid`` or ``coordinates`` and ``radius``
        (all targets within the cone are included).

        Returns
        -------
        `~astropy.table.Table` or str
            ``uid``, ``obsid``, ``ra``, ``dec`` and ``obsdate`` of every
            observation, ordered by ``uid`` and ``obsid``.
        """
        resolution = self._normalize_resolution(resolution)
        table = f'"public".{_CATALOGUE[resolution]}'
        if (obsid is None) == (coordinates is None):
            raise InvalidQueryError('Provide either obsid or coordinates and radius.')
        if obsid is not None:
            if radius is not None:
                raise InvalidQueryError('radius is only used with coordinates.')
            inner = f'obsid = {self._obsid(obsid)}'
        else:
            if radius is None:
                raise InvalidQueryError('coordinates and radius must be provided together.')
            inner = self._contains(coordinates, self._radius_deg(radius))[0]
        adql = (f'SELECT uid, obsid, ra, dec, obsdate FROM {table} '
                f'WHERE uid IN (SELECT uid FROM {table} WHERE {inner}) ORDER BY uid, obsid')
        return self._run(adql, get_query_payload=get_query_payload)

    @staticmethod
    def _obsid(obsid):
        try:
            return int(str(obsid).strip())
        except ValueError as error:
            raise InvalidQueryError(f'obsid must be an integer, got {obsid!r}.') from error

    # ----------------------------------------------------------------- SSAP
    def query_ssa(self, coordinates, radius, *, maxrec=None):
        """
        Simple Spectral Access (SSAP) cone search.

        Parameters
        ----------
        coordinates : str or `~astropy.coordinates.SkyCoord`
            Search center.
        radius : str, float or `~astropy.units.Quantity`
            Search diameter is twice this radius; bare numbers are degrees.
        maxrec : int, optional
            Maximum number of records.

        Returns
        -------
        `~astropy.table.Table`
            The catalogue columns plus the standard ``ssa_*`` columns and
            ``accref``, the URL of the spectrum FITS file.
        """
        c = commons.parse_coordinates(coordinates).icrs
        result = self.ssa.search(pos=c, diameter=2 * self._radius_deg(radius) * u.deg, maxrec=maxrec)
        table = result.to_table()
        self.table = table
        return table

    # ------------------------------------------------------------ downloads
    @property
    def _openapi_url(self):
        return f'{conf.server.rstrip("/")}/{self.data_release}/{self.sub_version}'

    def _auth(self, params=None):
        params = dict(params or {})
        if self.token:
            params['token'] = self.token
        return params

    def get_spectrum_list(self, obsid, *, resolution='low'):
        """
        URL of the spectrum FITS file of an observation (without downloading).

        Returns
        -------
        list of str
            A single-element list. For authenticated clients the URL contains
            the token and must not be shared.
        """
        resolution = self._normalize_resolution(resolution)
        res_path = 'mrs' if resolution == 'medium' else 'lrs'
        url = f'{self._openapi_url}/{res_path}/spectrum/fits'
        params = self._auth({'obsid': str(self._obsid(obsid))})
        return [f'{url}?{urlencode(params)}']

    def get_spectra(self, obsid, *, resolution='low', verify='warn', cache=True):
        """
        Download the spectrum FITS file of an observation.

        Parameters
        ----------
        obsid : str or int
            LAMOST observation ID.
        resolution : {"low", "medium"}, optional
            Low- (LRS) or medium-resolution (MRS) spectrum.
        verify : str, optional
            Passed to `astropy.io.fits.HDUList.verify`.
        cache : bool, optional
            Use the astroquery cache (ignored when a token is set).

        Returns
        -------
        list of `~astropy.io.fits.HDUList`
            A single-element list. The caller must close the HDU lists.
        """
        url = self.get_spectrum_list(obsid, resolution=resolution)[0]
        response = self._request('GET', url, timeout=conf.timeout, cache=cache and not self.token)
        response.raise_for_status()
        with commons.get_readable_fileobj(BytesIO(response.content), encoding='binary') as source:
            spectrum = fits.HDUList.fromstring(source.read())
        try:
            spectrum.verify(verify)
        except Exception:
            spectrum.close()
            raise
        return [spectrum]

    def download_catalog(self, catalog_name, *, resolution='low', save_dir='./',
                         filename=None, overwrite=True, verify='exception'):
        """
        Download a catalog product file (FITS).

        Parameters
        ----------
        catalog_name : str
            File product name from the release's download page, e.g.
            ``'dr10_v2.0_LRS_plan.fits.gz'``.
        resolution : {"low", "medium"}, optional
            Low- (LRS) or medium-resolution (MRS) products.
        save_dir : str, optional
            Directory to save into.
        filename : str, optional
            Output file name (relative to ``save_dir``). Default is
            ``catalog_name``.
        overwrite : bool, optional
            Replace an existing file.
        verify : str, optional
            Passed to `astropy.io.fits.HDUList.verify`; a failing file is
            not written.

        Returns
        -------
        str
            Path of the downloaded file.
        """
        resolution = self._normalize_resolution(resolution)
        res_path = 'mrs' if resolution == 'medium' else 'lrs'
        url = f'{self._openapi_url}/{res_path}/catalog'
        name = os.path.basename(catalog_name)
        path = filename if filename and os.path.isabs(filename) else os.path.join(save_dir, filename or name)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        if os.path.exists(path) and not overwrite:
            return path
        response = self._request('GET', url, params=self._auth({'name': catalog_name}),
                                 timeout=conf.timeout, cache=False, stream=True)
        with response:
            response.raise_for_status()
            with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(path))) as tmp:
                tmp_path = os.path.join(tmp, 'catalog')
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                with fits.open(tmp_path) as hdul:
                    hdul.verify(verify)
                os.replace(tmp_path, path)
        return path


# Singleton instance for module-level access
Lamost = LamostClass()


# Utility functions for FITS spectrum processing
def _spectrum_table_arrays(hdu, *, allow_loglam=False):
    """Read the named spectral arrays shared by LRS and MRS table HDUs."""
    if not isinstance(hdu, fits.BinTableHDU) or hdu.data is None or len(hdu.data) == 0:
        raise ValueError("Spectrum HDU must contain a nonempty binary table.")
    columns = {name.upper() for name in hdu.columns.names}
    loglam = allow_loglam and 'LOGLAM' in columns
    wavelength_column = 'LOGLAM' if loglam else 'WAVELENGTH'
    if 'FLUX' not in columns or wavelength_column not in columns:
        raise ValueError("Spectrum table requires FLUX and WAVELENGTH (or historical MRS LOGLAM) columns.")
    if loglam:
        if 'WAVELENGTH' in columns:
            raise ValueError("Spectrum table has ambiguous WAVELENGTH and LOGLAM columns.")
        # Historical MRS files store one scalar pixel per row, including coadds.
        flux = np.array(hdu.data['FLUX'], copy=True)
        wavelength = np.array(hdu.data['LOGLAM'], copy=True)
    else:
        if len(hdu.data) != 1:
            raise ValueError("FLUX and WAVELENGTH require one table row of vector arrays.")
        flux = np.array(hdu.data['FLUX'][0], copy=True)
        wavelength = np.array(hdu.data['WAVELENGTH'][0], copy=True)
    if (flux.ndim != 1 or flux.size == 0 or flux.shape != wavelength.shape
            or flux.dtype.kind not in 'iuf' or wavelength.dtype.kind not in 'iuf'):
        raise ValueError(f"FLUX and {wavelength_column} must be nonempty numeric arrays of equal length.")
    if loglam:
        invalid = np.flatnonzero(~np.isfinite(wavelength))
        if invalid.size:
            first = invalid[0]
            raise ValueError(
                f"LOGLAM must be finite; found {invalid.size} invalid pixels, "
                f"first at zero-based index {first}: {wavelength[first]!r}."
            )
        # Promote before exponentiating: float32 log wavelengths otherwise lose
        # precision unnecessarily. Do not apply RV corrections or reorder pixels.
        # The MRS parser checks the converted values, including overflow and
        # underflow to zero, and reports the extension and offending pixel.
        with np.errstate(over='ignore', under='ignore', invalid='ignore'):
            wavelength = 10.0 ** wavelength.astype(np.float64)
    return wavelength, flux


def parse_lrs_spectrum(filename):
    """
    Parse a low-resolution spectrum (LRS) FITS file.

    Read the wavelength and flux arrays without smoothing, changing flux
    precision, selecting pixels, or applying a velocity correction.

    Parameters
    ----------
    filename : str
        Path to the LRS FITS file.

    Returns
    -------
    wavelength : `~numpy.ndarray`
        Wavelength array in Angstroms.
    flux : `~numpy.ndarray`
        Spectrum flux array.

    Raises
    ------
    ValueError
        The file is neither a primary-HDU LRS image with COEFF0/COEFF1 nor
        a two-HDU file with FLUX and WAVELENGTH table columns.

    Notes
    -----
    This parser validates the file layout, not the scientific quality of its
    pixels. It does not reject nonfinite or nonpositive wavelength/flux values.

    Examples
    --------
    >>> wavelength, flux = parse_lrs_spectrum('spec.fits')  # doctest: +SKIP
    """
    with fits.open(filename) as hdulist:
        if len(hdulist) == 1:
            header, scidata = hdulist[0].header, hdulist[0].data
            if (scidata is None or scidata.ndim != 2 or not all(scidata.shape)
                    or 'COEFF0' not in header or 'COEFF1' not in header):
                raise ValueError("LRS primary HDU requires a flux image and COEFF0/COEFF1 header keywords.")
            flux = np.array(scidata[0], copy=True)
            wavelength = 10 ** (float(header['COEFF0']) + np.arange(flux.size) * float(header['COEFF1']))
        elif len(hdulist) == 2:
            wavelength, flux = _spectrum_table_arrays(hdulist[1])
        else:
            raise ValueError(
                f"Unsupported LRS FITS layout: found {len(hdulist)} HDUs; "
                "expected a single primary image or a primary HDU and a spectrum table."
            )

    return wavelength, flux


def parse_mrs_spectrum(filename):
    """
    Parse a medium-resolution spectrum (MRS) FITS file.

    This function reads a LAMOST medium-resolution spectrum FITS file which
    contains multiple spectral bands in separate extensions. It supports
    single-row FLUX/WAVELENGTH vectors and historical DR8/DR9 tables with
    scalar FLUX/LOGLAM pixels in successive rows. LOGLAM is converted to
    wavelength as ``10**LOGLAM`` in double precision. Pixel order, flux values,
    and extension names (including coadds and individual exposures) are kept;
    no radial-velocity or wavelength-frame correction is applied.
    Logarithmic wavelengths must be finite and the resulting wavelengths must
    be finite and positive. Flux quality selection is left to the caller.

    Parameters
    ----------
    filename : str
        Path to the MRS FITS file.

    Returns
    -------
    dict
        Dictionary with extension names as keys. Each value contains
        ``wavelength`` (array in Angstroms) and ``flux`` (spectrum flux array).

    Raises
    ------
    ValueError
        No spectrum extensions are present, or an extension is empty, lacks
        supported columns, has ambiguous wavelength columns, or does not have
        the numeric array shapes described above. Duplicate extension names
        are rejected to avoid silently losing a spectrum. Nonfinite LOGLAM or
        nonfinite/nonpositive wavelengths, including conversion overflow or
        underflow to zero, are rejected with extension and pixel diagnostics.

    Examples
    --------
    >>> data = parse_mrs_spectrum('spec_mrs.fits')  # doctest: +SKIP
    >>> for band_name, band_data in data.items():  # doctest: +SKIP
    ...     print(f"{band_name}: {len(band_data['wavelength'])} pixels")  # doctest: +SKIP
    """
    data = {}
    with fits.open(filename) as hdulist:
        if len(hdulist) < 2:
            raise ValueError(f"{filename}: MRS FITS requires at least one spectrum extension.")
        for i, hdu in enumerate(hdulist[1:], 1):
            extension_name = hdu.header.get('EXTNAME') or f'Extension_{i}'
            try:
                wavelength, flux = _spectrum_table_arrays(hdu, allow_loglam=True)
                invalid = np.flatnonzero(~np.isfinite(wavelength) | (wavelength <= 0))
                if invalid.size:
                    first = invalid[0]
                    raise ValueError(
                        f"Wavelengths must be finite and positive; found {invalid.size} invalid pixels, "
                        f"first at zero-based index {first}: {wavelength[first]!r}."
                    )
            except ValueError as error:
                raise ValueError(f"{filename}: extension {extension_name!r} (HDU {i}): {error}") from error
            if extension_name in data:
                raise ValueError(f"{filename}: duplicate spectrum extension name: {extension_name} (HDU {i}).")
            data[extension_name] = {'wavelength': wavelength, 'flux': flux}
    return data
