# -*- coding: utf-8 -*-
from datetime import datetime, timedelta


def ra_to_str(seconds):
    """
    Convert a right ascension to a pretty printed string
    seconds -- right ascension in seconds
    Returns string like ±18h26m32s
    """
    ra = int(abs(seconds))
    h, m, s = ra // 3600, (ra // 60) % 60, ra % 60
    if seconds < 0:
        sign = '-'
    else:
        sign = '+'
    return '{}{:02d}h{:02d}m{:02d}s'.format(sign, h, m, s)


def dec_to_str(arcsec):
    """
    Convert a declination to a pretty printed string
    arcsec -- declination in arcseconds
    Returns string like ±72d26m32s
    """
    dec = int(abs(arcsec))
    d, m, s = dec // 3600, (dec // 60) % 60, dec % 60
    if arcsec < 0:
        sign = '-'
    else:
        sign = '+'
    return '{}{:02d}d{:02d}m{:02d}s'.format(sign, d, m, s)


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


def sun_ra(longitude):
    """
    Calculate the RA of the sun
    longitude -- Current longitude
    Returns the Sun's RA in seconds
    """
    mst = mean_solar_time(longitude)
    return timedelta(hours=mst.hour - 12, minutes=mst.minute, seconds=mst.second).total_seconds()


def sun_dec(latitude):
    """
    Calculate the declination of the Sun
    longitude -- Current longitude
    Returns the Sun's declination in seconds
    """
    return (90. - latitude) * 3600
