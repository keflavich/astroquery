# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
ZTF Bright Transient Survey (BTS) Module
-----------------------------------------

This module provides access to the Zwicky Transient Facility (ZTF)
Bright Transient Survey Sample Explorer.

:author: astroquery contributors
"""

from astropy import config as _config


class Conf(_config.ConfigNamespace):
    """
    Configuration parameters for `astroquery.ztf_bts`.
    """
    server = _config.ConfigItem(
        'https://sites.astro.caltech.edu/ztf/bts',
        'ZTF BTS server URL.')
    
    timeout = _config.ConfigItem(
        60,
        'Time limit for connecting to ZTF BTS server.')
    
    api_url = _config.ConfigItem(
        'https://sites.astro.caltech.edu/ztf/bts/api.php',
        'ZTF BTS API endpoint.')


conf = Conf()

from .core import ZTFBTS, ZTFBTSClass

__all__ = ['ZTFBTS', 'ZTFBTSClass', 'Conf', 'conf']
