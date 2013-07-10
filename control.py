import RPi.GPIO as GPIO
import time
usleep = lambda x: time.sleep(x / 1000000.0)


class Motor:
    """ Constants for the 2 motors """
    mirror = 1
    body = 0


class Direction:
    """ Directions for the steppers """
    acw = 0
    cw = 1


class MicroStepperPins:
    """
    Wrapper around pin numbers for the MicroSteppers
    Prevents accidentally changing values
    """
    def __init__(self, clock_pin, direction_pin, sync_pin, home_pin=None):
        self._clock_pin = clock_pin
        self._direction_pin = direction_pin
        self._sync_pin = sync_pin
        self._home_pin = home_pin

    @property
    def clock_pin(self):
        return self._clock

    @property
    def direction_pin(self):
        return self._direction_pin

    @property
    def sync_pin(self):
        return self._sync_pin

    @property
    def home_pin(self):
        if self._home_pin is None:
            raise NotImplementedError
        else:
            return self._home_pin


class MicroStepper:
    def __init__(self, motor):
        self._motor = motor

    def step_motor(self, motor, direction, steps=1):
        assert(steps > 0 and steps < 20000)
        assert(direction == Direction.acw or direction == Direction.cw)
        m = self._motor

        GPIO.output(m.sync_pin, False)
        GPIO.output(m.direction_pin, direction == 1)
        while steps > 0:
            GPIO.output(m.clock_pin, True)
            usleep(50)
            GPIO.output(m.clock_pin, False)
            usleep(50)
            steps -= 1

        GPIO.output(m.sync_pin, True)
