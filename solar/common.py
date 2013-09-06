# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import Pysolar as pysol


def az_to_str(arcsec):
    """
    Convert azimuth to a pretty printed string
    seconds -- azimuth in seconds
    Returns string like ±18d26m32s
    """
    az = int(abs(arcsec))
    d, m, s = az // 3600, (az // 60) % 60, az % 60
    if arcsec < 0:
        sign = '-'
    else:
        sign = '+'
    return '{}{:02d}d{:02d}m{:02d}s'.format(sign, d, m, s)


def alt_to_str(arcsec):
    """
    Convert a altitude to a pretty printed string
    arcsec -- altitude in arcseconds
    Returns string like ±72d26m32s
    """
    return az_to_str(arcsec)


def mean_solar_time(longitude):
    """
    Calculate the mean solar time from the longitude
    longitude -- Current longitude
    Returns mean solar time as a python Datetime object
    """
    lt = datetime.utcnow()
    dt = timedelta(seconds=longitude / 15 * 3600)
    mst = lt + dt
    return mst


def sun_az(longitude, latitude):
    """
    Calculate the azimuth of the sun
    longitude -- Current longitude
    latitude -- Current latitude
    Returns the Sun's azimuth in arcseconds
    """
    return pysol.GetAzimuth(latitude, longitude, datetime.utcnow()) * 3600


def sun_alt(longitude, latitude):
    """
    Calculate the altitude of the Sun
    longitude -- Current longitude
    latitude -- Current latitude
    Returns the Sun's altitude in arcseconds
    """
    return pysol.GetAltitude(latitude, longitude, datetime.utcnow()) * 3600
