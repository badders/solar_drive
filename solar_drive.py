import math
import sys
import logging
import solar
import os
from datetime import datetime, timedelta
from PyQt4 import QtGui, QtCore, uic


def get_ui_file(name):
    """
    Helper function to automatically correct path for files in ui/
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui', name)


class QStreamIntercept(QtCore.QObject):
    """
    Wrapper to capture log messages
    """
    msg = QtCore.pyqtSignal(str)

    def flush(self):
        pass

    def write(self, text):
        self.msg.emit(text)


class SolarDriverApp(QtGui.QApplication):
    def __init__(self):
        super(SolarDriverApp, self).__init__([])
        ui = uic.loadUi(get_ui_file('solar_drive.ui'))
        self.ui = ui

        stream = QStreamIntercept()

        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler(stream))
        stream.msg.connect(self.log)

        solar.connect()
        solar.log_constants()

        ui.show()
        ui.raise_()

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

        self.tracking = False

        self.aboutToQuit.connect(self.terminating)
        self.load_config()

    def terminating(self):
        self.tracking = False
        sys.stdout = sys.__stdout__
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

    def find_sun(self):
        dec = solar.sun_dec(self.ui.latitude.value())
        ra = solar.sun_ra(self.ui.longitude.value())

        logging.info('Sun at: {} {}'.format(solar.ra_to_str(ra), solar.dec_to_str(dec)))

        solar.adjust_dec(dec - self._dec)
        self._dec = dec

        while abs(ra - self._ra) > 2 * solar.ARCSEC_PER_ENC:
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

    def sun_ra(self):
        return solar.sun_ra(self.ui.longitude.value())

    def sun_dec(self):
        return solar.sun_dec(self.ui.latitude.value())

    def return_to_zero(self):
        logging.info('Returning to zero')
        solar.adjust_ra_sec(-self._ra)
        solar.adjust_dec(-self._dec)
        self._dec = 0
        self._ra = 0

    def set_zero(self):
        logging.info('Setting as zero')
        solar.reset_zero()
        self._ra = 0
        self._dec = 0

    def log(self, msg):
        self.ui.logViewer.append(str(msg).strip())

    def update_time(self):
        lt = datetime.now()
        qlt = QtCore.QTime(lt.hour, lt.minute, lt.second)
        self.ui.localTime.setTime(qlt)

        utc = datetime.utcnow()
        qutc = QtCore.QTime(utc.hour, utc.minute, utc.second)
        self.ui.utcTime.setTime(qutc)

        mst = solar.mean_solar_time(self.ui.longitude.value())
        qmst = QtCore.QTime(mst.hour, mst.minute, mst.second)
        self.ui.solarTime.setTime(qmst)

        self.ui.raDisplay.setText(solar.ra_to_str(self._ra))
        self.ui.decDisplay.setText(solar.dec_to_str(self._dec))

if __name__ == '__main__':
    app = SolarDriverApp()
    sys.exit(app.exec_())
