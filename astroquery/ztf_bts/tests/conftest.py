# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Pytest configuration for ZTF BTS tests
"""

import pytest
from astropy.utils.data import get_pkg_data_filename


@pytest.fixture
def data_path(tmp_path):
    """Fixture to provide path to test data"""
    return get_pkg_data_filename('data', package='astroquery.ztf_bts.tests')
