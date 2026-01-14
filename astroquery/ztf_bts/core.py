# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Core module for querying the ZTF Bright Transient Survey.
"""

import warnings
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time
import numpy as np

from ..query import BaseQuery
from ..utils import async_to_sync
from . import conf


__all__ = ['ZTFBTS', 'ZTFBTSClass']


@async_to_sync
class ZTFBTSClass(BaseQuery):
    """
    Class for querying the ZTF Bright Transient Survey (BTS) Sample Explorer.

    The ZTF BTS is a systematic catalog of bright transients discovered by ZTF.
    This class provides methods to query the catalog by various criteria including
    object names, coordinates, classification, redshift, and temporal properties.

    Examples
    --------
    Query by ZTF name:

    >>> from astroquery.ztf_bts import ZTFBTS
    >>> result = ZTFBTS.query_object('ZTF18aaqedfj')  # doctest: +SKIP

    Query by position:

    >>> from astropy.coordinates import SkyCoord
    >>> import astropy.units as u
    >>> coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
    >>> result = ZTFBTS.query_region(coord, radius=5*u.arcmin)  # doctest: +SKIP

    Query by classification:

    >>> result = ZTFBTS.query_by_type('SN Ia')  # doctest: +SKIP

    Query by redshift range:

    >>> result = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1)  # doctest: +SKIP
    """

    URL = conf.server
    API_URL = conf.api_url
    TIMEOUT = conf.timeout

    def query_object_async(self, object_name, *, get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog by object name.

        This method accepts ZTF names (e.g., 'ZTF18aaqedfj') or TNS names
        (e.g., 'SN2018bff').

        Parameters
        ----------
        object_name : str
            The name of the object to query. Can be a ZTF name (ZTFYYaaaaaaa)
            or TNS name (e.g., SN2018bff, AT2019xxx).
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> result = ZTFBTS.query_object('ZTF18aaqedfj')  # doctest: +SKIP
        >>> result = ZTFBTS.query_object('SN2018bff')  # doctest: +SKIP

        Notes
        -----
        The ZTF BTS Explorer website returns all objects when querying by name,
        so this method filters the results to return only exact matches after
        retrieval.
        """
        request_payload = self._args_to_payload(name=object_name)

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)

        # Store the requested object name for post-filtering
        response.requested_name = object_name

        return response

    def query_region_async(self, coordinates, radius=1*u.arcmin, *,
                          get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog by sky position.

        Parameters
        ----------
        coordinates : str or `astropy.coordinates.SkyCoord`
            The coordinates to query. Can be a SkyCoord object or a
            string that can be parsed by SkyCoord.
        radius : `~astropy.units.Quantity`, optional
            The search radius. Default is 1 arcminute.
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astropy.coordinates import SkyCoord
        >>> import astropy.units as u
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
        >>> result = ZTFBTS.query_region(coord, radius=5*u.arcmin)  # doctest: +SKIP
        """
        # Parse coordinates
        if not isinstance(coordinates, SkyCoord):
            coordinates = SkyCoord(coordinates)

        # Convert radius to degrees
        radius_deg = radius.to(u.deg).value

        request_payload = self._args_to_payload(
            ra=coordinates.ra.deg,
            dec=coordinates.dec.deg,
            radius=radius_deg
        )

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def query_by_type_async(self, obj_type, *, get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog by classification type.

        Parameters
        ----------
        obj_type : str
            The classification type to query for. Common types include:
            'SN Ia', 'SN II', 'SN Ib', 'SN Ic', 'SN IIP', 'SN IIn', 'SN Ia-91T',
            'SN Ia-91bg', 'SN Ia-CSM', 'SN Ibn', 'SN Ic-BL', 'SN IIb',
            'SLSN-I', 'SLSN-II', 'nova', etc.
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> result = ZTFBTS.query_by_type('SN Ia')  # doctest: +SKIP
        >>> result = ZTFBTS.query_by_type('SLSN-I')  # doctest: +SKIP
        """
        request_payload = self._args_to_payload(classification=obj_type)

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def query_by_redshift_async(self, z_min=None, z_max=None, *,
                               get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog by redshift range.

        Parameters
        ----------
        z_min : float, optional
            Minimum redshift. If None, no lower bound is applied.
        z_max : float, optional
            Maximum redshift. If None, no upper bound is applied.
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> result = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1)  # doctest: +SKIP
        """
        request_payload = self._args_to_payload(z_min=z_min, z_max=z_max)

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def query_by_time_async(self, start_time=None, end_time=None, *,
                           get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog by discovery/peak time.

        Parameters
        ----------
        start_time : `~astropy.time.Time` or str, optional
            Start time for the search. Can be an astropy Time object or
            ISO format string.
        end_time : `~astropy.time.Time` or str, optional
            End time for the search. Can be an astropy Time object or
            ISO format string.
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> from astropy.time import Time
        >>> start = Time('2018-01-01')
        >>> end = Time('2018-12-31')
        >>> result = ZTFBTS.query_by_time(start_time=start, end_time=end)  # doctest: +SKIP
        """
        # Convert times to MJD if provided
        if start_time is not None:
            if not isinstance(start_time, Time):
                start_time = Time(start_time)
            start_mjd = start_time.mjd
        else:
            start_mjd = None

        if end_time is not None:
            if not isinstance(end_time, Time):
                end_time = Time(end_time)
            end_mjd = end_time.mjd
        else:
            end_mjd = None

        request_payload = self._args_to_payload(
            start_mjd=start_mjd,
            end_mjd=end_mjd
        )

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def query_criteria_async(self, *, name=None, ra=None, dec=None, radius=None,
                            classification=None, z_min=None, z_max=None,
                            peak_mag_min=None, peak_mag_max=None,
                            abs_mag_min=None, abs_mag_max=None,
                            duration_min=None, duration_max=None,
                            rise_min=None, rise_max=None,
                            fade_min=None, fade_max=None,
                            galactic_lat_min=None, galactic_lat_max=None,
                            get_query_payload=False, cache=True):
        """
        Query the ZTF BTS catalog with custom criteria.

        This is a general-purpose query method that allows combining multiple
        search criteria.

        Parameters
        ----------
        name : str, optional
            Object name (ZTF or TNS).
        ra : float, optional
            Right ascension in degrees (use with dec and radius).
        dec : float, optional
            Declination in degrees (use with ra and radius).
        radius : float, optional
            Search radius in degrees.
        classification : str, optional
            Object classification type.
        z_min : float, optional
            Minimum redshift.
        z_max : float, optional
            Maximum redshift.
        peak_mag_min : float, optional
            Minimum peak magnitude.
        peak_mag_max : float, optional
            Maximum peak magnitude.
        abs_mag_min : float, optional
            Minimum absolute magnitude.
        abs_mag_max : float, optional
            Maximum absolute magnitude.
        duration_min : float, optional
            Minimum duration in days.
        duration_max : float, optional
            Maximum duration in days.
        rise_min : float, optional
            Minimum rise time in days.
        rise_max : float, optional
            Maximum rise time in days.
        fade_min : float, optional
            Minimum fade time in days.
        fade_max : float, optional
            Maximum fade time in days.
        galactic_lat_min : float, optional
            Minimum Galactic latitude in degrees.
        galactic_lat_max : float, optional
            Maximum Galactic latitude in degrees.
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> # Query for Type Ia SNe with redshift 0.05-0.1 and peak mag < 18
        >>> result = ZTFBTS.query_criteria(
        ...     classification='SN Ia',
        ...     z_min=0.05, z_max=0.1,
        ...     peak_mag_max=18.0
        ... )  # doctest: +SKIP
        """
        request_payload = self._args_to_payload(
            name=name, ra=ra, dec=dec, radius=radius,
            classification=classification,
            z_min=z_min, z_max=z_max,
            peak_mag_min=peak_mag_min, peak_mag_max=peak_mag_max,
            abs_mag_min=abs_mag_min, abs_mag_max=abs_mag_max,
            duration_min=duration_min, duration_max=duration_max,
            rise_min=rise_min, rise_max=rise_max,
            fade_min=fade_min, fade_max=fade_max,
            galactic_lat_min=galactic_lat_min, galactic_lat_max=galactic_lat_max
        )

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def get_light_curve_async(self, ztf_name, *, get_query_payload=False, cache=True):
        """
        Retrieve the light curve data for a specific object.

        Parameters
        ----------
        ztf_name : str
            The ZTF name of the object (e.g., 'ZTF18aaqedfj').
        get_query_payload : bool, optional
            If True, return the query parameters without executing the query.
            Default is False.
        cache : bool, optional
            If True, cache the query result. Default is True.

        Returns
        -------
        response : `requests.Response`
            The HTTP response from the server containing light curve data.

        Examples
        --------
        >>> from astroquery.ztf_bts import ZTFBTS
        >>> lc = ZTFBTS.get_light_curve('ZTF18aaqedfj')  # doctest: +SKIP
        """
        request_payload = {'name': ztf_name, 'format': 'lightcurve'}

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
        return response

    def _args_to_payload(self, **kwargs):
        """
        Convert query arguments to API request payload.

        Parameters
        ----------
        **kwargs : dict
            Query parameters

        Returns
        -------
        request_payload : dict
            Dictionary of parameters formatted for the API request
        """
        request_payload = {}

        # Always request CSV format for consistent parsing
        request_payload['format'] = 'csv'

        # Object name search
        if 'name' in kwargs and kwargs['name'] is not None:
            request_payload['name'] = kwargs['name']

        # Coordinate searches - the API accepts RA/Dec ranges
        if 'ra' in kwargs and kwargs['ra'] is not None:
            # For cone search, convert central position + radius to RA/Dec box
            ra = kwargs['ra']
            dec = kwargs['dec']
            radius = kwargs.get('radius', 0)

            # Convert radius from degrees to RA/Dec box
            # At dec, 1 degree RA = 1 degree * cos(dec)
            dec_rad = np.radians(dec)
            ra_width = radius / np.cos(dec_rad) if abs(dec_rad) < np.pi/2 - 0.01 else radius

            request_payload['startra'] = ra - ra_width
            request_payload['endra'] = ra + ra_width
            request_payload['startdec'] = dec - radius
            request_payload['enddec'] = dec + radius

        # Classification filter
        if 'classification' in kwargs and kwargs['classification'] is not None:
            # The website uses custom filter for type matching
            request_payload['typef'] = kwargs['classification']

        # Redshift range
        if 'z_min' in kwargs and kwargs['z_min'] is not None:
            request_payload['startz'] = kwargs['z_min']
        if 'z_max' in kwargs and kwargs['z_max'] is not None:
            request_payload['endz'] = kwargs['z_max']

        # Peak magnitude range
        if 'peak_mag_min' in kwargs and kwargs['peak_mag_min'] is not None:
            request_payload['startpeakmag'] = kwargs['peak_mag_min']
        if 'peak_mag_max' in kwargs and kwargs['peak_mag_max'] is not None:
            request_payload['endpeakmag'] = kwargs['peak_mag_max']

        # Absolute magnitude range
        if 'abs_mag_min' in kwargs and kwargs['abs_mag_min'] is not None:
            request_payload['startabsmag'] = kwargs['abs_mag_min']
        if 'abs_mag_max' in kwargs and kwargs['abs_mag_max'] is not None:
            request_payload['endabsmag'] = kwargs['abs_mag_max']

        # Duration range
        if 'duration_min' in kwargs and kwargs['duration_min'] is not None:
            request_payload['startdur'] = kwargs['duration_min']
        if 'duration_max' in kwargs and kwargs['duration_max'] is not None:
            request_payload['enddur'] = kwargs['duration_max']

        # Rise time range
        if 'rise_min' in kwargs and kwargs['rise_min'] is not None:
            request_payload['startrise'] = kwargs['rise_min']
        if 'rise_max' in kwargs and kwargs['rise_max'] is not None:
            request_payload['endrise'] = kwargs['rise_max']

        # Fade time range
        if 'fade_min' in kwargs and kwargs['fade_min'] is not None:
            request_payload['startfade'] = kwargs['fade_min']
        if 'fade_max' in kwargs and kwargs['fade_max'] is not None:
            request_payload['endfade'] = kwargs['fade_max']

        # Galactic latitude range
        if 'galactic_lat_min' in kwargs and kwargs['galactic_lat_min'] is not None:
            request_payload['startb'] = kwargs['galactic_lat_min']
        if 'galactic_lat_max' in kwargs and kwargs['galactic_lat_max'] is not None:
            request_payload['endb'] = kwargs['galactic_lat_max']

        # Time range (MJD or JD-2458000)
        if 'start_mjd' in kwargs and kwargs['start_mjd'] is not None:
            # Convert MJD to JD-2458000
            request_payload['startpeak'] = kwargs['start_mjd'] - 58000
        if 'end_mjd' in kwargs and kwargs['end_mjd'] is not None:
            request_payload['endpeak'] = kwargs['end_mjd'] - 58000

        # If no filters specified, get all candidate transients (not variables)
        if len(request_payload) == 1:  # Only 'format' is set
            request_payload['subsample'] = 'cantrans'

        return request_payload

    def _parse_result(self, response, *, verbose=False):
        """
        Parse the response from the ZTF BTS API.

        Parameters
        ----------
        response : `requests.Response`
            The HTTP response from the API.
        verbose : bool, optional
            If True, print additional information. Default is False.

        Returns
        -------
        table : `~astropy.table.Table`
            An astropy Table containing the query results.
        """
        import csv
        from io import StringIO

        # Check for errors
        response.raise_for_status()

        # Get the response text
        content = response.text.strip()

        if not content:
            warnings.warn("Query returned no results.", UserWarning)
            return Table()

        # Parse CSV response
        # Use StringIO to treat the text as a file
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        if not rows:
            warnings.warn("Query returned no results.", UserWarning)
            return Table()

        # Convert to astropy Table
        table = Table(rows=rows)

        # Filter results if this was a name query
        # The ZTF BTS Explorer returns all objects when name is specified, so filter here
        if hasattr(response, 'requested_name'):
            name = response.requested_name
            # Try to match either ZTFID or IAUID (TNS name)
            mask = (table['ZTFID'] == name) | (table['IAUID'] == name)
            table = table[mask]

            if len(table) == 0:
                warnings.warn(f"No object found with name '{name}'.", UserWarning)
                return Table()

        # Convert numeric columns to appropriate types
        numeric_columns = ['peakt', 'peakmag', 'peakabs', 'duration', 'rise', 'fade',
                            'redshift', 'b', 'A_V']

        for col in numeric_columns:
            if col in table.colnames:
                # Replace '-' with NaN and strip '>' prefix for upper limits
                def parse_value(val):
                    if not val or val == '-':
                        return np.nan
                    # Remove '>' prefix if present (indicates upper limit)
                    val_clean = val.lstrip('>')
                    try:
                        return float(val_clean)
                    except ValueError:
                        return np.nan

                table[col] = [parse_value(val) for val in table[col]]

        # Add metadata
        table.meta['query_url'] = response.url
        table.meta['query_time'] = Time.now().iso

        return table



# Create a default instance
ZTFBTS = ZTFBTSClass()
