import time
import sys
import logging
import solar
from datetime import datetime, timedelta
from PyQt4 import QtGui, QtCore, uic

logger = logging.getLogger()


class LogCapture(QtCore.QObject):
    message = QtCore.pyqtSignal(str)

    def flush(self):
        pass

    def fileno(self):
        return -1

    def write(self, msg):
        if not self.signalsBlocked():
            self.messageWritten.emit(msg)


class SolarDriverApp(QtGui.QApplication):
    def __init__(self):
        super(SolarDriverApp, self).__init__([])
        ui = uic.loadUi('solar_drive.ui')
        solar.connect()

        cap = LogCapture()
        logger.addHandler(cap)
        cap.message.connect(ui.logViewer.append)
        ui.show()
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(500)

        self.ui = ui

    def update_time(self):
        lt = datetime.now()
        qlt = QtCore.QTime(lt.hour, lt.minute, lt.second)
        self.ui.localTime.setTime(qlt)

        longitude = float(self.ui.longitude.value())
        dt = timedelta(seconds=longitude / 15 * 3600)
        mst = lt + dt
        qmst = QtCore.QTime(mst.hour, mst.minute, mst.second)
        self.ui.solarTime.setTime(qmst)


if __name__ == '__main__':
    app = SolarDriverApp()
    sys.exit(app.exec_())
