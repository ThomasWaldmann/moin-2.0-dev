# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Support Package

    Stuff for python 2.3 compatibility

    @copyright: 2007 Heinrich Wendel <heinrich.wendel@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

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

try:
    set = set
except NameError:
    from sets import Set as set

try:
    from functools import partial
except NameError:
    class partial(object):
        def __init__(*args, **kw):
            self = args[0]
            self.fn, self.args, self.kw = (args[1], args[2:], kw)

        def __call__(self, *args, **kw):
            if kw and self.kw:
                d = self.kw.copy()
                d.update(kw)
            else:
                d = kw or self.kw
            return self.fn(*(self.args + args), **d)
