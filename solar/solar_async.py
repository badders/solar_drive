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


def slew_to_sun(properties):
    """
    Perform a slew to the suns location

    properties - A TrackProperties object
    """
    sdec = sun_dec(properties.latitude)
    sra = sun_ra(properties.longitude)

    logging.info('Sun at: {} {}'.format(ra_to_str(sra), dec_to_str(sdec)))

    solar.adjust_dec(sdec - properties.dec)
    properties.conn.send([Responses.SET_DEC, sdec])

    """
    As slewing can take a long time, might need to slew some more to catch
    up with the Sun
    """
    while abs(sra - properties.ra) > 2 * solar.SEC_PER_ENC:
        solar.adjust_ra_sec(sra - properties.ra)
        properties.ra = sra
        properties.conn.send([Responses.SET_RA, properties.ra])
        sra = sun_ra(properties.longitude)

    properties.conn.send([Responses.SLEW_FINISHED])


def slew_ra(properties, arcsec):
    """
    Slew the right ascension of the telescope

    properties - A TrackProperties object
    arcsec -- Arc seconds to slew by
    """
    solar.adjust_ra(arcsec)
    properties.ra += arcsec / 15
    properties.conn.send([Responses.SET_RA, properties.ra])
    properties.conn.send([Responses.SLEW_FINISHED])


def slew_dec(properties, arcsec):
    """
    Slew the declination of the telescope

    properties - A TrackProperties object
    arcsec -- Arc seconds to slew by
    """
    solar.adjust_dec(arcsec)
    properties.dec += arcsec
    properties.conn.send([Responses.SET_DEC, properties.dec])
    properties.conn.send([Responses.SLEW_FINISHED])


class TrackProperties:
    ra = 0
    dec = 0
    latitude = 0
    longitude = 0
    tune_latitude = 0
    tune_longitude = 0
    connection = None


def track_process(properties):
    time_tracked = 0
    start = datetime.utcnow()
    enc_tracked = 0
    enc_start = solar.current_position(solar.Devices.body)
    start_ra = properties.ra
    dt = 0

    while True:
        # Process any available messages
        while properties.conn.poll():
            msg = properties.conn.recv()
            cmd, args = msg[0], msg[1:]

            if cmd == Commands.CANCEL_TRACK:
                return
            elif cmd == Commands.FINE_TUNE:
                tune_longitude = args[0][0]
                tune_latitude = args[0][0]
                properties.tune_longitude = tune_longitude
                properties.tune_latitude = tune_latitude
            else:
                raise NotImplementedError

        # Do Tracking
        now = datetime.utcnow()
        dt = (now - start).total_seconds()
        enc_expected = math.floor(dt / solar.SEC_PER_ENC)
        enc_error = enc_expected - enc_tracked
        turns = (dt - time_tracked) // solar.SEC_PER_STEP

        # Check encoders report the position we expect, otherwise compensate
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
            properties.ra = start_ra + enc_tracked * solar.SEC_PER_ENC
            properties.conn.send([Responses.SET_RA, properties.ra])


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

    properties = TrackProperties()
    properties.conn = conn

    while True:
        msg = conn.recv()
        cmd, args = msg[0], msg[1:]

        if cmd == Commands.TERMINATE:
            return
        elif cmd == Commands.SLEW_TO_SUN:
            slew_to_sun(properties)
        elif cmd == Commands.SLEW_RA:
            arcsec = args[0]
            slew_ra(properties, arcsec)
        elif cmd == Commands.SLEW_DEC:
            arcsec = args[0]
            slew_dec(properties, arcsec)
        elif cmd == Commands.SET_LAT:
            properties.latitude = args[0]
        elif cmd == Commands.SET_LONG:
            properties.longitude = args[0]
        elif cmd == Commands.SET_RA:
            properties.ra = args[0]
        elif cmd == Commands.SET_DEC:
            properties.dec = args[0]
        elif cmd == Commands.FINE_TUNE:
            properties.tune_longitude = args[0][0]
            properties.tune_latitude = args[0][1]
        elif cmd == Commands.SET_ZERO:
            logging.info('Setting as zero')
            solar.reset_zero()
            conn.send([Responses.SET_RA, 0])
            conn.send([Responses.SET_DEC, 0])
            properties.ra = 0
            properties.dec = 0
        elif cmd == Commands.SET_SUN:
            logging.info('Setting as Sun Position')
            solar.reset_zero()
            properties.ra = sun_ra(properties.longitude)
            properties.dec = sun_dec(properties.latitude)
            conn.send([Responses.SET_RA, properties.ra])
            conn.send([Responses.SET_DEC, properties.dec])
        elif cmd == Commands.TRACK:
            track_process(properties)
        else:
            raise NotImplementedError


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
