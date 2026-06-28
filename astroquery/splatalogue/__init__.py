# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Splatalogue Catalog Query Tool
-----------------------------------

:Author: Adam Ginsburg (adam.g.ginsburg@gmail.com)

:Originally contributed by:

     Magnus Vilhelm Persson (magnusp@vilhelm.nu)
"""
from astropy import config as _config


class Conf(_config.ConfigNamespace):
    """
    Configuration parameters for `astroquery.splatalogue`.
    """
    slap_url = _config.ConfigItem(
        'https://find.nrao.edu/splata-slap/slap',
        'Splatalogue SLAP interface URL (not used).')
    base_url = 'https://splatalogue.online'
    query_url = _config.ConfigItem(
        f'{base_url}/splata-slap/advanceded/false',
        'Splatalogue web interface URL.')
    timeout = _config.ConfigItem(
        60,
        'Time limit for connecting to Splatalogue server.')
    lines_limit = _config.ConfigItem(
        1000,
        'Limit to number of lines exported.')
    db_path = _config.ConfigItem(
        '',
        'Path to a local CASA-hosted Splatalogue SQLite database. If empty, '
        'the database is auto-located from a CASA/casaconfig installation '
        'when a local query is requested.')
    use_local = _config.ConfigItem(
        'fallback',
        "Default routing for ``query_lines``: 'never' (web only), 'fallback' "
        "(query the web service, but fall back to a local CASA Splatalogue "
        "database if the service times out or is unreachable), or 'always' "
        "(query the local database directly, never touching the network).",
        cfgtype='string')
    local_table = _config.ConfigItem(
        '',
        'Name of the table to read inside the local Splatalogue SQLite '
        'database. If empty, the table is detected automatically.')


conf = Conf()

from .core import Splatalogue, SplatalogueClass

__all__ = ['Splatalogue', 'SplatalogueClass',
           'Conf', 'conf',
           ]
