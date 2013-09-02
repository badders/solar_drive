import socket
import time
import sys
import logging

from PyQt4 import QtGui, QtCore, uic

arduino = {
    'ip' : '192.168.2.2',
    'port' : 8010
}

class SerialApp(QtGui.QApplication):
    def __init__(self):
        super(SerialApp, self).__init__([])
        self.ui = uic.loadUi('solar_drive.ui')
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((arduino['ip'], arduino['port']))
        self.client_socket.setblocking(0)

        self.ui.mirrorLeft.pressed.connect(self.mirrorAC)
        self.ui.mirrorRight.pressed.connect(self.mirrorCW)
        self.ui.bodyLeft.pressed.connect(self.bodyAC)
        self.ui.bodyRight.pressed.connect(self.bodyCW)
        self.ui.resetButton.pressed.connect(self.reset)

        self.timer = QtCore.QTimer()

        self.timer.timeout.connect(self.readPort)
        self.timer.start(300)

        self.ui.show()
        self.ui.raise_()
        self.commands_running = 0

    def __del__(self):
        self.client_socket.close()

    def readPort(self):
        try:
            data = self.client_socket.recv(1024).strip()
        except socket.error:
            return
        logging.debug('Received:\t{}'.format(data))
        self.commands_running -= 1
        self.ui.textBrowser.append(data)

    def steps(self):
        return self.ui.steps.value()

    def mirrorCW(self):
        self.commands_running += 1
        self.sendCommand('M', 'C', self.steps())

    def mirrorAC(self):
        self.commands_running += 1
        self.sendCommand('M', 'A', self.steps())

    def bodyCW(self):
        self.commands_running += 1
        self.sendCommand('B', 'C', self.steps())

    def bodyAC(self):
        self.commands_running += 1
        self.sendCommand('B', 'A', self.steps())

    def reset(self):
        self.client_socket.write(bytes('R\n'))

    def sendCommand(self, motor, direction, steps):
        cmd = bytes('T{}{}{}\n'.format(motor, direction, steps))
        self.client_socket.send(cmd)
        logging.debug('Sent:\t{}'.format(cmd))

if __name__ == '__main__':
    app = SerialApp()
    sys.exit(app.exec_())
