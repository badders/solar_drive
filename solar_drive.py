import serial
import time
import sys
import logging

from PyQt4 import QtGui, QtCore, uic


class SerialApp(QtGui.QApplication):
    def __init__(self):
        super(SerialApp, self).__init__([])
        self.ui = uic.loadUi('solar_drive.ui')
        self.ser = serial.Serial('/dev/tty.usbserial-A600f6JS', 9600)
        time.sleep(2)

        self.ui.mirrorLeft.pressed.connect(self.mirrorAC)
        self.ui.mirrorRight.pressed.connect(self.mirrorCW)
        self.ui.bodyLeft.pressed.connect(self.bodyAC)
        self.ui.bodyRight.pressed.connect(self.bodyCW)
        self.ui.resetButton.pressed.connect(self.reset)

        self.timer = QtCore.QTimer()

        self.timer.timeout.connect(self.readPort)
        self.timer.start(50)

        self.ui.show()
        self.commands_running = 0

    def __del__(self):
        self.ser.close()

    def readPort(self):
        while self.ser.inWaiting():
            line = self.ser.readline().strip()
            logging.debug('Received:\t{}'.format(line))
            self.commands_running -= 1
            self.ui.textBrowser.append(line)

    def steps(self):
        return self.ui.steps.value()

    def mirrorCW(self):
        self.sendCommand('M', 'C', self.steps())

    def mirrorAC(self):
        self.sendCommand('M', 'A', self.steps())

    def bodyCW(self):
        self.sendCommand('B', 'C', self.steps())

    def bodyAC(self):
        self.sendCommand('B', 'A', self.steps())

    def reset(self):
        self.ser.write(bytes('R\n'))

    def sendCommand(self, motor, direction, steps):
        if self.commands_running > 0:
            return
        self.commands_running += 1
        cmd = bytes('T{}{} {}'.format(motor, direction, steps))
        self.ser.write(cmd)
        print cmd
        logging.debug('Sent:\t{}'.format(cmd))

if __name__ == '__main__':
    app = SerialApp()
    sys.exit(app.exec_())
