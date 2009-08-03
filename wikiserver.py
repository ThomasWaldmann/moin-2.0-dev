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

from wikiconfig import Config

from MoinMoin.i18n.strings import all_pages as item_names

from MoinMoin.storage.error import StorageError
from MoinMoin.storage.backends import memory, clone, enduser
from MoinMoin.storage.serialization import unserialize

def check_backend():
    """
    check if the configured backend has the system pages,
    if it does not, unserialize them from the xml file.
    """
    # XXX
    backend = Config.content_backend
    names = item_names[:]
    # XXX xml file is incomplete, do not check for these pages:
    names.remove('LanguageSetup')
    names.remove('InterWikiMap')
    names.remove('WikiLicense')
    try:
        for name in names:
            item = backend.get_item(name)
            del item
    except StorageError:
        # if there is some exception, we assume that backend needs to be filled
        print "Unserializing system pages..."
        xmlfile = os.path.join(moinpath, 'wiki', 'syspages.xml')
        tmp_backend = memory.MemoryBackend()
        unserialize(tmp_backend, xmlfile)
        clone(tmp_backend, backend, only_these=names)
        print "Unserialization finished."


if __name__ == '__main__':
    check_backend()
    sys.argv = ["moin.py", "server", "standalone"]
    MoinScript().run()

