#!/usr/bin/env python
"""
This module classes and methods for parsing log headers.
"""
##
# Copyright (C) 2012-2016 by SISSA - International School for Advanced Studies
#
# This file is part of Lograptor.
#
# Lograptor is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Lograptor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lograptor; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
# @Author Davide Brunato <brunato@sissa.it>
#
##
import re
import logging
from collections import namedtuple

from lograptor.exceptions import ConfigError

logger = logging.getLogger('lograptor')


class LogParser(object):
    """
    Base class to parse log lines.
    """
    def __init__(self, pattern, app=None):
        """
        Compile the pattern and record group fields. Check if pattern
        include mandatory named groups.
        """
        self.parser = re.compile(pattern)
        self.LogData = namedtuple('LogData', list(self.parser.groupindex.keys()))
        self.app = app
        self.fields = tuple(self.parser.groupindex.keys())

        for field in ('month', 'day', 'ltime', 'message'):
            if field not in self.parser.groupindex:
                msg = '%s: missing mandatory named group "%s"' % (self.__class__.__name__, field)
                raise ConfigError(msg)

    def match(self, line):
        """Perform header pattern matching on log line."""
        return self.parser.match(line)

    
class ParserRFC3164(LogParser):
    """
    Parser and extraction methods for BSD Syslog headers (RFC 3164).
    """

    def __init__(self, pattern):
        LogParser.__init__(self, pattern)
        rfc3164_fields = tuple([
            'pri', 'month', 'day', 'ltime', 'repeat', 'host', 'apptag', 'message'
            ])
        extra = set(self.fields) - set(rfc3164_fields)
        if extra:
            msg = 'no RFC 3164 fields in pattern: {0}'.format(extra)
            raise ConfigError(msg)
            

class ParserRFC5424(LogParser):
    """
    Parser for IETF-syslog logs (RFC 5424) .
    """

    def __init__(self, pattern):
        LogParser.__init__(self, pattern)
        rfc5424_fields = tuple([
            'pri', 'ver', 'year', 'month', 'day', 'ltime', 'secfrac', 'offset',
            'host', 'apptag', 'procid', 'msgid', 'message'
            ])
        extra = set(self.fields) - set(rfc5424_fields)
        if extra:
            msg = 'no RFC 5424 fields in pattern: {0}'.format(extra)
            raise ConfigError(msg)
