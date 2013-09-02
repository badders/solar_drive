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
    'ip' : '192.168.2.2',
    'port' : 8010
}

MOTOR_STEP_SIZE = 1.8  # degrees per step
MICRO_STEPS = 16  # Number of microsteps per motor step
GEAR_BOX_RATIO = 250
GEAR_RATIO = 6.0
STEP_SIZE = (MOTOR_STEP_SIZE / MICRO_STEPS) / GEAR_BOX_RATIO

ENCS_PER_REV = 10000 * GEAR_RATIO
STEPS_PER_REV = (360. / STEP_SIZE) * GEAR_RATIO

STEPS_PER_ENC = STEPS_PER_REV / ENCS_PER_REV
SEC_PER_STEP = (24 * 60 * 60) / STEPS_PER_REV
ARCSEC_PER_STEP = (360 * 60 * 60) / STEPS_PER_REV

SEC_PER_ENC = SEC_PER_STEP * STEPS_PER_ENC
ARCSEC_PER_ENC = ARCSEC_PER_STEP * STEPS_PER_ENC

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
        turns = min(200., dt * 0.7)
        raw_turns = turns * STEPS_PER_ENC
        raw_turns = int(max(raw_turns, STEPS_PER_ENC / 4))
        completed = _raw_turn(motor, direction, raw_turns)
        dt -= completed
    # Adjust for over turn


def adjust_ra_sec(seconds):
    """
    Adjust the ra in seconds
    """
    turns = seconds / SEC_PER_ENC
    if turns < 0:
        direc = Directions.anti_clockwise
    else:
        direc = Directions.clockwise
    turn(Devices.body, direc, abs(turns))


def adjust_ra(arcsec):
    """
    Adjust the ra by arcseconds
    """
    turns = arcsec / ARCSEC_PER_ENC
    if turns < 0:
        direc = Directions.anti_clockwise
    else:
        direc = Directions.clockwise
    turn(Devices.body, direc, abs(turns))


def adjust_dec(arcsec):
    """
    Adjust the declination by arcsec
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
    logging.info('Seconds per encoder step: {}'.format(SEC_PER_ENC))

if __name__ == '__main__':
    # Test tracking algorithm ideas
    def smooth_track_ra(seconds):
        logging.debug('Tracking RA:')
        start = datetime.now()
        start_enc = current_position(Devices.body)
        time_tracked = 0
        enc_tracked = 0
        logging.debug('Smooth tracking for: {}s'.format(seconds))
        while(time_tracked < seconds):
            now = datetime.now()
            dt = (now - start).total_seconds()

            enc_expected = math.floor(dt / SEC_PER_ENC)
            enc_error = enc_expected - (enc_tracked - start_enc)

            turns = (dt - time_tracked) / SEC_PER_STEP

            if enc_error > 1:
                turns += (STEPS_PER_ENC - 1) * enc_error
            elif enc_error > 0:
                turns += SLIP_FACTOR
            elif enc_error < 0:
                turns = -1

            if turns > 0:
                Telescope().send_command('T{}{}{}'.format(Devices.body, Directions.clockwise, int(turns)))
                enc_tracked = int(Telescope().readline())
                logging.debug('Elapsed: {:6.2f} Turns: {:5.2f} Error: {}'.format(dt, turns, int(enc_error)))

            time_tracked = dt

    def naive_track_ra(seconds):
        start = datetime.now()
        tracked = 0
        while(tracked < seconds):
            now = datetime.now()
            error = (now - start).total_seconds() - tracked
            logging.debug('Elapsed: {:.2}\tTracked: {:.2}\tError: {}'.format((now - start).total_seconds(), tracked, error))
            # now track for a second
            track_time = int(error + SEC_PER_ENC)
            if track_time > 0:
                adjust_ra(track_time)
                tracked = tracked + track_time
            time.sleep(SEC_PER_STEP)

    logging.basicConfig(level=logging.DEBUG)
    log_constants()
    connect()
    reset_zero()
    smooth_track_ra(7200)
    #naive_track_ra(240)
