#!/usr/bin/env python
"""
Example script demonstrating the use of the ZTF BTS module for astroquery.

This script shows various ways to query the ZTF Bright Transient Survey catalog.
"""

from astroquery.ztf_bts import ZTFBTS
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.time import Time


def main():
    print("=" * 70)
    print("ZTF Bright Transient Survey Query Examples")
    print("=" * 70)
    
    # Example 1: Query by object name
    print("\n1. Query by ZTF object name:")
    print("-" * 70)
    payload = ZTFBTS.query_object('ZTF18aaqedfj', get_query_payload=True)
    print(f"Querying for: ZTF18aaqedfj")
    print(f"Payload: {payload}")
    
    # Example 2: Query by TNS name
    print("\n2. Query by TNS name:")
    print("-" * 70)
    payload = ZTFBTS.query_object('SN2018bff', get_query_payload=True)
    print(f"Querying for: SN2018bff")
    print(f"Payload: {payload}")
    
    # Example 3: Query by position
    print("\n3. Query by sky position:")
    print("-" * 70)
    coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
    payload = ZTFBTS.query_region(coord, radius=5*u.arcmin, get_query_payload=True)
    print(f"Querying position: RA={coord.ra.deg:.3f}°, Dec={coord.dec.deg:.3f}°")
    print(f"Search radius: 5 arcmin")
    print(f"Payload: {payload}")
    
    # Example 4: Query by classification
    print("\n4. Query by object type:")
    print("-" * 70)
    payload = ZTFBTS.query_by_type('SN Ia', get_query_payload=True)
    print(f"Querying for: Type Ia supernovae")
    print(f"Payload: {payload}")
    
    # Example 5: Query by redshift range
    print("\n5. Query by redshift:")
    print("-" * 70)
    payload = ZTFBTS.query_by_redshift(z_min=0.05, z_max=0.1, get_query_payload=True)
    print(f"Querying redshift range: 0.05 < z < 0.1")
    print(f"Payload: {payload}")
    
    # Example 6: Query by time
    print("\n6. Query by discovery time:")
    print("-" * 70)
    start = Time('2018-01-01')
    end = Time('2018-12-31')
    payload = ZTFBTS.query_by_time(start_time=start, end_time=end, 
                                    get_query_payload=True)
    print(f"Querying time range: 2018-01-01 to 2018-12-31")
    print(f"Start MJD: {start.mjd:.2f}")
    print(f"End MJD: {end.mjd:.2f}")
    print(f"Payload: {payload}")
    
    # Example 7: Complex query with multiple criteria
    print("\n7. Complex query with multiple criteria:")
    print("-" * 70)
    payload = ZTFBTS.query_criteria(
        classification='SN Ia',
        z_min=0.05,
        z_max=0.1,
        peak_mag_max=18.0,
        rise_min=5.0,
        rise_max=20.0,
        abs_mag_min=-20.0,
        get_query_payload=True
    )
    print("Criteria:")
    print("  - Type: SN Ia")
    print("  - Redshift: 0.05 < z < 0.1")
    print("  - Peak magnitude: < 18.0")
    print("  - Rise time: 5-20 days")
    print("  - Absolute magnitude: > -20.0")
    print(f"Payload: {payload}")
    
    # Example 8: Get light curve
    print("\n8. Request light curve data:")
    print("-" * 70)
    payload = ZTFBTS.get_light_curve('ZTF18aaqedfj', get_query_payload=True)
    print(f"Requesting light curve for: ZTF18aaqedfj")
    print(f"Payload: {payload}")
    
    # Example 9: Combined position and filter query
    print("\n9. Combined position and filter query:")
    print("-" * 70)
    payload = ZTFBTS.query_criteria(
        ra=202.469,
        dec=47.195,
        radius=0.1,  # 0.1 degrees = 6 arcmin
        classification='SN Ia',
        z_min=0.05,
        get_query_payload=True
    )
    print("Criteria:")
    print("  - Position: RA=202.469°, Dec=47.195°")
    print("  - Radius: 0.1° (6 arcmin)")
    print("  - Type: SN Ia")
    print("  - Redshift: > 0.05")
    print(f"Payload: {payload}")
    
    print("\n" + "=" * 70)
    print("Note: These examples show the query payloads that would be sent")
    print("to the API. To actually execute queries and retrieve data, remove")
    print("the 'get_query_payload=True' parameter.")
    print("=" * 70)


if __name__ == '__main__':
    main()
