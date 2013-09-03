# -*- coding: utf-8 -*-
"""
Library for interacting with the telescope in an asynchronous manner
"""
from multiprocessing import Process, Pipe
from datetime import datetime
import math
import solar
import logging
from functools import wraps
from common import *


class Commands:
    """
    Command codes for passing instructions to the thread running the telescope
    """
    SET_RA, SET_DEC, SET_LAT, SET_LONG, \
        TRACK, CANCEL_TRACK, \
        TERMINATE, FINE_TUNE, \
        SLEW_RA, SLEW_DEC, SLEW_TO_SUN, SET_ZERO, SET_SUN = range(13)


class Responses:
    """
    Repsonse codes for recieving data from the telescope thread
    """
    SET_RA, SET_DEC, SLEW_FINISHED = range(3)


def track_action(conn, latitude, longitude, ra, dec, tune):
    """
    Actually peform the telescope tracking

    conn -- The pipe connection to communicate position changes
    latitude -- Current latitude
    longitude -- Current longiture
    ra -- Current right ascension of telescope
    dec -- Current declination of telescope
    tune -- [RA, Dec] manual fine tuning adjustment

    Algorithm:
    1. Check RA/Dec are where we expect, if not slew
    2. Start smoothly tracking for appoximately 7 seconds as follow:
        - Check if the encoders say we have dropped behind or gone too far and compensate
        - Work out how much we should have turned in the time passed
        - Turn the motors for this amount
    """
    target = sun_ra(longitude) + tune[0]
    target_dec = sun_dec(latitude) + tune[1]

    # Adjust declination in case of fine tuning
    if abs(target_dec - dec) > solar.ARCSEC_PER_ENC:
        solar.adjust_dec(target_dec - dec)
        conn.send([Responses.SET_DEC, target_dec])

    # If RA is off by more than an encode step (1.44 seconds) then slew
    if abs(target - ra) > solar.SEC_PER_ENC:
        solar.adjust_ra_sec(target - ra)
        logging.debug('Compensating for RA adjustment by {}s'.format(target - ra))
        ra = target
        conn.send([Responses.SET_RA, ra])

    # Otherwise smoothly track for about 7 seconds
    time_tracked = 0
    start = datetime.utcnow()
    enc_tracked = 0
    enc_start = solar.current_position(solar.Devices.body)
    start_ra = ra

    while(time_tracked < 10):
        now = datetime.utcnow()
        dt = (now - start).total_seconds()
        enc_expected = math.floor(dt / solar.SEC_PER_ENC)
        enc_error = enc_expected - enc_tracked
        turns = (dt - time_tracked) // solar.SEC_PER_STEP

        # Check encoders report the position we expect, otherwise compensat
        if enc_error > 1:
            # Large slip, so attempt to catch up
            turns += (enc_error - 1) * solar.STEPS_PER_ENC
        if enc_error > 0:
            # Small error, could be as little as one microstep so add small slip factor to catch up
            turns += solar.SLIP_FACTOR
        elif enc_error < 0:
            # Overstepped, just dont turn for this cycle
            turns = 0

        if turns > 0:
            solar.Telescope().send_command('T{}{}{}'.format(solar.Devices.body, solar.Directions.clockwise, int(turns)))
            enc_tracked = int(solar.Telescope().readline()) - enc_start
            time_tracked = dt
            logging.debug('Micro Steps: {:5.2f} Encoder Error: {}'.format(turns, int(enc_error)))
            ra = start_ra + enc_tracked * solar.SEC_PER_ENC
            conn.send([Responses.SET_RA, ra])

    return ra, dec


def slew_to_sun(conn, latitude, longitude, ra, dec):
    """
    Perform a slew to the suns location

    conn -- The pipe connection to communicate position changes
    latitude -- Current latitude
    longitude -- Current longiture
    ra -- Current right ascension of telescope
    dec -- Current declination of telescope
    """
    sdec = sun_dec(latitude)
    sra = sun_ra(longitude)

    logging.info('Sun at: {} {}'.format(ra_to_str(sra), dec_to_str(sdec)))

    solar.adjust_dec(sdec - dec)
    conn.send([Responses.SET_DEC, sdec])

    """
    As slewing can take a long time, might need to slew some more to catch
    up with the Sun
    """
    while abs(sra - ra) > 2 * solar.SEC_PER_ENC:
        solar.adjust_ra_sec(sra - ra)
        ra = sra
        conn.send([Responses.SET_RA, ra])
        sra = sun_ra(longitude)

    conn.send([Responses.SLEW_FINISHED])
    return ra, sdec


def slew_ra(conn, ra, arcsec):
    """
    Slew the right ascension of the telescope

    conn -- The pipe connection to communicate position changes
    ra -- Current right ascension of telescope
    arcsec -- Arc seconds to slew by
    """
    solar.adjust_ra(arcsec)
    ra += arcsec / 15
    conn.send([Responses.SET_RA, ra])
    conn.send([Responses.SLEW_FINISHED])
    return ra


def slew_dec(conn, dec, arcsec):
    """
    Slew the declination of the telescope

    conn -- The pipe connection to communicate position changes
    dec -- Current declination of telescope
    arcsec -- Arc seconds to slew by
    """
    solar.adjust_dec(arcsec)
    dec += arcsec
    conn.send([Responses.SET_DEC, dec])
    conn.send([Responses.SLEW_FINISHED])
    return dec


def thread_process(conn):
    """
    This is the program that runs on the seperate thread to communicate with the telsescope

    Alogrigthm:

    1. Connect to telescope
    2. Wait for any commands
    3. Perform command actions
    4. GOTO 2
    """
    solar.connect()
    solar.log_constants()

    latitude = 0
    longitude = 0
    ra = 0
    dec = 0
    tune = [0.0, 0.0]
    tracking = False

    while True:
        if not tracking:
            msg = conn.recv()
            cmd, args = msg[0], msg[1:]
        else:
            while conn.poll():
                msg = conn.recv()
                cmd, args = msg[0], msg[1:]

        if cmd == Commands.TERMINATE:
            return
        elif cmd == Commands.SLEW_TO_SUN:
            assert(not tracking)
            ra, dec = slew_to_sun(conn, latitude, longitude, ra, dec)
        elif cmd == Commands.SLEW_RA:
            arcsec = args[0]
            ra = slew_ra(conn, ra, arcsec)
        elif cmd == Commands.SLEW_DEC:
            arcsec = args[0]
            dec = slew_dec(conn, dec, arcsec)
        elif cmd == Commands.SET_LAT:
            latitude = args[0]
        elif cmd == Commands.SET_LONG:
            longitude = args[0]
        elif cmd == Commands.SET_RA:
            if not tracking:
                ra = args[0]
        elif cmd == Commands.SET_DEC:
            if not tracking:
                dec = args[0]
        elif cmd == Commands.FINE_TUNE:
            tune = args[0]
        elif cmd == Commands.SET_ZERO:
            logging.info('Setting as zero')
            solar.reset_zero()
            conn.send([Responses.SET_RA, 0])
            conn.send([Responses.SET_DEC, 0])
            ra, dec = 0, 0
        elif cmd == Commands.SET_SUN:
            logging.info('Setting as Sun Position')
            solar.reset_zero()
            ra = sun_ra(longitude)
            dec = sun_dec(latitude)
            conn.send([Responses.SET_RA, ra])
            conn.send([Responses.SET_DEC, dec])
        elif cmd == Commands.TRACK:
            tracking = True
        elif cmd == Commands.CANCEL_TRACK:
            tracking = False
        else:
            raise NotImplementedError

        if tracking:
            ra, dec = track_action(conn, latitude, longitude, ra, dec, tune)


class TelescopeManager(Process):
    """
    Wrap the command protocol for the telescope thread, and implement the
    threading using the python multiprocessing Library
    """
    def not_slewing(f):
        """
        Decorator to check we arent already performing a slew
        """
        @wraps(f)
        def _not_slewing(*args, **kwargs):
            if args[0].commands_running is 0:
                return f(*args, **kwargs)
            else:
                return None
        return _not_slewing

    def not_tracking(f):
        """
        Decorator to check we arent tracking
        """
        @wraps(f)
        def _not_tracking(*args, **kwargs):
            if not args[0].tracking:
                return f(*args, **kwargs)
            else:
                return None
        return _not_tracking

    def __init__(self):
        self.conn, child_conn = Pipe()
        super(TelescopeManager, self).__init__(target=thread_process, args=(child_conn,))
        self._ra = 0
        self._dec = 0
        self._longitude = 0
        self._latitude = 0
        self.commands_running = 0
        self.tracking = False

    def join(self, timeout=15):
        """
        Finish the thread and perform any cleanup
        """
        if self.tracking:
            self.conn.send([Commands.CANCEL_TRACK])
        self.conn.send([Commands.TERMINATE])
        super(TelescopeManager, self).join(timeout=timeout)
        while self.commands_running > 0:
            self.flush_messages()

    def flush_messages(self):
        """
        Call to process any messages recieved from the telescope command thread
        """
        while self.conn.poll():
            msg = self.conn.recv()
            res, args = msg[0], msg[1:]
            if res == Responses.SLEW_FINISHED:
                self.commands_running -= 1
            elif res == Responses.SET_RA:
                self._ra = args[0]
            elif res == Responses.SET_DEC:
                self._dec = args[0]
            else:
                raise NotImplementedError

    @property
    def ra(self):
        return self._ra

    @ra.setter
    def ra(self, ra):
        self._ra = ra
        self.conn.send([Commands.SET_RA, ra])

    @property
    def dec(self):
        return self._dec

    @dec.setter
    def dec(self, dec):
        self._dec = dec
        self.conn.send([Commands.SET_DEC, dec])

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    @not_slewing
    @not_tracking
    def longitude(self, longitude):
        self._longitude = longitude
        self.conn.send([Commands.SET_LONG, longitude])

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    @not_slewing
    @not_tracking
    def latitude(self, latitude):
        self._latitude = latitude
        self.conn.send([Commands.SET_LAT, latitude])

    @not_slewing
    @not_tracking
    def slew_ra(self, arcsec):
        self.commands_running += 1
        self.conn.send([Commands.SLEW_RA, arcsec])

    @not_slewing
    @not_tracking
    def slew_dec(self, arcsec):
        self.commands_running += 1
        self.conn.send([Commands.SLEW_DEC, arcsec])

    @not_tracking
    def slew_to_sun(self):
        self.commands_running += 1
        self.conn.send([Commands.SLEW_TO_SUN])

    @not_tracking
    def return_to_zero(self):
        logging.info('Returning to zero')
        self.commands_running += 1
        self.conn.send([Commands.SLEW_RA, -self._ra])
        self.commands_running += 1
        self.conn.send([Commands.SLEW_DEC, -self._dec])

    def tune(self, tune):
        self.conn.send([Commands.FINE_TUNE, tune])

    def set_zero(self):
        self.conn.send([Commands.SET_ZERO])

    def set_sun(self):
        self.conn.send([Commands.SET_SUN])

    @not_tracking
    def start_tracking(self):
        self.tracking = True
        self.conn.send([Commands.TRACK])

    def stop_tracking(self):
        self.tracking = False
        self.conn.send([Commands.CANCEL_TRACK])
