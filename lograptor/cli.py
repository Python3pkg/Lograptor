#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command line tools for Lograptor package.
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
import os
import sys
import contextlib
import argparse
import time
import re
import sre_constants

from .core import exec_lograptor
from .info import __version__, __description__
from .exceptions import (
    LograptorConfigError, OptionError, FormatError, FileMissingError, FileAccessError, LograptorArgumentError
)
from .timedate import get_interval, parse_date, parse_last, TimeRange


def positive_integer(string):
    value = int(string)
    if value <= 0:
        msg = "%r is not a positive integer" % string
        raise argparse.ArgumentTypeError(msg)
    return value


def filter_spec(string):
    _filter = dict()
    for flt in string.split(','):
        try:
            field, pattern = flt.split('=', 1)
            field, pattern = field.lower(), pattern.strip('\'"')
            if not field:
                raise argparse.ArgumentTypeError('filter %r: empty field name!' % flt)
            elif not pattern:
                raise argparse.ArgumentTypeError('filter %r: empty pattern!' % flt)

            try:
                _filter[field] = re.compile(pattern)
            except sre_constants.error:
                raise argparse.ArgumentTypeError("wrong regex pattern in filter %r" % flt)
        except ValueError:
            raise argparse.ArgumentTypeError('filter %r: wrong format!' % flt)
    return _filter


def comma_separated_string(string):
    return [x.strip() for x in string.split(',')]


def last_spec(string):
    try:
        diff = parse_last(string)
    except TypeError:
        raise argparse.ArgumentTypeError('wrong format: %r' % string)
    return get_interval(int(time.time()), diff, 3600)


def date_interval_spec(string):
    try:
        return parse_date(string)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('%r: wrong format, use [YYYY]MMDD[,[YYYY]MMDD]' % string)


def create_argument_parser():
    """
    Command line options and arguments parsing. This function return
    a list of options and the list of arguments (pattern, filenames).
    """
    parser = argparse.ArgumentParser(prog='lograptor', description=__description__, add_help=False)
    parser.usage = """ %(prog)s [options] [PATTERN] [FILE ...]
    %(prog)s [options] [ -e PATTERN | -f FILE ] [FILE ...]
    Try '%(prog)s --help' for more information."""

    group = parser.add_argument_group("Matcher mode selection")
    group.add_argument(
        "-G", "--use-rules", action="store_true", default=False,
        help="use patterns and application rules (default)"
    )
    group.add_argument(
        "-X", "--exclude-rules", action="store_true", default=False,
        help="use patterns and skip application rules"
    )
    group.add_argument(
        "-U", "--unparsed", action="store_true", default=False,
        help="match the patterns, don't match any application rule"
    )

    group = parser.add_argument_group("Scope Selection")
    group.add_argument(
        "--apps", metavar='APP[,APP...]', type=comma_separated_string, dest="appnames",
        default=[], help="process the log lines related to an application"
    )
    group.add_argument(
        "--hosts", metavar="HOSTNAME/IP[,HOSTNAME/IP...]", type=comma_separated_string,
        dest="hostnames", default=[], help="process the log lines related to an hostname/IP"
    )
    group.add_argument(
        "--filter", metavar="FIELD=PATTERN[,FIELD=PATTERN...]",
        action="append", dest="filters", type=filter_spec, default=[],
        help="process the log lines that match all the conditions for rule's field values"
    )
    group.add_argument(
        "--time", metavar="HH:MM,HH:MM", type=TimeRange, action="store", dest="timerange",
        help="process the log lines related to a time range"
    )
    group.add_argument(
        "--date", metavar="[YYYY]MMDD[,[YYYY]MMDD]", action="store", dest="period",
        type=date_interval_spec, help="restrict the search scope to a date or a date range"
    )
    group.add_argument(
        "--last", action="store", dest="period", type=last_spec,
        metavar="[hour|day|week|month|Nh|Nd|Nw|Nm]",
        help="restrict the search scope to a previous time period"
    )

    group = parser.add_argument_group("Data control")
    group.add_argument(
        "--report", metavar='NAME', nargs='?', default=None,
        help="produce a report at the end of processing"

    )
    group.add_argument(
        "--ip-lookup", action="store_true", default=False,
        help="translate IP addresses to DNS names"
    )
    group.add_argument(
        "--uid-lookup", action="store_true", default=False,
        help="translate UIDs to usernames"
    )
    group.add_argument(
        "--anonymize", action="store_true", default=False,
        help="anonymize defined rule's fields value"
    )
    group.add_argument(
        "--timestamps", action="store_true", default=False,
        help="create and verify timestamps on input log files"
    )

    group = parser.add_argument_group("Regexp matching control")
    group.add_argument(
        "-e", "--regexp", metavar="PATTERN", dest="patterns", default=[],
        action="append", help="use PATTERN for matching"
    )
    group.add_argument(
        "-f", "--file", metavar="FILE", dest="pattern_files", default=[],
        action="append", help="obtain patterns from FILE"
    )
    group.add_argument(
        "-i", "--ignore-case", action="store_true", dest="case", default=False,
        help="ignore case distinctions"
    )
    group.add_argument(
        "-v", "--invert-match", action="store_true", dest="invert", default=False,
        help="invert the sense of regexp matching"
    )
    group.add_argument(
        "-w", "--word-regexp", action="store_true", dest="word", default=False,
        help="force PATTERN to match only whole words"
    )

    group = parser.add_argument_group("Output control")
    group.add_argument(
        "--output", default=['stdout'], metavar='CHANNEL[,CHANNEL...]', dest='channels',
        type=comma_separated_string, help="send output to channels (default: ['stdout'])"
    )
    group.add_argument(
        "-m", "--max-count", metavar='NUM', action="store", type=positive_integer, default=None,
        help="stop after NUM matches"
    )
    group.add_argument(
        "-n", "--line-number", action="store_true", default=False,
        help="print line number with output lines"
    )
    group.add_argument(
        "-H", "--no-source", action="store_false", dest="print_filename", default=None,
        help="print the file name for each match"
    )
    group.add_argument(
        "-h", "--with-source", action="store_true", dest="print_filename", default=None,
        help="suppress the file name prefix on output"
    )
    group.add_argument(
        "-o", "--only-matching", action="store_true", default=False,
        help="show only the part of a line matching PATTERN"
    )
    group.add_argument(
        "-q", "--quiet", action="store_true", default=False, help="suppress all normal output"
    )
    group.add_argument(
        "-r", "--recursive", action="store_true", default=False,
        help="read all files under each directory, recursively"
    )
    group.add_argument(
        "-R", "--dereference-recursive", action="store_true", default=False,
        help="likewise, but follow all symlinks"
    )
    group.add_argument(
        "--include", metavar='GLOB', help="search only files that match GLOB"
    )
    group.add_argument(
        "--exclude", metavar='GLOB', help="skip files and directories matching GLOB"
    )
    group.add_argument(
        "--exclude-from", metavar='FILE', help="skip files matching any file pattern from FILE"
    )
    group.add_argument(
        "--exclude-dir", metavar='DIR', help="exclude directories matching the pattern DIR"
    )
    group.add_argument(
        "-L", "--files-without-match", action="store_false", dest="files_with_match",
        help="print only names of FILEs containing no match"
    )
    group.add_argument(
        "-l", "--files-with-match", action="store_true", dest="files_with_match",
        help="print only names of FILEs containing matches"
    )
    group.add_argument(
        "-c", "--count", action="store_true", default=False,
        help="print only a count of matching lines per FILE"
    )
    group.add_argument(
        "--color", action="store_true", default=False,
        help="use markers to highlight the matching strings"
    )

    group = parser.add_argument_group("Context control")
    group.add_argument(
        "-T", "--thread", action="store_true", default=False,
        help="print the thread related context"
    )
    group.add_argument(
        "-B", "--before-context", metavar='NUM', type=positive_integer, default=0,
        help="print NUM lines of leading context"
    )
    group.add_argument(
        "-A", "--after-context", metavar='NUM', type=positive_integer, default=0,
        help="print NUM lines of trailing context"
    )
    group.add_argument(
        "-C", "--context", metavar='NUM', type=positive_integer, default=0,
        help="print NUM lines of output context"
    )
    group.add_argument(
        "--group-separator", metavar='SEP', default='--', help="use SEP as a group separator"
    )
    group.add_argument(
        "--no-group-separator", dest="group_separator", action="store_const", const='',
        help="use empty string as a group separator"
    )

    group = parser.add_argument_group("Other options")
    group.add_argument(
        "--conf", dest="cfgfile", nargs=1, metavar="FILE",
        default=['lograptor.conf', '/etc/lograptor/lograptor.conf'],
        help="use a specific configuration file"
    )
    group.add_argument(
        "-d", dest="loglevel", default=2, type=int, metavar="[0-4]", choices=range(5),
        help="logging level (default is 2, use 4 for debug)"
    )
    group.add_argument(
        "-s", "--no-messages", action="store_true", default=False,
        help="suppress error messages, equivalent to -d=0 option"
    )
    group.add_argument('-V', '--version', action='version', version=__version__)
    group.add_argument('--help', action='help', help="show this help message and exit")

    parser.add_argument('files', metavar='[FILE...]', nargs='*', help="Input filename/s.")
    return parser


class DummyFile(object):
    def write(self, x):
        pass

    def flush(self):
        pass


@contextlib.contextmanager
def nostdout():
    """Redirect the stdout to a dummy file"""
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout


def main():
    if sys.version_info < (2, 7, 0):
        sys.stderr.write("You need python 2.7 or later to run this program\n")
        sys.exit(1)

    cli_parser = create_argument_parser()
    args = cli_parser.parse_args()

    if os.isatty(sys.stdin.fileno()):
        try:
            retval = exec_lograptor(args, is_batch=False)
        except (LograptorArgumentError, OptionError) as e:
            if e.message:
                cli_parser.error(e)
            else:
                cli_parser.print_usage()
                sys.exit(2)
        except (LograptorConfigError, FormatError, FileMissingError, FileAccessError) as e:
            sys.exit(u"ERROR: {0}\nExiting ...".format(e))
        except KeyboardInterrupt:
            print("\nCtrl-C pressed, terminate the process ...")
            sys.exit(1)
    else:
        with nostdout():
            try:
                retval = exec_lograptor(args, is_batch=True)
            except (LograptorArgumentError, OptionError, LograptorConfigError,
                    FormatError, FileMissingError, FileAccessError) as e:
                sys.exit(u"ERROR: {0}\nExiting ...".format(e))
    sys.exit(retval)


if __name__ == '__main__':
    main()
