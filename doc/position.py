# -*- coding: utf-8 -*-
from pylab import *
import Pysolar as pysol
from datetime import datetime, timedelta

start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
lat = 51.4841
lng = -3.1701
x = linspace(8 * 3600, 8 * 3600 + 12 * 60 * 60, num=200)
alt = array([pysol.GetAltitude(lat, lng, start + timedelta(seconds=s)) for s in x])
az = array([pysol.GetAzimuth(lat, lng, start + timedelta(seconds=s)) for s in x])
az = (az - 180) % -360 + 360
m, b = polyfit(x, az, 1)
az_fit = m * x + b

x = x / 3600
plot(x, az_fit - az_fit.mean(), '--', label='Linear Az')
plot(x, az - az.mean(), label='Azimuth')
plot(x, alt - alt.mean(), label='Altitude')
legend(loc='best')
xlim(8, 20)
ylim(-110, 110)
ylabel('Relative Movement')
xlabel('Time of day (h)')
title('Solar Position')
show()
