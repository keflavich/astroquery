# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Tests for ZTF BTS module
"""

import pytest
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.table import Table

from astroquery.ztf_bts import ZTFBTS


class TestZTFBTS:
    """Tests for the ZTFBTS class"""
    
    def test_query_object_payload(self):
        """Test that query_object generates the correct payload"""
        payload = ZTFBTS.query_object('ZTF18aaqedfj', get_query_payload=True)
        assert 'name' in payload
        assert payload['name'] == 'ZTF18aaqedfj'
        assert payload['format'] == 'json'
    
    def test_query_object_tns_payload(self):
        """Test query_object with TNS name"""
        payload = ZTFBTS.query_object('SN2018bff', get_query_payload=True)
        assert 'name' in payload
        assert payload['name'] == 'SN2018bff'
    
    def test_query_region_payload(self):
        """Test that query_region generates the correct payload"""
        coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
        payload = ZTFBTS.query_region(coord, radius=5*u.arcmin, get_query_payload=True)
        
        assert 'ra' in payload
        assert 'dec' in payload
        assert 'radius' in payload
        assert abs(payload['ra'] - 202.469) < 0.001
        assert abs(payload['dec'] - 47.195) < 0.001
        # radius should be in degrees
        assert abs(payload['radius'] - (5/60.0)) < 0.001
    
    def test_query_region_string_coord(self):
        """Test query_region with string coordinates"""
        payload = ZTFBTS.query_region('13h30m00s +47d12m00s', 
                                      radius=1*u.arcmin, 
                                      get_query_payload=True)
        assert 'ra' in payload
        assert 'dec' in payload
    
    def test_query_by_type_payload(self):
        """Test query_by_type generates correct payload"""
        payload = ZTFBTS.query_by_type('SN Ia', get_query_payload=True)
        assert 'type' in payload
        assert payload['type'] == 'SN Ia'
    
    def test_query_by_redshift_payload(self):
        """Test query_by_redshift generates correct payload"""
        payload = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1, 
                                           get_query_payload=True)
        assert 'redshift_min' in payload
        assert 'redshift_max' in payload
        assert payload['redshift_min'] == 0.05
        assert payload['redshift_max'] == 0.1
    
    def test_query_by_redshift_only_min(self):
        """Test query_by_redshift with only z_min"""
        payload = ZTFBTS.query_by_redshift(z_min=0.05, get_query_payload=True)
        assert 'redshift_min' in payload
        assert 'redshift_max' not in payload
    
    def test_query_by_time_payload(self):
        """Test query_by_time generates correct payload"""
        start = Time('2018-01-01')
        end = Time('2018-12-31')
        payload = ZTFBTS.query_by_time(start_time=start, end_time=end, 
                                       get_query_payload=True)
        assert 'time_min' in payload
        assert 'time_max' in payload
        assert payload['time_min'] == start.mjd
        assert payload['time_max'] == end.mjd
    
    def test_query_by_time_string(self):
        """Test query_by_time with string times"""
        payload = ZTFBTS.query_by_time(start_time='2018-01-01', 
                                       end_time='2018-12-31',
                                       get_query_payload=True)
        assert 'time_min' in payload
        assert 'time_max' in payload
    
    def test_query_criteria_combined(self):
        """Test query_criteria with multiple parameters"""
        payload = ZTFBTS.query_criteria(
            classification='SN Ia',
            z_min=0.05,
            z_max=0.1,
            peak_mag_max=18.0,
            rise_min=5.0,
            get_query_payload=True
        )
        assert 'type' in payload
        assert 'redshift_min' in payload
        assert 'redshift_max' in payload
        assert 'peak_mag_max' in payload
        assert 'rise_min' in payload
        assert payload['type'] == 'SN Ia'
        assert payload['redshift_min'] == 0.05
        assert payload['redshift_max'] == 0.1
        assert payload['peak_mag_max'] == 18.0
        assert payload['rise_min'] == 5.0
    
    def test_query_criteria_position_and_filters(self):
        """Test query_criteria with position and other filters"""
        payload = ZTFBTS.query_criteria(
            ra=202.469,
            dec=47.195,
            radius=0.1,
            classification='SN II',
            abs_mag_min=-20.0,
            get_query_payload=True
        )
        assert 'ra' in payload
        assert 'dec' in payload
        assert 'radius' in payload
        assert 'type' in payload
        assert 'abs_mag_min' in payload
    
    def test_get_light_curve_payload(self):
        """Test get_light_curve generates correct payload"""
        payload = ZTFBTS.get_light_curve('ZTF18aaqedfj', get_query_payload=True)
        assert 'name' in payload
        assert 'format' in payload
        assert payload['name'] == 'ZTF18aaqedfj'
        assert payload['format'] == 'lightcurve'


@pytest.mark.remote_data
class TestZTFBTSRemote:
    """Remote tests that actually query the ZTF BTS service"""
    
    @pytest.mark.skip(reason="Requires actual API implementation")
    def test_query_object_remote(self):
        """Test actual query_object call"""
        result = ZTFBTS.query_object('ZTF18aaqedfj')
        assert isinstance(result, Table)
        assert len(result) > 0
    
    @pytest.mark.skip(reason="Requires actual API implementation")
    def test_query_region_remote(self):
        """Test actual query_region call"""
        coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
        result = ZTFBTS.query_region(coord, radius=5*u.arcmin)
        assert isinstance(result, Table)
    
    @pytest.mark.skip(reason="Requires actual API implementation")
    def test_query_by_type_remote(self):
        """Test actual query_by_type call"""
        result = ZTFBTS.query_by_type('SN Ia')
        assert isinstance(result, Table)
        assert len(result) > 0
