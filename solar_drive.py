import sys
import logging
import solar
import os
from datetime import datetime
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

        self.telescope = solar.TelescopeManager()
        self.telescope.start()

        self.telescope.latitude = self.ui.latitude.value()
        self.telescope.longitude = self.ui.longitude.value()

        #self.ui.latitude.valueChanged.connect(self.telescope.latitude.fset)
        #self.ui.longitude.valueChanged.connect(self.telescope.longitude.fset)

        ui.show()
        ui.raise_()

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(200)

        ui.trackButton.clicked.connect(self.track)
        ui.findSun.clicked.connect(self.find_sun)
        ui.zeroReturn.clicked.connect(self.telescope.return_to_zero)

        ui.raLeft.clicked.connect(self.raLeft)
        ui.raRight.clicked.connect(self.raRight)
        ui.decLeft.clicked.connect(self.decLeft)
        ui.decRight.clicked.connect(self.decRight)
        ui.setZero.clicked.connect(self.telescope.set_zero)

        self.aboutToQuit.connect(self.terminating)
        self.load_config()

    def terminating(self):
        self.telescope.join()
        sys.stdout = sys.__stdout__
        self.save_config()

    def load_config(self):
        """
        Load the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        self.telescope.ra = settings.value('ra', 0).toPyObject()
        self.telescope.dec = settings.value('dec', 0).toPyObject()
        settings.endGroup()

    def save_config(self):
        """
        Save the configuration
        """
        settings = QtCore.QSettings('Solar Control', 'solar_drive')
        settings.beginGroup('Position')
        settings.setValue('ra', self.telescope.ra)
        settings.setValue('dec', self.telescope.dec)

    def raLeft(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_ra(-arc)

    def raRight(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_ra(arc)

    def decLeft(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_dec(-arc)

    def decRight(self):
        arc = self.ui.calArcSec.value()
        self.telescope.slew_dec(arc)

    def track(self):
        if self.telescope.tracking:
            logging.info('Tracking Cancelled')
            self.telescope.stop_tracking()
            return
        logging.info('Tracking Sun Commencing')
        self.find_sun()
        self.telescope.start_tracking()

    def find_sun(self):
        self.telescope.slew_to_sun()

    def log(self, msg):
        self.ui.logViewer.append(str(msg).strip())

    def update_time(self):
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

        self.ui.raDisplay.setText(solar.ra_to_str(self.telescope.ra))
        self.ui.decDisplay.setText(solar.dec_to_str(self.telescope.dec))

if __name__ == '__main__':
    app = SolarDriverApp()
    sys.exit(app.exec_())
