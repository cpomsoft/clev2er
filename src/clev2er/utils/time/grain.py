#!/usr/bin/env python
# encoding: utf-8
"""
Author: Nick Bearson, nickb@ssec.wisc.edu
Copyright (c) 2014 University of Wisconsin SSEC. All rights reserved.
Get new leap second files @ https://www.ietf.org/timezones/data/leap-seconds.list
"""

import os
from datetime import datetime, timedelta

# Useful constants...
VIIRS_EPOCH = datetime(1958, 1, 1)
MODIS_EPOCH = datetime(1993, 1, 1)
UNIX_EPOCH = datetime(1970, 1, 1)
NTP_EPOCH = datetime(1900, 1, 1)
CS2_EPOCH = datetime(2000, 1, 1)

DEFAULT_EPOCH = CS2_EPOCH

# Use the leap-seconds file included with this package if none is specified


class Grain:
    """An object for parsing and utilizing the information contained in a leap second file.
    Initialize with a file object, ie: the result of open(...)"""

    def __init__(self, leap_second_filename=None):
        if leap_second_filename is None:
            raise ValueError("No leap_second_filename provided")
        if not os.path.isfile(leap_second_filename):
            raise FileNotFoundError(f"{leap_second_filename} not found")

        with open(leap_second_filename, encoding="utf-8") as leap_second_file:
            leap_times = []
            offsets = []
            for line in leap_second_file:
                stripped_line = line.strip()
                if not stripped_line.startswith("#"):
                    pieces = stripped_line.split()
                    leap_time = NTP_EPOCH + timedelta(seconds=int(pieces[0]))
                    leap_times.append(leap_time)
                    offset = int(pieces[1])
                    offsets.append(offset)

            # Convert our offsets from leapseconds-from-beginning to the change at
            # each instant - it'll make things easier to deal with later!
            # add 0 to the start so our math works in the next line
            offsets.insert(0, 0)
            offsets = [j - i for i, j in zip(offsets[:-1], offsets[1:])]
            self.leaps = list(zip(leap_times, offsets))

    def _leaps_between(self, date1, date2):
        """
        Counts the number of leap seconds that have occurred between two datetimes
        """
        if date1 > date2:
            raise RuntimeError("date1 > date2")
        between_times = [
            i for i in self.leaps if date1 <= i[0] and i[0] <= date2
        ]  # should these be > or >=?
        # sum all the offsets in self.leaps
        offset = sum(leap[1] for leap in between_times)
        return offset

    def utc2tai(self, utc, epoch=DEFAULT_EPOCH):
        """
        Takes datetime object (utc) and returns TAI seconds since given epoch.
        """
        offset = self._leaps_between(epoch, utc)
        tai = utc - epoch
        seconds_since_epoch = (tai.days * (24 * 60 * 60)) + tai.seconds + offset
        return seconds_since_epoch

    def tai2utc(self, seconds_since_epoch, epoch=DEFAULT_EPOCH):
        """
        Takes TAI seconds since given epoch and returns a datetime.
        """
        td_sse = timedelta(seconds=seconds_since_epoch)
        utc_unadjusted = td_sse + epoch

        offset = self._leaps_between(NTP_EPOCH, utc_unadjusted)
        td_offset = timedelta(seconds=offset)
        utc = utc_unadjusted - td_offset
        return utc
