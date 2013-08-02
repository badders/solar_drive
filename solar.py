"""
Library for interfacing with the solar telescope.
"""
import serial
from functools import wraps


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


class _Constants:
    STEPS_PER_ENC = 400
    MAX_SINGLE_TURN = 100


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
        if self.ser is not None:
            self.ser.close()

    def connect(self, device):
        self.ser = serial.Serial(device, 9600)

    @connected
    def disconnect(self, device):
        if self.ser is not None:
            ser.close()
            self.ser = None

    @connected
    def send_command(self, cmd):
        self.ser.write(cmd + '\n')

    @connected
    def readline(self):
        return self.ser.readline()


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
    reset_zero()


@motor_check
@direction_check
def _raw_turn(motor, direction, turns):
    """
    Turn the motors, without regard for the encoder return values
    Returns the number of encoded turns
    """
    current = current_position(motor)

    Telescope().send_command('T{}{} {}'.format(motor, direction, turns))
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
        turns = min(1000, dt)
        raw_turns = turns * _Constants.STEPS_PER_ENC
        completed = _raw_turn(motor, direction, raw_turns)
        print completed
        dt -= completed


def reset_zero():
    """
    Reset the encoder counts to zero
    """
    Telescope().send_command('R')
