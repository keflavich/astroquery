.. _astroquery.nadc.lamost:

*****************************************
LAMOST Queries (`astroquery.nadc.lamost`)
*****************************************

``astroquery.nadc.lamost`` provides access to the LAMOST archive. Catalog
queries use the IVOA Table Access Protocol (TAP) and Simple Spectral Access
Protocol (SSAP) services that LAMOST publishes for each data release, through
`pyvo <https://pyvo.readthedocs.io>`_. LRS/MRS spectra and catalog files are
downloaded from the LAMOST OpenAPI, and local spectrum files can be read
with the provided parsers.

Examples use the public DR10/v2.0 service unless another release is specified.
Executing queries and downloading data requires internet access.

The VO services exist for DR10 and later (for example ``dr10/v2.0``,
``dr11/v1.0`` and ``dr12/v1.0``). ``get_spectra`` and ``download_catalog``
also work for older releases.

Configuration
=============

Set configuration options before creating a
`~astroquery.nadc.lamost.LamostClass` instance, or pass the release explicitly:

.. doctest::

  >>> from astroquery.nadc.lamost import LamostClass
  >>> lamost = LamostClass(data_release='dr10', sub_version='v2.0')
  >>> lamost.tap_url
  'https://www.lamost.org/dr10/v2.0/voservice/tap'

TAP and SSAP queries are anonymous. For releases whose file downloads need a
token, pass ``token=...`` or set ``conf.token``; it is appended to download
requests only.

Basic Usage
===========

Use ``query_region`` to find observations around a position. Radii accept
angular quantities such as ``5*u.arcsec``, angle strings such as
``'5 arcsec'``, and bare numbers in degrees:

.. doctest::

  >>> import astropy.units as u
  >>> from astropy.coordinates import SkyCoord
  >>> coord = SkyCoord(160.5, 29.1, unit='deg', frame='icrs')
  >>> lamost.query_region(coord, 3*u.arcmin, get_query_payload=True)  # doctest: +IGNORE_OUTPUT
  'SELECT TOP 1000 t.*, DISTANCE(...) AS separation FROM "public".catalogue AS t WHERE ...'

.. doctest-remote-data::

  >>> matches = lamost.query_region(coord, radius=3*u.arcmin)
  >>> print(matches['obsid', 'ra', 'dec', 'separation'][:5])  # doctest: +IGNORE_OUTPUT

Results are `~astropy.table.Table` objects sorted by distance, with the
distance in degrees in the ``separation`` column. At most ``max_rows`` (default
1000; `None` for no limit) rows are returned. Use ``resolution='medium'``
for the medium-resolution (MRS) catalogue. Pass ``get_query_payload=True`` to
any ``query_*`` method to get the ADQL query instead of running it.

Other query methods:

``query_catalog``
    Any table of the ``public`` schema, with optional cone, equality and
    range ``constraints``, a raw ``where`` condition, ``columns`` and
    ``order_by``.
``query_spectra``
    Quality filters: ``snr_min`` and ``teff_range``, ``logg_range`` and
    ``feh_range`` (the latter three use the stellar-parameter table).
``query_stellar_parameters``
    ``query_spectra`` with a default set of stellar-parameter columns.
``get_metadata``
    The catalogue row(s) of one ``obsid``.
``query_repeat_observations``
    All observations of a target (those sharing a ``uid``), found from an
    ``obsid`` or from a cone.
``query_ssa``
    SSAP cone search. The result has the catalogue columns and ``accref``,
    the URL of each spectrum FITS file.

.. doctest-remote-data::

  >>> stars = lamost.query_stellar_parameters(
  ...     teff_range=(5000, 5100), logg_range=(4, 5), snr_min=50, max_rows=5)
  >>> print(stars)  # doctest: +IGNORE_OUTPUT
  >>> repeats = lamost.query_repeat_observations(obsid=16011237)
  >>> print(repeats)  # doctest: +IGNORE_OUTPUT

ADQL queries
============

``query_tap`` sends any ADQL query and returns a `pyvo.dal.TAPResults`
(use ``.to_table()``). Tables of the main schema are quoted as ``"public".catalogue``.
Use ``async_job=True`` for long queries.
``get_tables`` lists the available tables and their columns:

.. doctest-remote-data::

  >>> adql = """SELECT TOP 5 obsid, ra, dec, snrg FROM "public".catalogue
  ...           WHERE snrg > 100 AND class = 'STAR'"""
  >>> print(lamost.query_tap(adql).to_table())  # doctest: +IGNORE_OUTPUT
  >>> tables = lamost.get_tables()
  >>> [column.name for column in tables['"public".stellar'].columns][:5]  # doctest: +IGNORE_OUTPUT

The underlying `pyvo.dal.TAPService` and `pyvo.dal.SSAService` are available
as ``lamost.tap`` and ``lamost.ssa``.

Data Products
=============

Use ``resolution='low'`` for LRS or ``resolution='medium'`` for MRS.
``get_spectra`` accepts one
observation ID and returns a list of `~astropy.io.fits.HDUList` objects.
The FITS retains its headers, inverse variance, masks, and spectral extensions.
To obtain its download URL without fetching the file, use ``get_spectrum_list``.
Authenticated URLs contain the token and must not be shared or logged.

``get_spectra`` uses Astropy's ``verify='warn'`` by default. This example
uses ``silentfix`` to repair structural FITS header issues in the selected
product. Close the returned HDU lists after use:

.. doctest-remote-data::

  >>> spectra = lamost.get_spectra(176604010, resolution='low', verify='silentfix')
  >>> try:
  ...     obsid = spectra[0][0].header['OBSID']
  ...     spectra[0].writeto('lrs-spectrum.fits', overwrite=True, output_verify='silentfix')
  ... finally:
  ...     for spectrum in spectra:
  ...         spectrum.close()
  >>> obsid
  176604010

Astropy may fix structural header issues when writing; this is not a
byte-for-byte copy of the HTTP response.

One MRS FITS can contain multiple exposures;
do not treat its ``obsid`` as a unique identifier for every exposure row.

``download_catalog`` saves a named catalog product and returns its local
path. For example:

.. code-block:: python

   path = lamost.download_catalog('dr10_v2.0_LRS_plan.fits.gz')

Find product names on the selected release's download page;
``get_tables`` lists queryable tables instead. FITS catalog downloads use
``verify='exception'`` by default. Existing files are reused unless
``overwrite=True``; failed downloads leave an existing file intact.

FITS verification checks file structure. Inspect warnings before changing
``verify`` and assess pixel quality separately. Catalog downloads bypass the
response cache and do not resume partial files.

Reading Local Spectra
=====================

``parse_lrs_spectrum`` reads the supported single-HDU image or two-HDU table
layout and returns two arrays: wavelength and flux. It preserves flux values
and precision without smoothing. Unsupported layouts raise ``ValueError``.
LRS parsing does not reject nonfinite or nonpositive wavelength/flux values;
apply scientific quality checks before analysis.

``parse_mrs_spectrum`` returns a dictionary keyed by extension name, each
containing ``wavelength`` and ``flux``. Both readers return wavelengths in
angstroms and retain the archive flux units and normalization. Consult the
FITS headers before interpreting them as calibrated flux. The simplified
arrays do not include inverse variance or quality masks; read those from the
original FITS when selecting pixels or propagating errors.

For existing local LRS and MRS FITS files:

.. code-block:: python

   from astroquery.nadc.lamost import parse_lrs_spectrum, parse_mrs_spectrum

   wavelength, flux = parse_lrs_spectrum('lrs-spectrum.fits')
   exposures = parse_mrs_spectrum('mrs-spectrum.fits')

MRS readers support modern wavelength columns and legacy logarithmic
wavelengths. Coadds and individual exposures retain their extension names.
Wavelengths must be finite and positive; unsupported or ambiguous layouts
raise ``ValueError``. Neither reader applies a velocity correction or
scientific pixel selection.

Tutorials and Analysis Examples
===============================

The `astroquery NADC LAMOST examples repository
<https://github.com/china-vo/astroquery-nadc-lamost-examples>`_ contains complete
workflows for catalog pagination and export, LRS export and smoothing,
MRS batch reading and plotting, and a Ca II H&K activity-index calculation.
The repository includes installation instructions, a standalone activity
script, and offline test data.

Failures and Diagnostics
========================

``InvalidQueryError``
    Check parameter values and column names using ``get_tables``.
`pyvo.dal.DALQueryError`, `pyvo.dal.DALServiceError`
    The TAP or SSAP service rejected the query or could not be reached, for
    example for a release without VO services. The message includes the
    service's explanation, such as an unknown column.
`requests.HTTPError`
    A spectrum or catalog-file download failed. Check service availability and
    the selected release.

Reference/API
=============

.. automodapi:: astroquery.nadc.lamost
    :no-inheritance-diagram:
