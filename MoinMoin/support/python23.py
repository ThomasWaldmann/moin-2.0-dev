# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Support Package

    Stuff for python 2.3 compatibility

    @copyright: 2007 Heinrich Wendel <heinrich.wendel@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

import __builtin__

try:
    sorted = sorted
except NameError:
    def sorted(l, *args, **kw):
        if type(l) == dict:
            l = l.keys()
        l = l[:]
        # py2.3 is a bit different
        if 'cmp' in kw:
            args = (kw['cmp'], )

        l.sort(*args)
        return l
    __builtin__.sorted = sorted

try:
    set = set
except NameError:
    from sets import Set as set
    __builtin__.set = set
