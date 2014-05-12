# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Query fucntion for the Open Exoplanet Catalogue 
-----------------------------------------------

The function query_system_xml simply returns the xml file from one of the servers and returns it. 

The function query_planet searches for a planet and returns its properties as a python dictionary.

The function query_system_to_obj returns a System object as defined by oec2py.

The function query_planet_to_obj returns a System object of a planet as defined by oec2py

------------------
:Author: Hanno Rein (hanno@hanno-rein.de)
"""
from __future__ import print_function
from oec2py import xml_to_obj
import sys
import urllib2
import csv
import xml.etree.ElementTree as ET
from astropy.config import ConfigurationItem


class CatalogueOpeningError(Exception):
    """Exception for error in opening open exoplanet catalogue"""
    pass

__all__ = ['query_system_xml','query_planet_obj','query_planet_xml', 'query_planet_dict', 'query_system_obj',\
        'query_system_dict', 'all_system_identifiers','all_planet_identifiers','all_star_identifiers', 'change_to_local', 'change_to_remote']

aliases = None
OEC_SERVER = 'https://raw.github.com/hannorein/open_exoplanet_catalogue/master/'
OEC_META_SERVER = 'https://raw.github.com/hannorein/oec_meta/master/'

def change_to_local(filepath):
    """(str) -> Notype
    change the querying to use a local version of the open exoplanet catalogue.

    filepath must be absolute.

    change_to_local("/home/usrname/open_exoplanet_catalogue/")
    >>>"Now using local data at /home/usrname/open_exoplanet_catalogue"
    """
    global OEC_SERVER
    global OEC_META_SERVER
    OEC_SERVER = "file://"+filepath
    OEC_META_SERVER = "file://"+filepath

    print("Now using local data at" + filepath)

def change_to_remote():
    """ Change the queries to use the default remote database"""
    global OEC_SERVER
    global OEC_META_SERVER
    OEC_SERVER = 'https://raw.github.com/hannorein/open_exoplanet_catalogue/master/'
    OEC_META_SERVER = 'https://raw.github.com/hannorein/oec_meta/master/'

    print("Now using remote data")
    print("Fetching data may be slow. Switch to local")

def find_system_for_alias(alias):
    """ (str) -> str
    Find the system for the given object, whether it be a star, binary or planet

    find_system_for_alias("Kepler-20 b")
    >>>"Kepler-20"

    find_system_for_alias("KOI-546 c")
    >>>"Kepler-182"
    """
    global aliases
    alias = alias.strip()
    if aliases is None:
        metaserver = OEC_META_SERVER
        metaurl = metaserver+"aliases.csv"
        try:
            metacsv = urllib2.urlopen(metaurl)
            aliases = list(csv.reader(metacsv))
        except:
            raise CatalogueOpeningError("Error getting Open Exoplanet Catalogue file '"+metaurl+\
			    "'.\nCheck system_id and server.")
    for a in aliases:
        if a[0] == alias:
            return a[1]
    
def get_xml_for_system(system,category='systems'):
    """"(str, *str)-> str
    Returns the xml file as a str for the given system
    """

    if(OEC_SERVER[:4] != "file"):
        print("Using remote data, queries may be slow")

    try:
        url = OEC_SERVER + category + "/" +\
                urllib2.quote(system) + ".xml"
        xml = urllib2.urlopen(url).read()
    except TypeError:
        raise TypeError("Error, system or category not defined")
    except:
        raise CatalogueOpeningError("Error getting Open Exoplanet Catalogue file '" + url +\
			"'.\nCheck system_id and server.")
    else:
        return xml

def xml_element_to_dict(e):
    """(str) -> dict
    Converts xml tree to dictionary
    """

    d = {}
    for c in e.getchildren():
        d[c.tag] = c.text
    return d
    
def query_system_xml(system_id,category='systems'):
    """ (str, *str) -> str 
    Queries the database and returns the XML data of the system 
    """

    system = find_system_for_alias(system_id)
    return get_xml_for_system(system,category)

def query_system_dict(system_id, category='systems'):
    """ (str, *str) -> dict 
    Queries the database and returns the python dict of data of the system 
    """

    system = find_system_for_alias(system_id)
    return xml_element_to_dict(get_xml_for_system(system,category))

def query_system_obj(system_id, category='systems'):
    """ (str, *str) -> System 
    Queries the database and returns a System object of the system
    """

    return xml_to_obj(query_system_xml(system_id,category))

def query_planet_dict(planet_id,category='systems'):
    """ (str, *str) -> dict
    Queries the database and returns the planet data as a python dictionary 
    """

    system = find_system_for_alias(planet_id)
    xml = get_xml_for_system(system,category)
    systemroot = ET.fromstring(xml)
    planets = systemroot.findall(".//planet")
    for planet in planets:
        names = planet.findall("./name")
        for name in names:
            if name.text == planet_id.strip():
                return xml_element_to_dict(planet)

    return None

def query_planet_xml(planet_id, category='systems'):
    """ (str, *str) -> xml 
    Queries the database and returns the planet data as a python dictionary 
    """

    system = find_system_for_alias(planet_id)
    xml = get_xml_for_system(system,category)
    systemroot = ET.fromstring(xml)
    planets = systemroot.findall(".//planet")
    for planet in planets:
        names = planet.findall("./name")
        for name in names:
            if name.text == planet_id.strip():
                return planet

    return None


def query_planet_obj(planet_id, category='systems'):
    """(str, *str) -> System
    Queries the database and returns the planet data as a System type
    """

    system = find_system_for_alias(planet_id)
    xml = get_xml_for_system(system,category)
    sysobj = xml_to_obj(xml)
    return sysobj.find_system(planet_id.strip(), "planet")


    return None

def all_system_identifiers():
    """(NoType) -> list
    returns a list of strings of all of the unique systems
    """

    global aliases
    if aliases is None:
        metaserver = OEC_META_SERVER
        metaurl = metaserver+"aliases.csv"
        try:
            metacsv = urllib2.urlopen(metaurl)
            aliases = list(csv.reader(metacsv))
        except:
            raise CatalogueOpeningError("Error getting Open Exoplanet Catalogue file '"+metaurl+\
			    "'.\nCheck system_id and server.")
    systems = []
    for sys in aliases:
        if sys[2] == "system" and not (sys[1] in systems):
            systems.append(sys[1])
    return systems

def all_planet_identifiers():
    """(NoType) -> list
    returns a list of strings of all of the unique planets 
    """

    global aliases
    if aliases is None:
        metaserver = OEC_META_SERVER
        metaurl = metaserver+"aliases.csv"
        try:
            metacsv = urllib2.urlopen(metaurl)
            aliases = list(csv.reader(metacsv))
        except:
            raise CatalogueOpeningError("Error getting Open Exoplanet Catalogue file '"+metaurl+\
			    "'.\nCheck system_id and server.")
    planets = []
    for plan in aliases:
        if plan[2] == "planet" and not(plan[3] in planets):
            planets.append(plan[3])
    return planets

def all_star_identifiers():  
    """(NoType) -> list
    returns a list of strings of all of the unique stars 
    """

    global aliases
    if aliases is None:
        metaserver = OEC_META_SERVER
        metaurl = metaserver+"aliases.csv"
        try:
            metacsv = urllib2.urlopen(metaurl)
            aliases = list(csv.reader(metacsv))
        except:
            raise CatalogueOpeningError("Error getting Open Exoplanet Catalogue file '"+metaurl+\
			    "'.\nCheck system_id and server.")
    stars = []
    for star in aliases:
        if star[2] == "star" and not(star[3] in stars):
            stars.append(star[3])
    return stars


