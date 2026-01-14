.. _astroquery.ztf_bts:

*********************************************
ZTF BTS Queries (`astroquery.ztf_bts`)
*********************************************

Getting started
===============

This module provides an interface to the Zwicky Transient Facility (ZTF)
Bright Transient Survey (BTS) Sample Explorer. The ZTF BTS is a systematic
search for bright (magnitude < 19) transients discovered by ZTF, with
extensive multi-wavelength follow-up observations.

The module allows querying the catalog by:

* Object names (ZTF or TNS identifiers)
* Sky coordinates with configurable search radius
* Classification type (e.g., SN Ia, SN II, SLSN)
* Redshift ranges
* Temporal properties (discovery date, peak time)
* Photometric properties (peak magnitude, absolute magnitude)
* Light curve characteristics (rise time, fade time, duration)


Query by Object Name
=====================

You can query the ZTF BTS catalog using either ZTF names or TNS (Transient Name
Server) designations:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> # Query by ZTF name
    >>> result = ZTFBTS.query_object('ZTF18aaqedfj')  # doctest: +SKIP
    >>> # Query by TNS name
    >>> result = ZTFBTS.query_object('SN2018bff')  # doctest: +SKIP


Query by Sky Position
=====================

Query for transients near a specific sky position:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> from astropy.coordinates import SkyCoord
    >>> import astropy.units as u
    >>> 
    >>> # Define the search position
    >>> coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
    >>> 
    >>> # Query with 5 arcminute radius
    >>> result = ZTFBTS.query_region(coord, radius=5*u.arcmin)  # doctest: +SKIP

You can also use string coordinates:

.. doctest-remote-data::

    >>> result = ZTFBTS.query_region('13h30m00s +47d12m00s', radius=1*u.arcmin)  # doctest: +SKIP


Query by Classification Type
=============================

Search for objects of a specific classification:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> 
    >>> # Get all Type Ia supernovae
    >>> result = ZTFBTS.query_by_type('SN Ia')  # doctest: +SKIP
    >>> 
    >>> # Get all superluminous supernovae
    >>> result = ZTFBTS.query_by_type('SLSN-I')  # doctest: +SKIP

Common classification types include:

* Type Ia SNe: ``SN Ia``, ``SN Ia-91T``, ``SN Ia-91bg``, ``SN Ia-CSM``
* Core-Collapse SNe: ``SN II``, ``SN IIP``, ``SN IIn``, ``SN IIb``, ``SN Ib``, ``SN Ic``, ``SN Ic-BL``
* Superluminous SNe: ``SLSN-I``, ``SLSN-II``
* Other: ``nova``, ``TDE``, ``CV``


Query by Redshift
=================

Find objects within a specific redshift range:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> 
    >>> # Objects with 0.05 < z < 0.1
    >>> result = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1)  # doctest: +SKIP
    >>> 
    >>> # Objects with z > 0.1
    >>> result = ZTFBTS.query_by_redshift(z_min=0.1)  # doctest: +SKIP


Query by Time
=============

Search for objects discovered or peaking within a time range:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> from astropy.time import Time
    >>> 
    >>> # Objects discovered in 2018
    >>> start = Time('2018-01-01')
    >>> end = Time('2018-12-31')
    >>> result = ZTFBTS.query_by_time(start_time=start, end_time=end)  # doctest: +SKIP

You can also use ISO format strings:

.. doctest-remote-data::

    >>> result = ZTFBTS.query_by_time(
    ...     start_time='2018-01-01',
    ...     end_time='2018-12-31'
    ... )  # doctest: +SKIP


Combined Criteria Query
========================

Combine multiple search criteria for more specific queries:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> 
    >>> # Complex query for bright, nearby Type Ia SNe with fast rise times
    >>> result = ZTFBTS.query_criteria(
    ...     classification='SN Ia',
    ...     z_min=0.05,
    ...     z_max=0.1,
    ...     peak_mag_max=18.0,
    ...     rise_min=5.0,
    ...     rise_max=20.0,
    ...     abs_mag_min=-20.0
    ... )  # doctest: +SKIP

Available criteria parameters:

* ``name``: Object name (ZTF or TNS)
* ``ra``, ``dec``, ``radius``: Sky position and search radius (degrees)
* ``classification``: Object type
* ``z_min``, ``z_max``: Redshift range
* ``peak_mag_min``, ``peak_mag_max``: Peak apparent magnitude range
* ``abs_mag_min``, ``abs_mag_max``: Absolute magnitude range
* ``duration_min``, ``duration_max``: Duration range (days)
* ``rise_min``, ``rise_max``: Rise time range (days)
* ``fade_min``, ``fade_max``: Fade time range (days)
* ``galactic_lat_min``, ``galactic_lat_max``: Galactic latitude range


Light Curve Data
================

Retrieve light curve data for a specific object:

.. doctest-remote-data::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> 
    >>> # Get light curve for a specific object
    >>> lc = ZTFBTS.get_light_curve('ZTF18aaqedfj')  # doctest: +SKIP

The returned table contains photometric measurements with columns for MJD,
magnitude, magnitude error, and filter.


Inspecting Query Payloads
==========================

You can inspect the query parameters without executing the query:

.. doctest-skip::

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> 
    >>> # Get the query payload without executing
    >>> payload = ZTFBTS.query_criteria(
    ...     classification='SN Ia',
    ...     z_min=0.05,
    ...     z_max=0.1,
    ...     get_query_payload=True
    ... )
    >>> print(payload)
    {'type': 'SN Ia', 'redshift_min': 0.05, 'redshift_max': 0.1, 'format': 'json'}


Reference/API
=============

.. automodapi:: astroquery.ztf_bts
    :no-inheritance-diagram:


Acknowledgements
================

If you use data from the ZTF BTS in your research, please cite:

    Perley, D. A., et al. 2020, ApJ, 904, 35
    "The Zwicky Transient Facility Bright Transient Survey. II. A Public 
    Statistical Sample for Exploring Supernova Demographics"
    https://arxiv.org/abs/2009.01242

ZTF BTS Resources:

* Explorer: https://sites.astro.caltech.edu/ztf/bts/explorer.php
* Documentation: https://sites.astro.caltech.edu/ztf/bts/explorer_info.html
* Examples: https://sites.astro.caltech.edu/ztf/bts/examples.html
