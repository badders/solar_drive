import serial
import time
import sys

ser = serial.Serial('/dev/tty.usbserial-A600f6JS', 9600)
time.sleep(2)

print ser.readline()

ser.write('1 1 10000\n')

time.sleep(5)
while ser.inWaiting():
	print ser.readline()
