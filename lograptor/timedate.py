# -*- coding: utf-8 -*-
"""
This module contains additional class and functions to handle time
and date values for Lograptor package.
"""
#
# Copyright (C), 2011-2016, by Davide Brunato and
# SISSA (Scuola Internazionale Superiore di Studi Avanzati).
#
# This file is part of Lograptor.
#
# Lograptor is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# See the file 'LICENSE' in the root directory of the present
# distribution or http://www.gnu.org/licenses/gpl-2.0.en.html.
#
# @Author Davide Brunato <brunato@sissa.it>
#
import datetime
import re


DATE_FORMATS = (
    ('%%', re.compile(r"(%%)")),        # a literal %
    ('%a', re.compile(r"(?<!%)(%a)")),  # locale's abbreviated weekday name (e.g., Sun)
    ('%A', re.compile(r"(?<!%)(%A)")),  # locale's full weekday name (e.g., Sunday)
    ('%b', re.compile(r"(?<!%)(%b)")),  # locale's abbreviated month name (e.g., Jan)
    ('%B', re.compile(r"(?<!%)(%B)")),  # locale's full month name (e.g., January)
    ('%d', re.compile(r"(?<!%)(%d)")),  # day of month (e.g., 01)
    ('%j', re.compile(r"(?<!%)(%j)")),  # day of the year as zero padded decimal number (0 .. 366)
    ('%m', re.compile(r"(?<!%)(%m)")),  # month (01..12)
    ('%w', re.compile(r"(?<!%)(%w)")),  # day of the week (0 .. 6), 1 is monday
    ('%y', re.compile(r"(?<!%)(%y)")),  # last two digits of year (00..99)
    ('%Y', re.compile(r"(?<!%)(%Y)"))   # year
)


def parse_last(last):
    """
    Parse the --last value and return the time difference in seconds.
    """
    
    wordmap = {
        'hour': '1h',
        'day': '1d',
        'week': '1w',
        'month': '1m'
    }

    # seconds
    multmap = {
        'h': 3600,
        'd': 86400,
        'w': 604800,
        'm': 2592000
    }

    if last in wordmap:
        last = wordmap[last]

    cat = last[-1:].lower()

    if cat not in multmap:
        raise TypeError

    try: 
        num = int(last[:-1])
        if num <= 0:
            raise TypeError
    except ValueError: 
        raise TypeError
    
    diff = num * multmap[cat]    
    return diff


def get_interval(timestamp, diff, offset=0):
    """
    Returns datetime interval from timestamp backward in the past,
    computed using the milliseconds difference passed as argument.
    The final datetime is corrected with an optional offset.
    """
    fin_datetime = datetime.datetime.fromtimestamp(timestamp + offset)
    ini_datetime = datetime.datetime.fromtimestamp(timestamp - diff)
    return fin_datetime, ini_datetime


def parse_date(date):
    """
    Parse the --date value and return a couple of datetime object.
    The format is [YYYY]MMDD[,[YYYY]MMDD].
    """
    import datetime
    
    now = datetime.datetime.today()
    date_len = len(date)
    
    if date_len == 4:
        date1 = str(now.year) + date
        date2 = str(now.year) + date + "235959"
    elif date_len == 8:
        date1 = date
        date2 = date + "235959"
    elif date_len == 9:
        if date[4] != ',':
            raise TypeError
        date1 = str(now.year) + date[0:4]
        date2 = str(now.year) + date[5:9] + "235959"
    elif date_len == 17:
        if date[8] != ',':
            raise TypeError
        date1 = date[0:8]
        date2 = date[9:17] + "235959"
    else:
        raise TypeError

    try:
        date1 = datetime.datetime.strptime(date1, "%Y%m%d")
    except ValueError:
        if date_len < 9:
            raise ValueError("Error of date value in --date parameter, use --date=[YYYY]MMDD")
        else:
            raise ValueError("Error in the first date value in --date parameter, "
                             "use --date=[YYYY]MMDD,[YYYY]MMDD")
    try:
        date2 = datetime.datetime.strptime(date2, "%Y%m%d%H%M%S")        
    except ValueError:
        raise ValueError("Error in the second date value in --date parameter, "
                         "use --date=[YYYY]MMDD,[YYYY]MMDD")
        
    if date1 > date2:
        raise ValueError("Wrong parameter --date: the first date is after the second!")

    return date1, date2


class TimeRange(object):
    """
    A simple class to manage time range intervals
    """
    def __init__(self, timerange):
        """
        Constructor from timerange string.
        The time range format is HH:MM,HH:MM.
        """
        try:
            start_time, end_time = timerange.split(',')
        except ValueError:
            raise ValueError("%r is not a time range specification, use: HH:MM,HH:MM")

        self.start_time = datetime.datetime.strptime(start_time.strip(), '%H:%M').time()
        self.end_time = datetime.datetime.strptime(end_time.strip(), '%H:%M').time()
        if self.start_time == self.end_time:
            raise ValueError("times must be differents!")

        self.h1 = self.start_time.hour
        self.m1 = self.start_time.minute
        self.h2 = self.end_time.hour
        self.m2 = self.end_time.minute

    def between(self, mytime):
        """
        Compare if the parameter HH:MM is in the time range.
        """
        hour = int(mytime[0:2])
        minute = int(mytime[3:5])
        return not (
            hour < self.h1 or hour > self.h2 or
            (hour == self.h1 and minute < self.m1) or
            (hour == self.h2 and minute > self.m2)
        )


def strftimegen(start_dt, end_dt):
    """
    Return a generator function for strings containings datetime format specs.
    The generator produce a day-by-day sequence starting from the first datetime
    to the second datetime argument.
    """
    if start_dt > end_dt:
        raise ValueError("start datetime mustn't be after the end datetime")

    def iterftime(string):
        date_subs = [i for i in DATE_FORMATS if i[1].search(string) is not None]
        if not date_subs:
            yield string
        else:
            dt = start_dt
            date_path = string
            while end_dt >= dt:
                for item in date_subs:
                    date_path = item[1].sub(dt.strftime(item[0]), date_path)
                yield date_path
                dt = dt + datetime.timedelta(days=1)

    return iterftime
