import math
import sys
import logging
import solar
from datetime import datetime, timedelta
from PyQt4 import QtGui, QtCore, uic
from functools import wraps


class SolarDriverApp(QtGui.QApplication):
    def __init__(self):
        super(SolarDriverApp, self).__init__([])
        ui = uic.loadUi('solar_drive.ui')
        logging.basicConfig(level=logging.DEBUG)

        solar.connect()
        solar.log_constants()

        ui.show()
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(300)

        ui.trackButton.pressed.connect(self.track)
        ui.findSun.pressed.connect(self.find_sun)
        ui.zeroReturn.pressed.connect(self.return_to_zero)

        ui.raLeft.pressed.connect(self.raLeft)
        ui.raRight.pressed.connect(self.raRight)
        ui.decLeft.pressed.connect(self.decLeft)
        ui.decRight.pressed.connect(self.decRight)

        ui.setZero.pressed.connect(self.set_zero)

        self.ui = ui
        self.tracking = False

        self.aboutToQuit.connect(self.terminating)
        self.load_config()

    def terminating(self):
        self.tracking = False
        self.save_config()

    def load_config(self):
        """
        Load the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        self._ra = settings.value('ra', 0).toPyObject()
        self._dec = settings.value('dec', 0).toPyObject()
        settings.endGroup()

    def save_config(self):
        """
        Save the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        settings.setValue('ra', self._ra)
        settings.setValue('dec', self._dec)

    def raLeft(self):
        arc = self.ui.calArcSec.value()
        solar.adjust_ra(-arc)
        self._ra -= arc * 15

    def raRight(self):
        arc = self.ui.calArcSec.value()
        solar.adjust_ra(arc)
        self._ra += arc * 15

    def decLeft(self):
        arc = self.ui.calArcSec.value()
        solar.adjust_dec(-arc)
        self._dec -= arc

    def decRight(self):
        arc = self.ui.calArcSec.value()
        solar.adjust_dec(arc)
        self._dec += arc

    def track(self):
        if self.tracking:
            logging.info('Tracking Cancelled')
            self.tracking = False
            return
        logging.info('Tracking Sun Commencing')
        self.tracking = True
        self.find_sun()
        self.start_tracking()

    def sun_ra(self):
        mst = self.mst()
        return timedelta(hours=mst.hour - 12, minutes=mst.minute, seconds=mst.second).total_seconds()

    def sun_dec(self):
        return (90. - self.ui.latitude.value()) * 3600

    def find_sun(self):
        dec = self.sun_dec()
        ra = self.sun_ra()

        logging.info('Sun at: {} seconds {} arcsec'.format(ra, dec))

        solar.adjust_dec(dec - self._dec)
        self._dec = dec

        while abs(ra - self._ra) > 5:
            solar.adjust_ra_sec(ra - self._ra)
            self._ra = ra
            ra = self.sun_ra()

    def start_tracking(self):
        # Get sun position
        # Add any calibraion
        # If far slew to location, otherwise smooth track
        while self.tracking:
            # Compensate for any fine tuning of declination
            dec = self._dec
            target = self.sun_dec() + self.ui.decAdjust.value()
            if abs(target - dec) > solar.ARCSEC_PER_ENC:
                solar.adjust_dec(target - dec)
                self._dec = target
                logging.debug('Compensating declination adjustment')

            # Now track along RA
            ra = self._ra
            target = self.sun_ra() + self.ui.raAdjust.value()

            # If the gap has become large, slew
            if abs(target - ra) > solar.SEC_PER_ENC:
                solar.adjust_ra_sec(target - ra)
                self._ra = target
                logging.debug('Compensating for RA adjustment')

            # Otherwise smoothly track for at least 3 seconds
            time_tracked = 0
            start = datetime.utcnow()
            enc_tracked = 0
            enc_start = solar.current_position(solar.Devices.body)
            while(time_tracked < 3):
                now = datetime.utcnow()
                dt = (now - start).total_seconds()
                enc_expected = math.floor(dt / solar.SEC_PER_ENC)
                enc_error = enc_expected - enc_tracked
                turns = (dt - time_tracked) // solar.SEC_PER_STEP

                if enc_error > 0:
                    turns += solar.SLIP_FACTOR
                elif enc_error < 0:
                    turns = 0

                if turns > 0:
                    solar.Telescope().send_command('T{}{}{}'.format(solar.Devices.body, solar.Directions.clockwise, int(turns)))
                    enc_tracked += int(solar.Telescope().readline()) - enc_start
                    time_tracked = dt
                    logging.debug('Micro Steps: {:5.2f} Encoder Error: {}'.format(turns, int(enc_error)))
                    self._ra = ra + enc_tracked * solar.SEC_PER_ENC

                if self.tracking:
                    QtGui.QApplication.processEvents()

    def return_to_zero(self):
        logging.info('Returning to zero')
        solar.adjust_dec(-self._dec)
        solar.adjust_ra_sec(-self._ra)
        self._dec = 0
        self._ra = 0

    def set_zero(self):
        logging.info('Setting as zero')
        solar.reset_zero()
        self._ra = 0
        self._dec = 0

    def mst(self):
        lt = datetime.utcnow()
        longitude = float(self.ui.longitude.value())
        dt = timedelta(seconds=longitude / 15 * 3600)
        mst = lt + dt
        return mst

    def update_time(self):
        lt = datetime.now()
        qlt = QtCore.QTime(lt.hour, lt.minute, lt.second)
        self.ui.localTime.setTime(qlt)

        utc = datetime.utcnow()
        qutc = QtCore.QTime(utc.hour, utc.minute, utc.second)
        self.ui.utcTime.setTime(qutc)

        mst = self.mst()
        qmst = QtCore.QTime(mst.hour, mst.minute, mst.second)
        self.ui.solarTime.setTime(qmst)

        ra = int(self._ra)
        dec = int(self._dec)
        sra = '{:+02d}h{:02d}m{:02d}s'.format(ra // 3600, (ra // 60) % 60, ra % 60)
        sdec = '{:+02d}d{:02d}m{:02d}s'.format(dec // 3600, (dec // 60) % 60, dec % 60)

        self.ui.raDisplay.setText(sra)
        self.ui.decDisplay.setText(sdec)

if __name__ == '__main__':
    app = SolarDriverApp()
    sys.exit(app.exec_())
