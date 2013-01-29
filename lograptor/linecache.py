"""
This module contains class to handle log line caching for Lograptor's
application class instances.
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
from __future__ import print_function

try:
    from collections import UserDict
except ImportError:
    # Fall back for Python 2.x
    from UserDict import IterableUserDict as UserDict

try:
    from collections import OrderedDict
except ImportError:
    # Backport for Python 2.4-2.6
    from lograptor.backports.ordereddict import OrderedDict
    

class CacheEntry:
    """
    Simple container class for cache entries
    """
    def __init__(self, event_time):
        self.pattern_match = False
        self.filter_match = False
        self.counted = False
        self.filter_set = set()
        self.buffer = list()        
        self.start_time = self.end_time = event_time


class LineCache(UserDict):
    """
    A class to manage line caching
    """
    
    def __init__(self, and_filters, tot_filters):
        self.data = OrderedDict()
        self._and_filters = and_filters
        self._tot_filters = tot_filters
    
    def add_line(self, line, thread, pattern_match, filter_match, rule_filters, event_time):        
        try:
            cache_entry = self.data[thread]
        except KeyError:
            cache_entry = self.data[thread] = CacheEntry(event_time)
        
        if pattern_match:
            cache_entry.pattern_match = True
        if filter_match:
            if not self._and_filters:
                cache_entry.filter_match = True
            elif not cache_entry.filter_match:
                cache_entry.filter_set.update(rule_filters)
                cache_entry.filter_match = (len(cache_entry.filter_set) >= self._tot_filters)
                
        cache_entry.buffer.append(line)
        cache_entry.end_time = event_time
        
    def flush_cache(self, output, prefix, event_time=None):
        """
        Flush the cache to output. Only matched threads are printed.
        Delete cache entries older (last updated) than 1 hour. Return
        the total lines of matching threads.
        """

        cache = self.data
        counter = 0
        
        for thread in cache.keys():
            if cache[thread].pattern_match and cache[thread].filter_match:
                if not cache[thread].counted:
                    counter += 1
                    cache[thread].counted = True

                if cache[thread].buffer:
                    if output:
                        for line in cache[thread].buffer:
                            print('{0}{1}'.format(prefix, line), end='')
                        print('--')
                    cache[thread].buffer = []
            if (abs(event_time - cache[thread].end_time) > 3600):
                del self[thread]
        return counter
    
    def flush_old_cache(self, output, prefix, event_time=None):
        """
        Flush the older cache to output. Only matched threads are printed.
        Delete cache entries older (last updated) than 1 hour. Return the
        total lines of old matching threads.
        """

        cache = self.data
        counter = 0
        
        for thread in cache.keys():
            if (abs(event_time - cache[thread].end_time) > 3600):
                if cache[thread].pattern_match and cache[thread].filter_match:
                    if not cache[thread].counted:
                        counter += 1
                        cache[thread].counted = True

                    if output and cache[thread].buffer:
                        for line in cache[thread].buffer:
                            print('{0}{1}'.format(prefix, line), end='')
                        print('--')
                del self[thread]
        return counter
