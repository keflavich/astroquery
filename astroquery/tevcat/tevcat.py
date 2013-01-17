# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Query TeVCat ( http://tevcat.uchicago.edu/ )

TeVCat is a TeV gamma-ray source catalog that is continually updated.

The data can be browsed on the html pages at http://tevcat.uchicago.edu/
but currently there is no download link for the catalog in CSV or FITS format. 

However all data on the website is contained in a ~ 0.5 MB JSON object
which is easy to extract and process from Python. This is what we do here,
we convert the JSON data to Python and expose it via the TeVCat object.

Usage:

>>> from astroquery.tevcat import TeVCat
>>> tevcat = TeVCat()
>>> print tevcat.table
>>> ... TODO: more examples

TODO:
- Convert dict to astropy.table.Table objects
- Test with Python 3
- Get catalog version (is at the bottom of the html page)
- Handle failure in _get_data, add a timeout? 
"""

import json
import re
import urllib2
import base64
from astropy.logger import log
from astropy.table import Table, Column

__all__ = ('TeVCat')


class TeVCat(object):
    """TeVCat info ( http://tevcat.uchicago.edu/ )"""
    URL = 'http://tevcat.uchicago.edu/'

    def __init__(self):
        self._get_data()
        self._extract_data()
        self._extract_version()
        #self._make_table()
        #del self._html
        #del self._data

    def _get_data(self):
        """Gets the data and sets the 'data' and 'version' attributes"""
        log.info('Downloading {} (should be ~ 0.5 MB)'.format(self.URL))
        response = urllib2.urlopen(self.URL)
        self._html = response.read()

    def _extract_data(self):
        """Extract the data dict from the html"""
        pattern = 'var jsonData = atob\("(.*)"\);'
        matches = re.search(pattern, self._html)
        encoded_data = matches.group(1)
        decoded_data = base64.decodestring(encoded_data)
        data = json.loads(decoded_data)
        # Only keep the useful parts
        self._data = dict(sources=data['sources'], catalogs=data['catalogs'])

    def _extract_version(self):
        """"Extract the version number from the html"""
        pattern = 'Current Catalog Version:\s*(.*)\s*'
        matches = re.search(pattern, self._html)
        self.version = matches.group(1)

    def _make_table(self):
        """Convert the 'data' Python dict into a 'table' astropy.table.Table object"""
        # With this I ran into several issues:
        # - self.data['sources'] is a list of dicts, with dict entries like this:
        # u'coord_ra': u'18 49 01.63'
        # u'greens_cat': None
        # i.e. all keys are unicode objects, values are unicode or None.
        # Isn't there a standard way to convert this into an astropy.table.Table???
        self.table = Table(meta=dict(name='TeVCat'))
        names = [_.encode('utf8') for _ in self._data['sources'][0].keys()]
        for name in names:
            print name
            print 
            for _ in self._data['sources']:
                print _[name]
                print _[name].encode('utf8')
            data = [_[name].encode('utf8') for _ in self._data['sources']]
            print data
            column = Column(name, data)
            print column
            #import IPython; IPython.embed(); 1 / 0
            print '*** before add_column'
            self.table.add_column(column)
            print '*** after add_column'
