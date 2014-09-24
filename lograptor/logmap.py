#!/usr/bin/env python
"""
This module contains classes and methods to handle a map of log files.
"""
##
# Copyright (C) 2012 by SISSA
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
# @Author Davide Brunato <brunato@sissa.it>
##

import datetime 
import logging
import re
import fnmatch
import glob
import os
import platform

logger = logging.getLogger("lograptor")


class LogMap:
    """
    This is a container class to manage a collection of log files.
    The collection is generated by configuration parameters. You should
    use this class as an iterator to access and read sequentially all
    the log listed in the base.
    """
    
    datesub = {
        'year' : re.compile(r"(?<!%)(%Y)"),
        'month' : re.compile(r"(?<!%)(%m)"),
        'day' : re.compile(r"(?<!%)(%d)"),
        'perc' : re.compile(r"(%%)")
        }
    
    def __init__(self, initial_datetime, final_datetime):
        """
        Create a new log map, including host, logdir parameter and two datetime
        """
        
        self.dt1 = initial_datetime     # Initial date and time for logmap iteration
        self.dt2 = final_datetime       # Final date and time for logmap iteration

        self.__logmap = dict()
        self.__appmap = dict()

    def __iter__(self):
        """
        Iterate into the log base, with name expansion
        """
        logger.debug("Start LogMap iteration ...")        
        logger.debug(self.__logmap)
        self.__ordmap = sorted(self.__logmap, key=lambda x:(self.__logmap[x][0],x))
        logger.debug(self.__ordmap)
        
        for logfile in self.__ordmap:
            logfile_by_args = (self.__logmap[logfile][1]=="*")
            applist = sorted(self.__logmap[logfile][1:], key=lambda x:(self.__appmap[x],x))
            logger.debug(applist)
            
            sub_year = self.datesub['day'].search(logfile) is not None
            sub_month = self.datesub['month'].search(logfile) is not None
            sub_day = self.datesub['year'].search(logfile) is not None
            sub_perc = self.datesub['perc'].search(logfile) is not None
            if ( sub_year or sub_month or sub_day ):
                logger.debug('Expand logfile set {0}'.format(logfile))

                dt = self.dt1
                lastpath = None
                while self.dt2 >= dt:
                    newpath = logfile
                    if sub_year:
                        newpath = self.datesub['year'].sub(str(dt.year), newpath)
                    if sub_month:
                        newpath = self.datesub['month'].sub(format(dt.month,'02d'), newpath)
                    if sub_day:
                        newpath = self.datesub['day'].sub(format(dt.day,'02d'), newpath)
                    if sub_perc:
                        newpath = self.datesub['perc'].sub("%", newpath)
                    if lastpath is None or lastpath != newpath:
                        logger.debug('Select logfile {0}'.format(newpath))
                        
                        filename = None
                        for filename in glob.iglob(newpath):
                            if self.check_logfile_stat(filename, sub_day or logfile_by_args):
                                yield (filename, applist)
                        if filename is None and self.__logmap[logfile][1] == "*":
                            logger.error('No file corresponding to path {0}'.format(newpath))
                        lastpath = newpath
                                                    
                    dt = dt + datetime.timedelta(days=1)
            else:
                logger.debug('Select logfile {0}'.format(logfile))

                if sub_perc:
                    logfile = self.datesub['perc'].sub("%", logfile)

                filename = None
                for filename in glob.iglob(logfile):
                    if self.check_logfile_stat(filename, logfile_by_args):
                        yield (filename, applist)
                if filename is None and self.__logmap[logfile][1] == "*":
                    logger.error('No file corresponding to path {0}'.format(logfile))


    def check_logfile_stat(self, logfile, outerrs=False):
        """
        Checks logfile stat information to exclude older or newer files. On linux
        it's possible to checks only modification time, because file creation info
        are not available, so it's possible to exclude only older files.
        In Unix BSD systems and windows informations about file creation date and times are available,
        so is possible to exclude too newer files.
        """
        statinfo = os.stat(logfile)
        st_mtime = datetime.datetime.fromtimestamp(statinfo.st_mtime)
        if platform.system() == 'Windows':
            st_ctime = datetime.datetime.fromtimestamp(statinfo.st_mtime)
            logger.info('Log file: {0}; st_ctime: {1}; st_mtime: {2}'
                        .format(logfile, st_ctime, st_mtime))
            check = (st_mtime >= self.dt1) and (st_ctime <= self.dt2)
            if outerrs and not check:
                if not ((self.dt1 - st_mtime).days == 0 or (st_ctime - self.dt2).days == 0):  
                    logger.error('Log file ({0}) not in datetime range!!'.format(logfile))
        else:
            logger.info('Log file: {0}; st_mtime: {1}'
                        .format(logfile, st_mtime))
            check = (st_mtime >= self.dt1)
            if outerrs and not check:
                if not ((self.dt1 - st_mtime).days == 0):  
                    logger.error('Log file ({0}) is older than expected!!'.format(logfile))
        return check
             
    def check_log_datetime_range(self, logfile, outerrs=False):
        """
        Check (True/False) if the logfile is in the datetime range of the LogMap.
        Both st_ctime and st_mtime are checked. Despite ctime sign only metadata
        change on unix, it's a flag about file change
        """
        statinfo = os.stat(logfile)
        dt = datetime.datetime.fromtimestamp(statinfo.st_mtime)
        logger.info('Log file: {0}; {1}'.format(logfile, dt))
        check = ( dt >= self.dt1 ) and ( dt <= self.dt2 )
        if (not check) and outerrs:
            if not ((self.dt1-dt).days == 0 or (dt-self.dt2).days == 0):  
                logger.error('Log file ({0}) not in datetime range!!'.format(logfile))
        return check
    
    def add(self, appname, fileset, priority=0 ):
        """
        Add a list of logfiles from an app configuration, replacing variables to host and
        dates with specific wildcards.
        """

        logger.debug('Adding the set of paths of app "{0}"'.format(appname))
        self.__appmap[appname] = priority
        for newlog in fileset:            
            logger.debug('Processing file path: {0}'.format(newlog))

            for maplog in self.__logmap:
                if fnmatch.fnmatch(newlog, maplog):
                    logger.debug('Adding "{0}" to path: {1}'.format(appname, maplog))
                    self.__logmap[maplog].append(appname)
                    if self.__logmap[maplog][0] > priority:
                        self.__logmap[maplog][0] = priority
                    newlog = None
                    break
                if fnmatch.fnmatch(maplog, newlog):
                    logger.debug('Replacing path: {0} '.format(maplog))
                    self.__logmap[newlog] = self.__logmap[maplog]
                    self.__logmap[newlog].append(appname)
                    if self.__logmap[newlog][0] > priority:
                        self.__logmap[newlog][0] = priority
                    del self.__logmap[maplog]
                    newlog = None
                    break
                
            if newlog is not None:
                logger.debug('Adding path {0} with priority {1}'.format(newlog, priority))
                self.__logmap[newlog] = [priority, appname]
