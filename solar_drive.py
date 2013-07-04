import serial
import time
import sys

from PyQt4 import QtGui, QtCore, uic

MIRROR = 1
BODY = 0

LEFT = 0
RIGHT = 1

class SerialApp(QtGui.QMainWindow):
    def __init__(self):
        super(SerialApp, self).__init__()
        self._ui = uic.loadUi('solar_drive.ui')
        self._ser = serial.Serial('/dev/tty.usbserial-A600f6JS', 9600)
        time.sleep(2)

        self._ui.mirrorLeft.pressed.connect(self.mirrorLeft)
        self._ui.mirrorRight.pressed.connect(self.mirrorRight)
        self._ui.bodyLeft.pressed.connect(self.bodyLeft)
        self._ui.bodyRight.pressed.connect(self.bodyRight)

        self._timer = QtCore.QTimer()

        self._timer.timeout.connect(self._readPort)
        self._timer.start(200)

        self._ui.show()

    def __del__(self):
        self._ser.close()

    def _readPort(self):
        while self._ser.inWaiting():
            line = self._ser.readline().strip()
            self._ui.textBrowser.append(line)

    def _steps(self):
        return self._ui.steps.value()

    def mirrorLeft(self):
        self._sendCommand(MIRROR, LEFT, self._steps())

    def mirrorRight(self):
        self._sendCommand(MIRROR, RIGHT, self._steps())

    def bodyLeft(self):
        self._sendCommand(BODY, LEFT, self._steps())

    def bodyRight(self):
        self._sendCommand(BODY, RIGHT, self._steps())

    def _sendCommand(self, motor, direction, steps):
        cmd = '{} {} {}\n'.format(int(motor), int(direction), int(steps))
        print cmd
        self._ser.write(cmd)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    win = SerialApp()
    sys.exit(app.exec_())

