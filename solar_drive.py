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
        self._ra -= arc

    def raRight(self):
        arc = self.ui.calArcSec.value()
        solar.adjust_ra(arc)
        self._ra += arc

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
        #self.find_sun()
        self.start_tracking()

    def find_sun(self):
        dec = (90. - self.ui.latitude.value()) * 3600
        mst = self.mst()
        ra = timedelta(hours=mst.hour - 12, minutes=mst.minute, seconds=mst.second).total_seconds()

        logging.info('Sun at: {} seconds {} arcsec'.format(ra, dec))
        solar.adjust_dec(dec - self._dec)
        solar.adjust_ra_sec(ra - self._ra)
        self._dec = dec
        self._ra = ra

    def start_tracking(self):
        # Track Loop
        start = datetime.utcnow()
        start_enc = solar.current_position(solar.Devices.body)
        start_ra = self._ra
        while self.tracking:
            time_tracked = 0
            enc_tracked = 0

            # Track in 3 second bursts to allow for cancelling
            while(time_tracked < 3.0):
                now = datetime.utcnow()
                dt = (now - start).total_seconds()

                enc_expected = math.floor(dt / solar.SEC_PER_ENC)
                enc_error = enc_expected - (enc_tracked - start_enc)

                turns = (dt - time_tracked) / solar.SEC_PER_STEP

                if enc_error > 1:
                    turns += (solar.STEPS_PER_ENC - 1) * enc_error
                elif enc_error > 0:
                    turns += solar.SLIP_FACTOR
                elif enc_error < 0:
                    turns = -1

                if turns > 0:
                    solar.Telescope().send_command('T{}{}{}'.format(solar.Devices.body, solar.Directions.clockwise, int(turns)))
                    enc_tracked = int(solar.Telescope().readline())
                    logging.debug('Elapsed: {:6.2f} Turns: {:5.2f} Error: {}'.format(dt, turns, int(enc_error)))

                time_tracked = dt
                self._ra = start_ra + enc_tracked * solar.SEC_PER_ENC
                QtGui.QApplication.processEvents()

            start = start + timedelta(seconds=time_tracked)

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
