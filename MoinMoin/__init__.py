# -*- coding: ascii -*-
"""
MoinMoin - a wiki engine in Python.

@copyright: 2000-2006 by Juergen Hermann <jh@web.de>,
            2002-2011 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import os
import sys

from MoinMoin import log
logging = log.getLogger(__name__)

project = "MoinMoin"

if sys.hexversion < 0x2060000:
    logging.warning("%s requires Python 2.6 or greater." % project)


# XXX temporary sys.path hack for convenience:
support_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'support'))
if support_dir not in sys.path:
    sys.path.insert(0, support_dir)


from MoinMoin.util.version import Version

version = Version(2, 0, 0, 'alpha')

