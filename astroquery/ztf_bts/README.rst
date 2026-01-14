ZTF Bright Transient Survey (BTS) Module
=========================================

This module provides an interface to query the Zwicky Transient Facility (ZTF) 
Bright Transient Survey Sample Explorer.

About ZTF BTS
-------------

The ZTF Bright Transient Survey is a systematic search for bright (magnitude < 19) 
transients in the ZTF public survey. The sample includes well-characterized 
supernovae and other transients with extensive multi-wavelength follow-up.

Key Features
------------

- Query by object name (ZTF or TNS names)
- Query by sky coordinates with configurable search radius
- Query by classification type (SN Ia, SN II, SLSN, etc.)
- Query by redshift range
- Query by temporal properties (discovery date, peak time)
- Query by photometric properties (peak magnitude, absolute magnitude)
- Query by light curve characteristics (rise time, fade time, duration)
- Retrieve light curve data

Query Examples
--------------

Query by Object Name
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    
    # Query by ZTF name
    result = ZTFBTS.query_object('ZTF18aaqedfj')
    
    # Query by TNS name
    result = ZTFBTS.query_object('SN2018bff')

Query by Sky Position
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    
    # Define coordinates
    coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
    
    # Query with 5 arcminute radius
    result = ZTFBTS.query_region(coord, radius=5*u.arcmin)

Query by Classification
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    
    # Get all Type Ia supernovae
    result = ZTFBTS.query_by_type('SN Ia')
    
    # Get all superluminous supernovae
    result = ZTFBTS.query_by_type('SLSN-I')

Query by Redshift
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    
    # Get objects with redshift between 0.05 and 0.1
    result = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1)

Query by Time Range
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    from astropy.time import Time
    
    # Get objects discovered in 2018
    start = Time('2018-01-01')
    end = Time('2018-12-31')
    result = ZTFBTS.query_by_time(start_time=start, end_time=end)

Combined Criteria Query
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    
    # Complex query combining multiple criteria
    result = ZTFBTS.query_criteria(
        classification='SN Ia',
        z_min=0.05,
        z_max=0.1,
        peak_mag_max=18.0,
        rise_min=5.0,
        rise_max=20.0
    )

Get Light Curve Data
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from astroquery.ztf_bts import ZTFBTS
    
    # Retrieve light curve for a specific object
    lc = ZTFBTS.get_light_curve('ZTF18aaqedfj')

Available Classification Types
------------------------------

Common classification types in the ZTF BTS catalog include:

- Type Ia Supernovae: 'SN Ia', 'SN Ia-91T', 'SN Ia-91bg', 'SN Ia-CSM', 'SN Ia-pec'
- Core-Collapse Supernovae: 'SN II', 'SN IIP', 'SN IIn', 'SN IIb', 'SN Ib', 'SN Ic', 'SN Ic-BL', 'SN Ibn', 'SN Icn'
- Superluminous Supernovae: 'SLSN-I', 'SLSN-II'
- Other Transients: 'nova', 'TDE', 'CV'

References
----------

If you use data from the ZTF BTS in your research, please cite:

Perley, D. A., et al. 2020, ApJ, 904, 35
"The Zwicky Transient Facility Bright Transient Survey. II. A Public Statistical 
Sample for Exploring Supernova Demographics"
https://arxiv.org/abs/2009.01242

ZTF BTS Explorer: https://sites.astro.caltech.edu/ztf/bts/explorer.php
ZTF BTS Documentation: https://sites.astro.caltech.edu/ztf/bts/explorer_info.html
