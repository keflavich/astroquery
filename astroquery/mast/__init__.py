# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MAST Query Tool
===============

Module to query the Barbara A. Mikulski Archive for Space Telescopes (MAST).
"""

from astropy import config as _config


class Conf(_config.ConfigNamespace):
    """
    Configuration parameters for `astroquery.mast`.
    """

    server = _config.ConfigItem(
        'https://mast.stsci.edu',
        'Name of the MAST server.')
    ssoserver = _config.ConfigItem(
        'https://ssoportal.stsci.edu',
        'MAST SSO Portal server.')
    catalogsserver = _config.ConfigItem(
        'https://catalogs.mast.stsci.edu',
        'Name of the MAST Catalogs server.')
    timeout = _config.ConfigItem(
        600,
        'Time limit for requests from the STScI server.')
    pagesize = _config.ConfigItem(
        50000,
        'Number of results to request at once from the STScI server.')


conf = Conf()


from .core import Catalogs, CatalogsClass
from .tesscut import TesscutClass, Tesscut
from .discovery_portal import MastClass, Mast
from .observations import Observations, ObservationsClass
from . import utils

__all__ = ['Observations', 'ObservationsClass',
           'Catalogs', 'CatalogsClass',
           'Mast', 'MastClass',
           'Tesscut', 'TesscutClass',
           'Conf', 'conf', 'utils'
           ]
