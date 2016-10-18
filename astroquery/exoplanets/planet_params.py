# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import astropy.units as u
from astropy.time import Time

__all__ = ['PlanetParams']

class PlanetParams(object):
    """
    Exoplanet and host star parameters.
    """
    def __init__(self, *args, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @classmethod
    def from_exoplanets_org(cls, exoplanet_name, cache=True,
                            show_progress=True):
        """
        Gather exoplanet parameters from exoplanets.org [1]_.

        Parameters
        ----------
        exoplanet_name : str
            Name of exoplanet (case insensitive)
        cache : bool (optional)
            Cache exoplanet table to local astropy cache? Default is `True`.
        show_progress : bool (optional)
            Show progress of exoplanet table download (if no cached copy is
            available). Default is `True`.

        Examples
        --------
        To get the orbital period and mid-transit time of the
        planet HD 209458 b, run:

        >>> from astroquery.exoplanets import PlanetParams
        >>> planet = PlanetParams.from_exoplanets_org('HD 209458 b')
        >>> planet.per  # doctest: +FLOAT_CMP
        <Quantity 3.52474859 d>
        >>> planet.tt
        <Time object: scale='utc' format='jd' value=2452826.628514>

        References
        ----------
        .. [1] http://www.exoplanets.org
        """
        from .exoplanets_org import (query_exoplanets_org_catalog, TIME_ATTRS,
                                     BOOL_ATTRS)

        # Load exoplanets table
        table = query_exoplanets_org_catalog(cache=cache,
                                             show_progress=show_progress)

        if not exoplanet_name.lower().strip() in table['NAME_LOWERCASE'].data:
            raise ValueError('Planet "{0}" not found in exoplanets.org catalog')

        row = table.loc[exoplanet_name.lower().strip()]

        kwargs = dict()
        for column in row.colnames:
            value = row[column]

            # If param is unitful quantity, make it a `astropy.units.Quantity`
            if table[column].unit is not None:
                parameter = u.Quantity(value, unit=table[column].unit)

            # If param describes a time, make it a `astropy.time.Time`
            elif column in TIME_ATTRS:
                parameter = Time(value, format=TIME_ATTRS[column])

            elif column in BOOL_ATTRS:
                parameter = bool(value)

            # Otherwise, simply set the parameter to its raw value
            else:
                parameter = value

            # Attributes should be all lowercase:
            kwargs[column.lower()] = parameter

        return cls(**kwargs)

    @classmethod
    def from_exoplanet_archive(cls, exoplanet_name, cache=True,
                               show_progress=True):
        """
        Gather exoplanet parameters from NExScI's Exoplanet Archive [1]_.

        More information on each column is available here [2]_.

        Parameters
        ----------
        exoplanet_name : str
            Name of exoplanet (case insensitive)
        cache : bool (optional)
            Cache exoplanet table to local astropy cache? Default is `True`.
        show_progress : bool (optional)
            Show progress of exoplanet table download (if no cached copy is
            available). Default is `True`.

        Examples
        --------
        To get the orbital period and orbital inclination of the
        planet HD 209458 b, run:

        >>> from astroquery.exoplanets import PlanetParams
        >>> planet = PlanetParams.from_exoplanet_archive('HD 209458 b')
        >>> planet.pl_orbper  # doctest: +FLOAT_CMP
        <Quantity 3.52474859 d>
        >>> planet.pl_orbincl  # doctest: +FLOAT_CMP
        <Quantity 86.929 deg>

        References
        ----------
        .. [1] http://exoplanetarchive.ipac.caltech.edu/index.html
        .. [2] http://exoplanetarchive.ipac.caltech.edu/docs/API_exoplanet_columns.html
        """
        from .exoplanet_archive import (query_exoplanet_archive_catalog,
                                        TIME_ATTRS, BOOL_ATTRS)

        # Load exoplanets table
        table = query_exoplanet_archive_catalog(cache=cache,
                                                show_progress=show_progress)

        if not exoplanet_name.lower().strip() in table['NAME_LOWERCASE'].data:
            raise ValueError('Planet "{0}" not found in exoplanets.org catalog')

        row = table.loc[exoplanet_name.lower().strip()]

        kwargs = dict()
        for column in row.colnames:
            value = row[column]

            # If param is unitful quantity, make it a `astropy.units.Quantity`
            if table[column].unit is not None:
                parameter = u.Quantity(value, unit=table[column].unit)

            # If param describes a time, make it a `astropy.time.Time`
            elif column in TIME_ATTRS:
                parameter = Time(value, format=TIME_ATTRS[column])

            elif column in BOOL_ATTRS:
                parameter = bool(value)

            # Otherwise, simply set the parameter to its raw value
            else:
                parameter = value

            # Attributes should be all lowercase:
            kwargs[column.lower()] = parameter

        return cls(**kwargs)
