# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
LAMOST Spectroscopic Survey Query Tool
---------------------------------------

This module provides access to the LAMOST (Large Sky Area Multi-Object Fiber
Spectroscopic Telescope) spectroscopic survey data through the IVOA services
(TAP and SSAP) of each data release.
"""

from astropy import config as _config


class Conf(_config.ConfigNamespace):
    """
    Configuration parameters for `astroquery.nadc.lamost`.
    """

    server = _config.ConfigItem(
        'https://www.lamost.org/openapi',
        'LAMOST OpenAPI base URL, including /openapi, used for spectrum and '
        'catalog-file downloads.')

    vo_server = _config.ConfigItem(
        'https://www.lamost.org',
        'Base URL of the LAMOST data releases; the TAP and SSAP services are '
        'at <vo_server>/<data_release>/<sub_version>/voservice/{tap,ssap}.')

    timeout = _config.ConfigItem(
        60,
        'Timeout for LAMOST queries in seconds')

    data_release = _config.ConfigItem(
        'dr10',
        'Default LAMOST data release (e.g., dr10, dr11, dr12; the VO services exist for DR10 and later)')

    sub_version = _config.ConfigItem(
        'v2.0',
        'Default API sub-version')

    token = _config.ConfigItem(
        '',
        'Token appended to download requests, for releases that require one. '
        'TAP and SSAP queries are anonymous.')


conf = Conf()

from .core import Lamost, LamostClass
from .core import parse_lrs_spectrum, parse_mrs_spectrum

__all__ = ['Lamost', 'LamostClass',
           'Conf', 'conf',
           'parse_lrs_spectrum', 'parse_mrs_spectrum']
