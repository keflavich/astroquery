# ZTF BTS Module Implementation Summary

## Overview
This module provides an interface to query the Zwicky Transient Facility (ZTF) Bright Transient Survey (BTS) Sample Explorer at https://sites.astro.caltech.edu/ztf/bts/explorer.php

## Files Created

### Core Module Files
1. **`astroquery/ztf_bts/__init__.py`**
   - Configuration parameters (server URL, timeout, API endpoint)
   - Module exports

2. **`astroquery/ztf_bts/core.py`**
   - Main `ZTFBTSClass` implementation
   - Query methods for different search criteria
   - Response parsing functionality

3. **`astroquery/ztf_bts/setup_package.py`**
   - Package data configuration

### Test Files
4. **`astroquery/ztf_bts/tests/__init__.py`**
   - Test package marker

5. **`astroquery/ztf_bts/tests/test_ztf_bts.py`**
   - Comprehensive unit tests
   - Tests for all query methods
   - Payload validation tests

6. **`astroquery/ztf_bts/tests/conftest.py`**
   - Pytest configuration and fixtures

7. **`astroquery/ztf_bts/tests/data.py`**
   - Mock response data for offline testing

### Documentation Files
8. **`astroquery/ztf_bts/README.rst`**
   - Quick start guide
   - Usage examples
   - Reference information

9. **`astroquery/ztf_bts/examples.py`**
   - Executable examples demonstrating all features

10. **`docs/ztf_bts/ztf_bts.rst`**
    - Complete Sphinx documentation
    - Detailed API documentation

## Key Features

### Query Methods Implemented

1. **`query_object(object_name)`**
   - Query by ZTF name (e.g., 'ZTF18aaqedfj')
   - Query by TNS name (e.g., 'SN2018bff')

2. **`query_region(coordinates, radius)`**
   - Query by sky position
   - Accepts SkyCoord objects or string coordinates
   - Configurable search radius

3. **`query_by_type(obj_type)`**
   - Search by classification type
   - Supports all ZTF BTS classification schemes

4. **`query_by_redshift(z_min, z_max)`**
   - Search within redshift ranges
   - Supports one-sided constraints

5. **`query_by_time(start_time, end_time)`**
   - Search by discovery/peak time
   - Accepts Time objects or ISO strings

6. **`query_criteria(**kwargs)`**
   - General-purpose query method
   - Combines multiple search criteria
   - Supports all available filters:
     - Position (ra, dec, radius)
     - Classification
     - Redshift
     - Magnitudes (peak and absolute)
     - Temporal properties (duration, rise, fade)
     - Galactic coordinates

7. **`get_light_curve(ztf_name)`**
   - Retrieve photometric time series data

### Design Patterns

- **Async/Sync Pattern**: Uses `@async_to_sync` decorator following astroquery conventions
- **BaseQuery Inheritance**: Inherits from `astroquery.query.BaseQuery`
- **Caching**: Built-in HTTP response caching
- **Payload Inspection**: All methods support `get_query_payload=True`
- **Error Handling**: Graceful handling of empty results and API errors

### API Parameter Mapping

The module maps user-friendly parameter names to API-specific names:

| User Parameter | API Parameter |
|----------------|---------------|
| `classification` | `type` |
| `z_min` | `redshift_min` |
| `z_max` | `redshift_max` |
| `galactic_lat_min` | `b_min` |
| `galactic_lat_max` | `b_max` |
| `start_mjd` | `time_min` |
| `end_mjd` | `time_max` |

## Testing

The module includes comprehensive tests:

- **Unit Tests**: Test payload generation for all query methods
- **Validation Tests**: Verify parameter parsing and conversion
- **Mock Data**: Includes sample responses for offline testing
- **Remote Tests**: Marked with `@pytest.mark.remote_data` (skipped by default)

## Usage Examples

### Basic Queries
```python
from astroquery.ztf_bts import ZTFBTS

# Query by name
result = ZTFBTS.query_object('ZTF18aaqedfj')

# Query by position
from astropy.coordinates import SkyCoord
import astropy.units as u
coord = SkyCoord(ra=202.469, dec=47.195, unit=(u.deg, u.deg))
result = ZTFBTS.query_region(coord, radius=5*u.arcmin)

# Query by type
result = ZTFBTS.query_by_type('SN Ia')
```

### Advanced Queries
```python
# Complex multi-criteria query
result = ZTFBTS.query_criteria(
    classification='SN Ia',
    z_min=0.05,
    z_max=0.1,
    peak_mag_max=18.0,
    rise_min=5.0,
    rise_max=20.0
)

# Get light curve
lc = ZTFBTS.get_light_curve('ZTF18aaqedfj')
```

## Notes on API Implementation

The actual ZTF BTS Explorer currently uses a web form interface. This module implements
a proposed API structure based on the explorer's query parameters. To use this module
with the real service, one of the following would be needed:

1. **Official API**: The ZTF BTS team could implement a JSON API endpoint
2. **Web Scraping**: The module could be adapted to parse the HTML/JavaScript interface
3. **Custom Backend**: A middleware API service could be created

The current implementation provides the framework and demonstrates the intended functionality.
The query payload generation is fully functional and can be inspected using
`get_query_payload=True`.

## Classification Types

The module supports all ZTF BTS classification types:

**Type Ia Supernovae:**
- SN Ia, SN Ia-91T, SN Ia-91bg, SN Ia-CSM, SN Ia-pec

**Core-Collapse Supernovae:**
- SN II, SN IIP, SN IIn, SN IIb, SN Ib, SN Ic, SN Ic-BL, SN Ibn, SN Icn

**Superluminous Supernovae:**
- SLSN-I, SLSN-II

**Other Transients:**
- nova, TDE (Tidal Disruption Event), CV (Cataclysmic Variable)

## Citation

Users should cite:
> Perley, D. A., et al. 2020, ApJ, 904, 35
> "The Zwicky Transient Facility Bright Transient Survey. II. A Public Statistical 
> Sample for Exploring Supernova Demographics"
> https://arxiv.org/abs/2009.01242

## Future Enhancements

Potential improvements:
1. Implement actual HTTP requests to ZTF BTS service
2. Add cutout image retrieval
3. Add spectrum download functionality
4. Implement batch query capabilities
5. Add result caching and offline mode
6. Support for custom filters and saved queries
