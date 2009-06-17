#!/usr/bin/env python
"""
    Start script for the standalone Wiki server.

    @copyright: 2007 MoinMoin:ForrestVoight
    @license: GNU GPL, see COPYING for details.
"""

import sys, os

# a) Configuration of Python's code search path
#    If you already have set up the PYTHONPATH environment variable for the
#    stuff you see below, you don't need to do a1) and a2).

# a1) Path of the directory where the MoinMoin code package is located.
#     Needed if you installed with --prefix=PREFIX or you didn't use setup.py.
#sys.path.insert(0, 'PREFIX/lib/python2.5/site-packages')

# a2) Path of the directory where wikiconfig.py / farmconfig.py is located.
moinpath = os.path.abspath(os.path.normpath(os.path.dirname(sys.argv[0])))
sys.path.insert(0, moinpath)
os.chdir(moinpath)

# b) Configuration of moin's logging
#    If you have set up MOINLOGGINGCONF environment variable, you don't need this!
#    You also don't need this if you are happy with the builtin defaults.
#    See wiki/config/logging/... for some sample config files.
from MoinMoin import log
log.load_config('wikiserverlogging.conf')

from MoinMoin.script import MoinScript

from create_persistent_dev_wiki import run
def create_if_missing():
    instance = 'instance'
    underlay = 'underlay'

    successfile = os.path.join(instance, '.success')
    if not os.path.isfile(successfile):
        run(instance, underlay)
        successfile = open(successfile, 'w').close()


if __name__ == '__main__':
    sys.argv = ["moin.py", "server", "standalone"]
    try:
        create_if_missing()
    except OSError:
        sys.exit("Conversion of underlay failed. Please remove the instance folder and retry.")
    MoinScript().run()

