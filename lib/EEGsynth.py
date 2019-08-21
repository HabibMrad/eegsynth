import configparser
import os
import sys
import time
import threading
import math
import numpy as np
from scipy.signal import firwin, decimate, lfilter, lfilter_zi, lfiltic, iirnotch

###################################################################################################
def printkeyval(key, val):
    try:
        # this works in Python 2, but fails in Python 3
        isstring = isinstance(val, basestring)
    except:
        try:
            # this works in Python 3, but fails for unicode strings in Python 2
            isstring = isinstance(val, str)
        except:
            isstring = False
    if val is None:
        print("%s = None" % (key))
    elif isinstance(val, list):
        print("%s = %s" % (key, str(val)))
    elif isstring:
        print("%s = %s" % (key, val))
    else:
        print(key, val, type(val))
        print("%s = %g" % (key, val))

###################################################################################################
def trimquotes(option):
    # remove leading and trailing quotation marks
    # this is needed to include leading or trailing spaces in an ini-file option
    if option[0]=='"':
        option = option[1:]
    if option[0]=='\'':
        option = option[1:]
    if option[-1]=='"':
        option = option[0:-1]
    if option[-1]=='\'':
        option = option[0:-1]
    return option

###################################################################################################
class monitor():
    """Class to monitor control values and print them to screen when they have changed. It also
    prints a boilerplate license upon startup.
    """

    def __init__(self):
        self.previous_value = {}
        self.loop_time = None
        print("""
##############################################################################
# This software is part of the EEGsynth, see <http://www.eegsynth.org>.
#
# Copyright (C) 2017-2019 EEGsynth project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

Press Ctrl-C to stop this module.
        """)

    def loop(self, debug=True):
        now = time.time()
        if self.loop_time is None:
            if debug:
                print("Starting loop...")
            self.loop_time = now
            self.loop_count = 0
        else:
            self.loop_count += 1
        elapsed = now - self.loop_time
        if elapsed>=1:
            if debug:
                print("looping with %d iterations in %g seconds" % (self.loop_count, elapsed))
            self.loop_time = now
            self.loop_count = 0

    def update(self, key, val, debug=True):
        if (key not in self.previous_value) or (self.previous_value[key]!=val):
            try:
                # the comparison returns false in case both are nan
                a = math.isnan(self.previous_value[key])
                b = math.isnan(val)
                if (a and b):
                    debug = False
            except:
                pass
            if debug:
                printkeyval(key, val)
            self.previous_value[key] = val
            return True
        else:
            return False

###################################################################################################
class patch():
    """Class to provide a generalized interface for patching modules using
    configuration files and Redis.

    The formatting of the item in the ini file should be like this
      item=1            this returns 1
      item=key          get the value of the key from redis
    or if multiple is True
      item=1-20         this returns [1,20]
      item=1,2,3        this returns [1,2,3]
      item=1,2,3,5-9    this returns [1,2,3,5,9], not [1,2,3,4,5,6,7,8,9]
      item=key1,key2    get the value of key1 and key2 from redis
      item=key1,5       get the value of key1 from redis
      item=0,key2       get the value of key2 from redis
    """

    def __init__(self, c, r):
        self.config = c
        self.redis  = r

    ####################################################################
    def getfloat(self, section, item, multiple=False, default=None, debug=False):
        if self.config.has_option(section, item) and len(self.config.get(section, item))>0:
            # get all items from the ini file, there might be one or multiple
            items = self.config.get(section, item)

            if multiple:
                # convert the items to a list
                if items.find(",") > -1:
                    separator = ","
                elif items.find("-") > -1:
                    separator = "-"
                elif items.find("\t") > -1:
                    separator = "\t"
                else:
                    separator = " "
                items = squeeze(' ', items)        # remove excess whitespace
                items = squeeze(separator, items)  # remove double separators
                items = items.split(separator)     # split on the separator
            else:
                # make a list with a single item
                items = [items]

            # set the default
            if default != None:
                val = [float(default)] * len(items)
            else:
                val = [default] * len(items)

            # convert the strings into floating point values
            for i,item in enumerate(items):
                try:
                    # if it resembles a value, use that
                    val[i] = float(item)
                except ValueError:
                    # if it is a string, get the value from Redis
                    try:
                        val[i] = float(self.redis.get(item))
                    except TypeError:
                        pass
        else:
            # the configuration file does not contain the item
            if multiple == True and default == None:
                val = []
            elif multiple == True and default != None:
                val = [float(x) for x in default]
            elif multiple == False and default == None:
                val = None
            elif multiple == False and default != None:
                val = float(default)

        if debug:
            printkeyval(item, val)

        if multiple:
            # return it as list
            return val
        else:
            # return a single value
            if isinstance(val, list):
                return val[0]
            else:
                return val

    ####################################################################
    def getint(self, section, item, multiple=False, default=None, debug=False):
        if self.config.has_option(section, item) and len(self.config.get(section, item))>0:
            # get all items from the ini file, there might be one or multiple
            items = self.config.get(section, item)

            if multiple:
                # convert the items to a list
                if items.find(",") > -1:
                    separator = ","
                elif items.find("-") > -1:
                    separator = "-"
                elif items.find("\t") > -1:
                    separator = "\t"
                else:
                    separator = " "
                items = squeeze(' ', items)        # remove excess whitespace
                items = squeeze(separator, items)  # remove double separators
                items = items.split(separator)     # split on the separator
            else:
                # make a list with a single item
                items = [items]

            # set the default
            if default != None:
                val = [int(default)] * len(items)
            else:
                val = [default] * len(items)

            # convert the strings into integer values
            for i,item in enumerate(items):
                try:
                    # if it resembles a value, use that
                    val[i] = int(item)
                except ValueError:
                    # if it is a string, get the value from Redis
                    try:
                        val[i] = int(round(float(self.redis.get(item))))
                    except TypeError:
                        pass
        else:
            # the configuration file does not contain the item
            if multiple == True and default == None:
                val = []
            elif multiple == True and default != None:
                val = [int(x) for x in default]
            elif multiple == False and default == None:
                val = None
            elif multiple == False and default != None:
                val = int(default)

        if debug:
            printkeyval(item, val)

        if multiple:
            # return it as list
            return val
        else:
            # return a single value
            if isinstance(val, list):
                return val[0]
            else:
                return val

    ####################################################################
    def getstring(self, section, item, default=None, multiple=False, debug=False):
        # get all items from the ini file, there might be one or multiple
        try:
            val = self.config.get(section, item)
        except:
            val = default

        if multiple:
            if val==None or len(val)==0:
                # convert it to an empty list
                val = []
            else:
                # convert the string with items to a list
                if val.find(",") > -1:
                    separator = ","
                elif val.find("-") > -1:
                    separator = "-"
                elif val.find("\t") > -1:
                    separator = "\t"
                else:
                    separator = " "

                val = squeeze(separator, val)  # remove double separators
                val = val.split(separator)     # split on the separator

        if debug:
            printkeyval(item, val)

        if multiple:
            # return it as list
            return val
        else:
            # return a single value
            if isinstance(val, list):
                return val[0]
            else:
                return val

    ####################################################################
    def hasitem(self, section, item):
        # check whether an item is present in the ini file
        return self.config.has_option(section, item)

    ####################################################################
    def setvalue(self, item, val, debug=False, duration=0):
        self.redis.set(item, val)      # set it as control channel
        self.redis.publish(item, val)  # send it as trigger
        if debug:
            print("%s = %g" % (item, val))
        if duration > 0:
            # switch off after a certain amount of time
            threading.Timer(duration, self.setvalue, args=[item, 0.]).start()


####################################################################
def rescale(xval, slope=None, offset=None, reverse=False):
    if hasattr(xval, "__iter__"):
        return [rescale(x, slope, offset) for x in xval]
    elif xval == None:
        return None
    else:
        if slope==None:
            slope = 1.0
        if offset==None:
            offset = 0.0
        if reverse:
            return (float(xval) - float(offset))/float(slope)
        else:
            return float(slope)*float(xval) + float(offset)

####################################################################
def limit(xval, lo=0.0, hi=127.0):
    if hasattr(xval, "__iter__"):
        return [limit(x, lo, hi) for x in xval]
    elif xval == None:
        return None
    else:
        xval = float(xval)
        lo = float(lo)
        hi = float(hi)
        if xval < lo:
            return lo
        elif xval > hi:
            return hi
        else:
            return xval

####################################################################
def compress(xval, lo=0.5, hi=0.5, range=1.0):
    if hasattr(xval, "__iter__"):
        return [compress(x, lo, hi, range) for x in xval]
    else:
        xval  = float(xval)
        lo    = float(lo)
        hi    = float(hi)
        range = float(range)

        if lo>range/2:
          ax = 0.0
          ay = lo-range/2
        else:
          ax = range/2-lo
          ay = 0.0

        if hi<range/2:
          bx = range
          by = range/2+hi
        else:
          bx = 1.5*range-hi
          by = range

        if (bx-ax)==0:
            # threshold the value halfway
            yval = (xval>0.5)*range
        else:
            # map the value according to a linear transformation
            slope     = (by-ay)/(bx-ax)
            intercept = ay - ax*slope
            yval      = (slope*xval + intercept)

        if yval<0:
          yval = 0
        elif yval>range:
          yval = range

        return yval

####################################################################
def normalizerange(xval, min, max):
    min = float(min)
    max = float(max)
    return (float(xval)-min)/(max-min)

####################################################################
def normalizestandard(xval, avg, std):
    avg = float(avg)
    std = float(std)
    return (float(xval)-avg)/std

####################################################################
def squeeze(char, string):
    while char*2 in string:
        string = string.replace(char*2, char)
    return string

####################################################################
def initialize_online_notchfilter(fsample, fnotch, quality, x, axis=-1):
    nyquist = fsample / 2.
    ndim = len(x.shape)
    axis = axis % ndim

    if fnotch != None:
        fnotch = fnotch/nyquist
        if fnotch < 0.001:
            fnotch = None
        elif fnotch > 0.999:
            fnotch = None

    if not(fnotch == None) and (quality>0):
        print('using NOTCH filter', [fnotch, quality])
        b, a = iirnotch(fnotch, quality)
    else:
        # no filtering at all
        print('using IDENTITY filter', [fnotch, quality])
        b = np.ones(1)
        a = np.ones(1)

    # initialize the state for the filtering based on the previous data
    if ndim == 1:
        zi = zi = lfiltic(b, a, x, x)
    elif ndim == 2:
        f = lambda x : lfiltic(b, a, x, x)
        zi = np.apply_along_axis(f, axis, x)

    return b, a, zi

####################################################################
def initialize_online_filter(fsample, highpass, lowpass, order, x, axis=-1):
    # boxcar, triang, blackman, hamming, hann, bartlett, flattop, parzen, bohman, blackmanharris, nuttall, barthann
    filtwin = 'nuttall'
    nyquist = fsample / 2.
    ndim = len(x.shape)
    axis = axis % ndim

    if highpass != None:
        highpass = highpass/nyquist
        if highpass < 0.001:
            print('Warning: highpass is too low, disabling')
            highpass = None
        elif highpass > 0.999:
            print('Warning: highpass is too high, disabling')
            highpass = None

    if lowpass != None:
        lowpass = lowpass/nyquist
        if lowpass < 0.001:
            print('Warning: lowpass is too low, disabling')
            lowpass = None
        elif lowpass > 0.999:
            print('Warning: lowpass is too low, disabling')
            lowpass = None

    if not(highpass is None) and not(lowpass is None) and highpass>=lowpass:
        # totally blocking all signal
        print('using NULL filter', [highpass, lowpass, order])
        b = np.zeros(order)
        a = np.ones(1)
    elif not(lowpass is None) and (highpass is None):
        print('using lowpass filter', [highpass, lowpass, order])
        b = firwin(order, cutoff = lowpass, window = filtwin, pass_zero = True)
        a = np.ones(1)
    elif not(highpass is None) and (lowpass is None):
        print('using highpass filter', [highpass, lowpass, order])
        b = firwin(order, cutoff = highpass, window = filtwin, pass_zero = False)
        a = np.ones(1)
    elif not(highpass is None) and not(lowpass is None):
        print('using bandpass filter', [highpass, lowpass, order])
        b = firwin(order, cutoff = [highpass, lowpass], window = filtwin, pass_zero = False)
        a = np.ones(1)
    else:
        # no filtering at all
        print('using IDENTITY filter', [highpass, lowpass, order])
        b = np.ones(1)
        a = np.ones(1)

    # initialize the state for the filtering based on the previous data
    if ndim == 1:
        zi = zi = lfiltic(b, a, x, x)
    elif ndim == 2:
        f = lambda x : lfiltic(b, a, x, x)
        zi = np.apply_along_axis(f, axis, x)

    return b, a, zi

####################################################################
def online_filter(b, a, x, axis=-1, zi=[]):
    y, zo = lfilter(b, a, x, axis=axis, zi=zi)
    return y, zo
