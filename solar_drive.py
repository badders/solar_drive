# -*- coding: utf-8 -*-
"""
GUI Application for controlling the solar telescope
"""
import logging
import solar
import os
import sys
from datetime import datetime
from PyQt4 import QtGui, QtCore, uic


def get_ui_file(name):
    """
    Helper function to automatically correct path for files in ui/
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui', name)


class SolarDriverApp(QtGui.QApplication):
    """
    The actual application. Handles loading the interface and connecting together
    the interface elements to their respective functions
    """
    def __init__(self):
        super(SolarDriverApp, self).__init__([])
        ui = uic.loadUi(get_ui_file('solar_drive.ui'))
        self.ui = ui

        logging.getLogger().setLevel(logging.INFO)

        self.telescope = solar.TelescopeManager()
        self.telescope.start()

        self.ui.latitude.valueChanged.connect(self.set_latitude)
        self.ui.longitude.valueChanged.connect(self.set_longitude)
        self.ui.azAdjust.valueChanged.connect(self.tune)
        self.ui.altAdjust.valueChanged.connect(self.tune)

        ui.show()
        ui.raise_()

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(200)

        ui.trackButton.clicked.connect(self.track)
        ui.findSun.clicked.connect(self.find_sun)
        ui.zeroReturn.clicked.connect(self.return_to_zero)

        ui.azLeft.clicked.connect(self.azLeft)
        ui.azRight.clicked.connect(self.azRight)
        ui.altLeft.clicked.connect(self.altLeft)
        ui.altRight.clicked.connect(self.altRight)
        ui.setZero.clicked.connect(self.telescope.set_zero)
        ui.setSun.clicked.connect(self.telescope.set_sun)

        ui.setZero.hide()
        
        self.aboutToQuit.connect(self.terminating)
        self.load_config()

    def terminating(self):
        """
        Called just before the application quits
        """
        self.telescope.join()
        self.save_config()

    def load_config(self):
        """
        Load the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        self.telescope.az = settings.value('az', 0).toPyObject()
        self.telescope.alt = settings.value('alt', 0).toPyObject()
        self.telescope.latitude = settings.value('lat', self.ui.latitude.value()).toPyObject()
        self.telescope.longitude = settings.value('long', self.ui.longitude.value()).toPyObject()
        settings.endGroup()

    def save_config(self):
        """
        Save the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        settings.setValue('az', self.telescope.az)
        settings.setValue('alt', self.telescope.alt)
        settings.setValue('lat', self.telescope.latitude)
        settings.setValue('lat', self.telescope.longitude)

    def set_latitude(self, value):
        self.telescope.latitude = value

    def set_longitude(self, value):
        self.telescope.longitude = value

    def azLeft(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_az(-arc)

    def azRight(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_az(arc)

    def altLeft(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_alt(-arc)

    def altRight(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_alt(arc)

    def track(self):
        if self.telescope.tracking:
            logging.info('Tracking Cancelled')
            self.telescope.stop_tracking()
            self.ui.calibrationTab.setEnabled(True)
            return
        logging.info('Tracking Sun Commencing')
        self.ui.calibrationTab.setEnabled(False)
        self.find_sun()
        self.telescope.start_tracking()

    def find_sun(self):
        self.telescope.slew_to_sun()

    def return_to_zero(self):
        self.telescope.return_to_zero()

    def tune(self):
        t_az = self.ui.azAdjust.value()
        t_alt = self.ui.altAdjust.value()
        self.telescope.tune([t_az, t_alt])

    def update_time(self):
        """
        Called repeatedly to check for any updates and to update the time
        and position displays
        """
        self.telescope.flush_messages()

        lt = datetime.now()
        qlt = QtCore.QTime(lt.hour, lt.minute, lt.second)
        self.ui.localTime.setTime(qlt)

        utc = datetime.utcnow()
        qutc = QtCore.QTime(utc.hour, utc.minute, utc.second)
        self.ui.utcTime.setTime(qutc)

        mst = solar.mean_solar_time(self.ui.longitude.value())
        qmst = QtCore.QTime(mst.hour, mst.minute, mst.second)
        self.ui.solarTime.setTime(qmst)

        self.ui.azDisplay.setText(solar.az_to_str(self.telescope.az))
        self.ui.altDisplay.setText(solar.alt_to_str(self.telescope.alt))

if __name__ == '__main__':
    app = SolarDriverApp()
    sys.exit(app.exec_())
