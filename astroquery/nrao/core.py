# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os.path
import keyring
import numpy as np
import re
import tarfile
import string
import requests
import warnings

from pkg_resources import resource_filename
from bs4 import BeautifulSoup
import pyvo
from urllib.parse import urljoin

from astropy.table import Table, Column, vstack
from astroquery import log
from astropy.utils.console import ProgressBar
from astropy import units as u
from astropy.time import Time

try:
    from pyvo.dal.sia2 import SIA2_PARAMETERS_DESC, SIA2Service
except ImportError:
    # Can be removed once min version of pyvo is 1.5
    from pyvo.dal.sia2 import SIA_PARAMETERS_DESC as SIA2_PARAMETERS_DESC
    from pyvo.dal.sia2 import SIAService as SIA2Service

from ..exceptions import LoginError
from ..utils import commons
from ..utils.process_asyncs import async_to_sync
from ..query import BaseQuery, QueryWithLogin, BaseVOQuery
from . import conf, auth_urls, tap_urls
from astroquery.exceptions import CorruptDataWarning
from ..alma.tapsql import (_gen_str_sql, _gen_numeric_sql,
                     _gen_band_list_sql, _gen_datetime_sql, _gen_pol_sql, _gen_pub_sql,
                     _gen_science_sql, _gen_spec_res_sql, ALMA_DATE_FORMAT)
from .tapsql import (_gen_pos_sql)

__all__ = {'NraoClass',}

__doctest_skip__ = ['NraoClass.*']

NRAO_BANDS = {}

TAP_SERVICE_PATH = 'tap'

NRAO_FORM_KEYS = {
    'Position': {
        'Source name (astropy Resolver)': ['source_name_resolver',
                                           'SkyCoord.from_name', _gen_pos_sql],
        'Source name (NRAO)': ['source_name_alma', 'target_name', _gen_str_sql],
        'RA Dec (Sexagesimal)': ['ra_dec', 's_ra, s_dec', _gen_pos_sql],
        'Galactic (Degrees)': ['galactic', 'gal_longitude, gal_latitude',
                               _gen_pos_sql],
        'Angular resolution (arcsec)': ['spatial_resolution',
                                        'spatial_resolution', _gen_numeric_sql],
        'Largest angular scale (arcsec)': ['spatial_scale_max',
                                           'spatial_scale_max', _gen_numeric_sql],
        'Field of view (arcsec)': ['fov', 's_fov', _gen_numeric_sql]
    },
}


def _gen_sql(payload):
    sql = 'select * from tap_schema.obscore'
    where = ''
    unused_payload = payload.copy()
    if payload:
        for constraint in payload:
            for attrib_category in NRAO_FORM_KEYS.values():
                for attrib in attrib_category.values():
                    if constraint in attrib:
                        # use the value and the second entry in attrib which
                        # is the new name of the column
                        val = payload[constraint]
                        if constraint == 'em_resolution':
                            # em_resolution does not require any transformation
                            attrib_where = _gen_numeric_sql(constraint, val)
                        else:
                            attrib_where = attrib[2](attrib[1], val)
                        if attrib_where:
                            if where:
                                where += ' AND '
                            else:
                                where = ' WHERE '
                            where += attrib_where

                        # Delete this key to see what's left over afterward
                        #
                        # Use pop to avoid the slight possibility of trying to remove
                        # an already removed key
                        unused_payload.pop(constraint)

    if unused_payload:
        # Left over (unused) constraints passed.  Let the user know.
        remaining = [f'{p} -> {unused_payload[p]}' for p in unused_payload]
        raise TypeError(f'Unsupported arguments were passed:\n{remaining}')

    return sql + where


class NraoAuth(BaseVOQuery, BaseQuery):
    pass

class NraoClass(BaseQuery):
    TIMEOUT = conf.timeout
    archive_url = conf.archive_url
    USERNAME = conf.username

    def __init__(self):
        # sia service does not need disambiguation but tap does
        super().__init__()
        self._sia = None
        self._tap = None
        self._datalink = None
        self._sia_url = None
        self._tap_url = None
        self._datalink_url = None
        self._auth = NraoAuth()

    @property
    def auth(self):
        return self._auth

    @property
    def datalink(self):
        if not self._datalink:
            self._datalink = pyvo.dal.adhoc.DatalinkService(self.datalink_url)
        return self._datalink

    @property
    def datalink_url(self):
        if not self._datalink_url:
            try:
                self._datalink_url = urljoin(self._get_dataarchive_url(), DATALINK_SERVICE_PATH)
            except requests.exceptions.HTTPError as err:
                log.debug(
                    f"ERROR getting the NRAO Archive URL: {str(err)}")
                raise err
        return self._datalink_url

    @property
    def sia(self):
        if not self._sia:
            self._sia = SIA2Service(baseurl=self.sia_url)
        return self._sia

    @property
    def sia_url(self):
        if not self._sia_url:
            try:
                self._sia_url = urljoin(self._get_dataarchive_url(), SIA_SERVICE_PATH)
            except requests.exceptions.HTTPError as err:
                log.debug(
                    f"ERROR getting the  NRAO Archive URL: {str(err)}")
                raise err
        return self._sia_url

    @property
    def tap(self):
        if not self._tap:
            self._tap = pyvo.dal.tap.TAPService(baseurl=self.tap_url, session=self._session)
        return self._tap

    @property
    def tap_url(self):
        if not self._tap_url:
            try:
                self._tap_url = urljoin(self._get_dataarchive_url(), TAP_SERVICE_PATH)
            except requests.exceptions.HTTPError as err:
                log.debug(
                    f"ERROR getting the  NRAO Archive URL: {str(err)}")
                raise err
        return self._tap_url

    def query_tap(self, query, maxrec=None):
        """
        Send query to the NRAO TAP. Results in pyvo.dal.TapResult format.
        result.table in Astropy table format

        Parameters
        ----------
        maxrec : int
            maximum number of records to return

        """
        log.debug('TAP query: {}'.format(query))
        return self.tap.search(query, language='ADQL', maxrec=maxrec)

    def _get_dataarchive_url(self):
        return tap_urls[0]

    def query_object_async(self, object_name, *, payload=None, **kwargs):
        """
        Query the archive for a source name.

        Parameters
        ----------
        object_name : str
            The object name.  Will be resolved by astropy.coord.SkyCoord
        public : bool
            True to return only public datasets, False to return private only,
            None to return both
        science : bool
            True to return only science datasets, False to return only
            calibration, None to return both
        payload : dict
            Dictionary of additional keywords.  See `help`.
        """
        if payload is not None:
            payload['source_name_resolver'] = object_name
        else:
            payload = {'source_name_resolver': object_name}
        return self.query_async(payload=payload, **kwargs)

    def query_region_async(self, coordinate, radius, *,
                           payload=None, **kwargs):
        """
        Query the NRAO archive with a source name and radius

        Parameters
        ----------
        coordinates : str / `astropy.coordinates`
            the identifier or coordinates around which to query.
        radius : str / `~astropy.units.Quantity`, optional
            the radius of the region
        payload : dict
            Dictionary of additional keywords.  See `help`.
        """
        rad = radius
        if not isinstance(radius, u.Quantity):
            rad = radius*u.deg
        obj_coord = commons.parse_coordinates(coordinate).icrs
        ra_dec = '{}, {}'.format(obj_coord.to_string(), rad.to(u.deg).value)
        if payload is None:
            payload = {}
        if 'ra_dec' in payload:
            payload['ra_dec'] += ' | {}'.format(ra_dec)
        else:
            payload['ra_dec'] = ra_dec

        return self.query_async(payload=payload, **kwargs)

    def query_async(self, payload, *, get_query_payload=False,
                    maxrec=None, **kwargs):
        """
        Perform a generic query with user-specified payload

        Parameters
        ----------
        payload : dictionary
            Please consult the `help` method
        legacy_columns : bool
            True to return the columns from the obsolete NRAO advanced query,
            otherwise return the current columns based on ObsCore model.
        get_query_payload : bool
            Flag to indicate whether to simply return the payload.
        maxrec : integer
            Cap on the amount of records returned.  Default is no limit.

        Returns
        -------

        Table with results. Columns are those in the NRAO ObsCore model
        (see ``help_tap``) unless ``legacy_columns`` argument is set to True.
        """

        if payload is None:
            payload = {}
        for arg in kwargs:
            value = kwargs[arg]
            if arg in payload:
                payload[arg] = '{} {}'.format(payload[arg], value)
            else:
                payload[arg] = value
        print(payload)
        query = _gen_sql(payload)
        print(query)
        if get_query_payload:
            # Return the TAP query payload that goes out to the server rather
            # than the unprocessed payload dict from the python side
            return query

        result = self.query_tap(query, maxrec=maxrec)

        if result is not None:
            result = result.to_table()
        else:
            # Should not happen
            raise RuntimeError('BUG: Unexpected result None')

        return result


Nrao = NraoClass()
