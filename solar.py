"""
Library for interfacing with the solar telescope.
"""
import serial
from functools import wraps
import time
import math
from datetime import datetime, timedelta
import logging


class Commands:
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


MOTOR_STEP_SIZE = 1.8  # degrees per step
MICRO_STEPS = 16
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
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Telescope:
    __metaclass__ = _Singleton

    def connected(f):
        @wraps(f)
        def _connected(*args, **kwargs):
            if args[0].ser is not None:
                return f(*args, **kwargs)
            else:
                raise IOError('Not connected to motors. Call Telescope.connect(\'<path to device>\')')
        return _connected

    def __init__(self):
        self.ser = None

    def __del__(self):
        self.disconnect()

    def connect(self, device):
        self.ser = serial.Serial(device, 9600)

    @connected
    def disconnect(self, device):
        self.ser.close()
        self.ser = None

    @connected
    def send_command(self, cmd):
        #logging.debug('Send: {}'.format(cmd))
        self.ser.write(cmd + '\n')

    @connected
    def readline(self):
        data = self.ser.readline().strip()
        #logging.debug('Recv: {}'.format(data))
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


def connect(device='/dev/tty.usbserial-A600f6JS'):
    """
    Connecte to the telscope on <device>
    """
    Telescope().connect(device)
    time.sleep(2)


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


def adjust_ra(seconds):
    """
    Adjust the ra by seconds
    """
    turns = SEC_PER_ENC * seconds
    if turns < 0:
        direc = Directions.anit_clockwise
    else:
        direc = Directions.clockwise
    turn(Devices.mirror, direc, abs(turns))


def turn_dec(arcsec):
    """
    Adjust the declination by arcsec
    """
    turns = ARCSEC_PER_ENC * arcsec
    if turns < 0:
        direc = Directions.clockwise
    else:
        direc = Directions.anti_clockwise
    turn(Devices.body, direc, abs(turns))


def reset_zero():
    """
    Reset the encoder counts to zero
    """
    Telescope().send_command('R')


def smooth_track_ra(seconds, callback=None):
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

        if callback is not None:
            callback()
        #time.sleep(SEC_PER_STEP / 3)


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.debug('Motor steps per 1 encode tick: {}'.format(STEPS_PER_ENC))
    logging.debug('Seconds per motor step: {}'.format(SEC_PER_STEP))
    logging.debug('Arcsec per motor step: {}'.format(ARCSEC_PER_STEP))
    logging.debug('Seconds per encoder step: {}'.format(SEC_PER_ENC))
    logging.debug('Arcsec per encoder step: {}'.format(ARCSEC_PER_ENC))
    logging.debug('Tracking RA:')
    connect()
    reset_zero()
    smooth_track_ra(10)
    #naive_track_ra(240)
