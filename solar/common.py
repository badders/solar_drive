from datetime import datetime, timedelta


def ra_to_str(seconds):
    ra = int(abs(seconds))
    h, m, s = ra // 3600, (ra // 60) % 60, ra % 60
    if seconds < 0:
        sign = '-'
    else:
        sign = '+'
    return '{}{:02d}h{:02d}m{:02d}s'.format(sign, h, m, s)


def dec_to_str(arcsec):
    dec = int(abs(arcsec))
    d, m, s = dec // 3600, (dec // 60) % 60, dec % 60
    if arcsec < 0:
        sign = '-'
    else:
        sign = '+'
    return '{}{:02d}d{:02d}m{:02d}s'.format(sign, d, m, s)


def mean_solar_time(longitude):
    lt = datetime.utcnow()
    dt = timedelta(seconds=longitude / 15 * 3600)
    mst = lt + dt
    return mst


def sun_ra(longitude):
    mst = mean_solar_time(longitude)
    return timedelta(hours=mst.hour - 12, minutes=mst.minute, seconds=mst.second).total_seconds()


def sun_dec(latitude):
    return (90. - latitude) * 3600
