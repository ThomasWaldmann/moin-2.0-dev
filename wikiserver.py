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

import gzip
from StringIO import StringIO
from wikiconfig import LocalConfig
from MoinMoin.i18n.strings import all_pages as only_these
from MoinMoin.storage.backends import memory, clone, enduser
from MoinMoin.storage.serialization import unserialize
def create_if_missing():
    successfile = '.success_creating_dev_wiki'
    if not os.path.isfile(successfile):
        print "Decompressing system pages. This may take a while..."
        wiki_folder = 'wiki'
        f = gzip.open(os.path.join(wiki_folder, 'syspages.xml.gz'))
        data = StringIO(f.read())
        f.close()
        backend = memory.MemoryBackend()
        unserialize(backend, data)
        destination_backend = enduser.get_enduser_backend(LocalConfig.backend_uri)
        clone(backend, destination_backend, only_these=only_these)
        successfile = open(successfile, 'w').close()
        print "Conversion succeeded."


if __name__ == '__main__':
    sys.argv = ["moin.py", "server", "standalone"]
    try:
        create_if_missing()
    except OSError, e:
        print e
        sys.exit("Conversion of underlay failed. Please remove the instance folder and retry.")
    MoinScript().run()

