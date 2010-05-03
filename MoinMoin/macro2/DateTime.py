# -*- coding: iso-8859-1 -*-
"""
    MoinMoin DateTime macro - outputs the date and time for some specific point in time,
    adapted to the TZ settings of the user viewing the content.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details
"""

from MoinMoin.macro2.Date import MacroDateTimeBase

class Macro(MacroDateTimeBase):
    def macro(self, stamp=None):
        tm = self.parse_time(stamp)
        return self.request.user.getFormattedDateTime(tm)

