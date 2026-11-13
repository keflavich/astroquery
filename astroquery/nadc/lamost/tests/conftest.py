# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Shared fixtures: sample spectrum FITS files."""

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits


@pytest.fixture
def sample_lrs_fits():
    """
    Return path to a real low-resolution spectrum FITS file for testing.

    Returns
    -------
    str
        Absolute path to the LRS FITS file.
    """
    test_dir = Path(__file__).parent
    fits_file = test_dir / 'data' / 'spec-57278-EG224429N215706B01_sp01-001.fits.gz'

    if not fits_file.exists():
        pytest.fail(f"Required test FITS file is missing: {fits_file}")

    return str(fits_file)


@pytest.fixture
def sample_mrs_fits(tmp_path):
    """
    Create a synthetic medium-resolution spectrum FITS file for testing.

    Exercise lowercase column names and simple B/R extension names independently
    of the historical and modern archive excerpts.

    Returns
    -------
    str
        Path to the created MRS FITS file.
    """
    # Create primary HDU
    primary = fits.PrimaryHDU()

    # Create multiple extensions for different bands
    bands = ['B', 'R']
    hdu_list = [primary]

    for band in bands:
        # Create synthetic spectrum data
        n_pixels = 32
        wavelength = np.linspace(5000, 6000, n_pixels) if band == 'B' else np.linspace(6000, 7000, n_pixels)
        flux = np.arange(n_pixels, dtype=np.float32) + (1 if band == 'B' else 2)
        ivar = np.ones(n_pixels, dtype=np.float32)

        # Create structured array matching LAMOST MRS format
        data = np.array(
            [(flux, ivar, wavelength)],
            dtype=[('flux', 'f4', n_pixels), ('ivar', 'f4', n_pixels), ('wavelength', 'f8', n_pixels)]
        )

        # Create binary table HDU
        hdu = fits.BinTableHDU(data=data, name=band)
        hdu_list.append(hdu)

    # Write to file
    fits_path = tmp_path / 'test_mrs_spectrum.fits'
    hdul = fits.HDUList(hdu_list)
    hdul.writeto(fits_path, overwrite=True)
    hdul.close()

    return str(fits_path)
