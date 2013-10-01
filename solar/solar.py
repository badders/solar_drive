# -*- coding: utf-8 -*-
"""
Library for interfacing with the arduino controlling the solar telescope
"""
import socket
from functools import wraps
import time
import math
from datetime import datetime
import logging


class Commands:
    """
    Command codes for the arduino program
    """
    reset = 'R'
    turn = 'T'


class Devices:
    """
    Motors available
    """
    body = 'B'
    mirror = 'M'


class Directions:
    clockwise = 'C'
    anti_clockwise = 'A'

arduino = {
    'ip': '192.168.2.2',
    'port': 8010
}

MOTOR_STEP_SIZE = 1.8  # degrees per step
MICRO_STEPS = 16  # Number of microsteps per motor step
GEAR_BOX_RATIO = 250
GEAR_RATIO = 6.0
STEP_SIZE = (MOTOR_STEP_SIZE / MICRO_STEPS) / GEAR_BOX_RATIO

ENCS_PER_REV = 10000 * GEAR_RATIO
STEPS_PER_REV = (360. / STEP_SIZE) * GEAR_RATIO

STEPS_PER_ENC = STEPS_PER_REV / ENCS_PER_REV
ARCSEC_PER_STEP = (360 * 60 * 60) / STEPS_PER_REV
ARCSEC_PER_ENC = ARCSEC_PER_STEP * STEPS_PER_ENC
SEC_PER_STEP = (24 * 60 * 60) / STEPS_PER_REV
SEC_PER_ENC = SEC_PER_STEP * STEPS_PER_ENC

SLIP_FACTOR = STEPS_PER_ENC / 10


class _Singleton(type):
    """
    Class to force another class to be a singleton
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Telescope:
    """
    Class to communicate with the arduino directly
    """
    __metaclass__ = _Singleton

    def connected(f):
        @wraps(f)
        def _connected(*args, **kwargs):
            if args[0].client_socket is not None:
                return f(*args, **kwargs)
            else:
                raise IOError('Not connected to motors. Call Telescope.connect(\'<path to device>\')')
        return _connected

    def __init__(self):
        self.client_socket = None

    def __del__(self):
        self.disconnect()

    def connect(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((arduino['ip'], arduino['port']))
        self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

    @connected
    def disconnect(self, device):
        self.client_socket.close()
        self.client_socket = None

    @connected
    def send_command(self, cmd):
        logging.debug('Send: {}'.format(cmd))
        self.client_socket.send(cmd + '\n')

    @connected
    def readline(self):
        data = ' '
        while data[-1] != '\n':
            data += self.client_socket.recv(1)
        data = data.strip()
        logging.debug('Recv: {}'.format(data))
        return data


def motor_check(f):
    @wraps(f)
    def wrapper(motor, *args):
        assert(motor == Devices.body or motor == Devices.mirror)
        return f(motor, *args)
    return wrapper


def direction_check(f):
    @wraps(f)
    def wrapper(motor, direction, *args):
        assert(direction == Directions.clockwise or direction == Directions.anti_clockwise)
        return f(motor, direction, *args)
    return wrapper


def connect():
    """
    Connect to the telscope
    """
    Telescope().connect()


@motor_check
@direction_check
def _raw_turn(motor, direction, turns):
    """
    Turn the motors, without regard for the encoder return values
    Returns the number of encoded turns
    """
    current = current_position(motor)

    Telescope().send_command('T{}{}{}'.format(motor, direction, int(turns)))
    count = int(Telescope().readline())

    return abs(count - current)


@motor_check
def current_position(motor):
    """
    Return the current encoder count for the motor
    """
    Telescope().send_command('E{}'.format(motor))
    return int(Telescope().readline())


@motor_check
@direction_check
def turn(motor, direction, enc_turns):
    """
    Turn a motor until the encoder reports back enough turns.
    """
    dt = enc_turns
    while dt > 0:
        turns = min(2000., dt * 0.7)
        raw_turns = turns * STEPS_PER_ENC
        raw_turns = int(max(raw_turns, STEPS_PER_ENC / 4))
        completed = _raw_turn(motor, direction, raw_turns)
        dt -= completed


def adjust_az(arcsec):
    """
    Move the telescope by arcsec in azimuth
    n.b. Not implemented, just rotates the polar axis
    """
    adjust_polar(arcsec)


def adjust_alt(arcsec):
    """
    Move the telescope by arcsec in altitude
    n.b. Not implemented, just rotates the declination axis
    """
    adjust_dec(arcsec)


def adjust_polar(arcsec):
    """
    Roate the polar axis by arcseconds
    """
    turns = arcsec / ARCSEC_PER_ENC
    if turns < 0:
        direc = Directions.anti_clockwise
    else:
        direc = Directions.clockwise
    turn(Devices.body, direc, abs(turns))


def adjust_dec(arcsec):
    """
    Rotate the declination axis by arcsec
    """
    turns = arcsec / ARCSEC_PER_ENC
    if turns < 0:
        direc = Directions.anti_clockwise
    else:
        direc = Directions.clockwise
    turn(Devices.mirror, direc, abs(turns))


def reset_zero():
    """
    Reset the encoder counts to zero
    """
    Telescope().send_command('R')


def log_constants():
    logging.info('Motor steps per encode tick: {}'.format(STEPS_PER_ENC))
    logging.info('Arcsec per motor step: {}'.format(ARCSEC_PER_STEP))
    logging.info('Arcsec per encoder step: {}'.format(ARCSEC_PER_ENC))
