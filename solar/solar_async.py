from multiprocessing import Process, Pipe
from datetime import datetime
import math
import solar
import logging
from common import *


def thread_process(conn):
    pass


class TelescopeManager(Process):
    def __init__(self):
        self.parent_conn, child_conn = Pipe()
        super(TelescopeManager, self).__init__(target=thread_process, args=(child_conn,))
        solar.connect()
        solar.log_constants()
        self._ra = 0
        self._dec = 0
        self._longitude = 0
        self._latitude = 0
        self.tracking = False

    @property
    def ra(self):
        return self._ra

    @property
    def dec(self):
        return self._dec

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, longitude):
        self._longitude = longitude

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, latitude):
        self._latitude = latitude

    def adjust_ra_arc(self, arcsec):
        solar.adjust_ra(arcsec)
        self._ra += arcsec * 15

    def adjust_ra(self, seconds):
        pass

    def adjust_dec(self, arcsec):
        solar.adjust_dec(arcsec)
        self._dec += arcsec

    def return_to_zero(self):
        logging.info('Returning to zero')
        solar.adjust_ra_sec(-self._ra)
        solar.adjust_dec(-self._dec)
        self._dec = 0
        self._ra = 0

    def set_zero(self):
        logging.info('Setting as zero')
        solar.reset_zero()
        self._ra = 0
        self._dec = 0

    def slew_to_sun(self):
        dec = sun_dec(self._latitude)
        ra = sun_ra(self._longitude)

        logging.info('Sun at: {} {}'.format(ra_to_str(ra), dec_to_str(dec)))

        solar.adjust_dec(dec - self._dec)
        self._dec = dec

        while abs(ra - self._ra) > 2 * solar.ARCSEC_PER_ENC:
            solar.adjust_ra_sec(ra - self._ra)
            self._ra = ra
            ra = sun_ra(self.longitude)

    def start_tracking(self):
        self.tracking = True

    def stop_tracking(self):
        self.tracking = False

    def track(self):
        # Get sun position
        # Add any calibraion
        # If far slew to location, otherwise smooth track
        while self.tracking:
            # Compensate for any fine tuning of declination
            dec = self._dec
            target = self.sun_dec() + self.ui.decAdjust.value()
            if abs(target - dec) > solar.ARCSEC_PER_ENC:
                solar.adjust_dec(target - dec)
                self._dec = target
                logging.debug('Compensating declination adjustment')

            # Now track along RA
            ra = self._ra
            target = self.sun_ra() + self.ui.raAdjust.value()

            # If the gap has become large, slew
            if abs(target - ra) > solar.SEC_PER_ENC:
                solar.adjust_ra_sec(target - ra)
                self._ra = target
                logging.debug('Compensating for RA adjustment')

            # Otherwise smoothly track for at least 3 seconds
            time_tracked = 0
            start = datetime.utcnow()
            enc_tracked = 0
            enc_start = solar.current_position(solar.Devices.body)
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
                    self._ra = ra + enc_tracked * solar.SEC_PER_ENC

                if self.tracking:
                    QtGui.QApplication.processEvents()
