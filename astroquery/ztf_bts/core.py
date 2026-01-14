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
        """
        request_payload = self._args_to_payload(name=object_name)
        
        if get_query_payload:
            return request_payload
            
        response = self._request('GET', self.API_URL, params=request_payload,
                                timeout=self.TIMEOUT, cache=cache)
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
        
        # Map parameter names to API parameter names
        param_mapping = {
            'name': 'name',
            'ra': 'ra',
            'dec': 'dec',
            'radius': 'radius',
            'classification': 'type',
            'z_min': 'redshift_min',
            'z_max': 'redshift_max',
            'peak_mag_min': 'peak_mag_min',
            'peak_mag_max': 'peak_mag_max',
            'abs_mag_min': 'abs_mag_min',
            'abs_mag_max': 'abs_mag_max',
            'duration_min': 'duration_min',
            'duration_max': 'duration_max',
            'rise_min': 'rise_min',
            'rise_max': 'rise_max',
            'fade_min': 'fade_min',
            'fade_max': 'fade_max',
            'galactic_lat_min': 'b_min',
            'galactic_lat_max': 'b_max',
            'start_mjd': 'time_min',
            'end_mjd': 'time_max',
        }
        
        for key, value in kwargs.items():
            if value is not None:
                api_key = param_mapping.get(key, key)
                request_payload[api_key] = value
        
        # Set default output format to JSON
        request_payload['format'] = 'json'
        
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
        # Check for errors
        response.raise_for_status()
        
        # Parse JSON response
        try:
            data = response.json()
        except ValueError:
            warnings.warn("Could not parse JSON response from server.", UserWarning)
            return Table()
        
        # Handle different response formats
        if isinstance(data, dict):
            # Check if it's an error response
            if 'error' in data:
                warnings.warn(f"API Error: {data['error']}", UserWarning)
                return Table()
            
            # If the response is a dict with results
            if 'results' in data:
                data = data['results']
            elif 'data' in data:
                data = data['data']
        
        # Handle empty results
        if not data or (isinstance(data, list) and len(data) == 0):
            warnings.warn("Query returned no results.", UserWarning)
            return Table()
        
        # Convert to astropy Table
        if isinstance(data, list):
            table = Table(rows=data)
        else:
            # Single object result
            table = Table([data])
        
        # Add metadata
        table.meta['query_url'] = response.url
        table.meta['query_time'] = Time.now().iso
        
        return table


# Create a default instance
ZTFBTS = ZTFBTSClass()
