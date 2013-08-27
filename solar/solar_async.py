from multiprocessing import Process, Pipe
from datetime import datetime
import math
import solar
import logging
from functools import wraps
from common import *


class Commands:
    SET_RA, SET_DEC, SET_LAT, SET_LONG, \
        TRACK, CANCEL_TRACK, \
        TERMINATE, \
        SLEW_RA, SLEW_DEC, SLEW_TO_SUN, SET_ZERO = range(11)


class Responses:
    SET_RA, SET_DEC, SLEW_FINISHED = range(3)


def track_action(conn, latitude, longitude, ra, dec):
    # Get sun position
    # Add any calibraion
    # If far slew to location, otherwise smooth track

    # Now track along RA
    target = sun_ra(longitude)

    # If the gap has become large, slew
    if abs(target - ra) > solar.SEC_PER_ENC:
        solar.adjust_ra_sec(target - ra)
        ra = target
        conn.send([Responses.SET_RA, ra])
        logging.debug('Compensating for RA adjustment')

    # Otherwise smoothly track for at least 3 seconds
    time_tracked = 0
    start = datetime.utcnow()
    enc_tracked = 0
    enc_start = solar.current_position(solar.Devices.body)
    start_ra = ra

    while(time_tracked < 3):
        now = datetime.utcnow()
        dt = (now - start).total_seconds()
        enc_expected = math.floor(dt / solar.SEC_PER_ENC)
        enc_error = enc_expected - enc_tracked
        turns = (dt - time_tracked) // solar.SEC_PER_STEP

        if enc_error > 0:
            turns += solar.SLIP_FACTOR
        elif enc_error < 0:
            turns = 0

        if turns > 0:
            solar.Telescope().send_command('T{}{}{}'.format(solar.Devices.body, solar.Directions.clockwise, int(turns)))
            enc_tracked += int(solar.Telescope().readline()) - enc_start
            time_tracked = dt
            logging.debug('Micro Steps: {:5.2f} Encoder Error: {}'.format(turns, int(enc_error)))
            ra = start_ra + enc_tracked * solar.SEC_PER_ENC
            conn.send([Responses.SET_RA, ra])


def slew_to_sun(conn, latitude, longitude, ra, dec):
        sdec = sun_dec(latitude)
        sra = sun_ra(longitude)

        logging.info('Sun at: {} {}'.format(ra_to_str(sra), dec_to_str(sdec)))

        solar.adjust_dec(sdec - dec)
        conn.send([Responses.SET_DEC, sdec])

        while abs(sra - ra) > solar.SEC_PER_ENC:
            solar.adjust_ra_sec(sra - ra)
            ra = sra
            conn.send([Responses.SET_RA, ra])
            sra = sun_ra(longitude)

        conn.send([Responses.SLEW_FINISHED])
        return ra, sdec


def slew_ra(conn, ra, arcsec):
    solar.adjust_ra(arcsec)
    ra += arcsec / 15
    conn.send([Responses.SET_RA, ra])
    conn.send([Responses.SLEW_FINISHED])
    return ra


def slew_dec(conn, dec, arcsec):
    solar.adjust_dec(arcsec)
    dec += arcsec
    conn.send([Responses.SET_DEC, dec])
    conn.send([Responses.SLEW_FINISHED])
    return dec


def thread_process(conn):
    solar.connect()
    solar.log_constants()

    latitude = 0
    longitude = 0
    ra = 0
    dec = 0
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
            assert(not tracking)
            arcsec = args[0]
            ra = slew_ra(conn, ra, arcsec)
        elif cmd == Commands.SLEW_DEC:
            assert(not tracking)
            arcsec = args[0]
            dec = slew_dec(conn, dec, arcsec)
        elif cmd == Commands.SET_LAT:
            latitude = args[0]
        elif cmd == Commands.SET_LONG:
            longitude = args[0]
        elif cmd == Commands.SET_RA:
            ra = args[0]
        elif cmd == Commands.SET_DEC:
            dec = args[0]
        elif cmd == Commands.SET_ZERO:
            logging.info('Setting as zero')
            solar.reset_zero()
            conn.send([Responses.SET_RA, 0])
            conn.send([Responses.SET_DEC, 0])
            ra, dec = 0, 0
        elif cmd == Commands.TRACK:
            tracking = True
        elif cmd == Commands.CANCEL_TRACK:
            tracking = False
        else:
            raise NotImplementedError

        if tracking:
            track_action(conn, latitude, longitude, ra, dec)


class TelescopeManager(Process):
    def not_slewing(f):
        @wraps(f)
        def _not_slewing(*args, **kwargs):
            if args[0].commands_running is 0:
                return f(*args, **kwargs)
            else:
                return None
        return _not_slewing

    def not_tracking(f):
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
        if self.tracking:
            self.conn.send([Commands.CANCEL_TRACK])
        self.conn.send([Commands.TERMINATE])
        super(TelescopeManager, self).join(timeout=timeout)
        while self.commands_running > 0:
            self.flush_messages()

    def flush_messages(self):
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

    def set_zero(self):
        self.conn.send([Commands.SET_ZERO])

    @not_tracking
    def start_tracking(self):
        self.tracking = True
        self.conn.send([Commands.TRACK])

    def stop_tracking(self):
        self.tracking = False
        self.conn.send([Commands.CANCEL_TRACK])
