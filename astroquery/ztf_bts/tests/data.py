"""
This is a collection of mock responses for the ZTF BTS service.
These are used for offline testing of the module.
"""

# Mock JSON response for a single object query
SINGLE_OBJECT_RESPONSE = {
    "results": [{
        "ZTF_ID": "ZTF18aaqedfj",
        "TNS_ID": "SN2018bff",
        "RA": "13:45:25.21",
        "Dec": "+26:25:27.2",
        "peak_time": 242.77,
        "peak_mag": 18.11,
        "peak_filter": "r",
        "Mabs": -19.09,
        "Duration": 27.8,
        "Rise": 4.738,
        "Fade": 23.062,
        "Type": "SN Ia",
        "Redshift": 0.0623,
        "b": 77.94,
        "AV": 0.04
    }]
}

# Mock JSON response for a region query
REGION_QUERY_RESPONSE = {
    "results": [
        {
            "ZTF_ID": "ZTF18aaqedfj",
            "TNS_ID": "SN2018bff",
            "RA": "13:45:25.21",
            "Dec": "+26:25:27.2",
            "peak_time": 242.77,
            "peak_mag": 18.11,
            "Type": "SN Ia",
            "Redshift": 0.0623
        },
        {
            "ZTF_ID": "ZTF18aaqqoqs",
            "TNS_ID": "SN2018cbh",
            "RA": "13:51:52.89",
            "Dec": "+47:15:25.1",
            "peak_time": 261.74,
            "peak_mag": 18.30,
            "Type": "SN Ia-91T",
            "Redshift": 0.08
        }
    ]
}

# Mock JSON response for a type query
TYPE_QUERY_RESPONSE = {
    "results": [
        {
            "ZTF_ID": "ZTF18aaqedfj",
            "TNS_ID": "SN2018bff",
            "Type": "SN Ia",
            "Redshift": 0.0623,
            "peak_mag": 18.11
        },
        {
            "ZTF_ID": "ZTF18aaqqoqs",
            "TNS_ID": "SN2018cbh",
            "Type": "SN Ia",
            "Redshift": 0.08,
            "peak_mag": 18.30
        }
    ]
}

# Mock empty response
EMPTY_RESPONSE = {
    "results": []
}

# Mock error response
ERROR_RESPONSE = {
    "error": "Invalid query parameters"
}

# Mock light curve data
LIGHT_CURVE_RESPONSE = {
    "name": "ZTF18aaqedfj",
    "data": [
        {"mjd": 58200.5, "mag": 19.5, "magerr": 0.1, "filter": "g"},
        {"mjd": 58201.5, "mag": 19.2, "magerr": 0.1, "filter": "g"},
        {"mjd": 58202.5, "mag": 18.8, "magerr": 0.08, "filter": "r"},
        {"mjd": 58203.5, "mag": 18.5, "magerr": 0.07, "filter": "r"},
    ]
}
