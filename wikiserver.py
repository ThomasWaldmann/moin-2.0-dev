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

import tarfile
from shutil import rmtree
from wikiconfig import LocalConfig
from migrate_old_wiki_data import run
from MoinMoin.i18n.strings import all_pages as only_these
def create_if_missing():
    successfile = '.success_creating_dev_wiki'
    if not os.path.isfile(successfile):
        print "Untaring underlay. This may take a while..."
        wiki_folder = 'wiki'
        tar = tarfile.open(os.path.join(wiki_folder, 'underlay.tar'))
        tar.extractall(wiki_folder)
        tar.close()

        underlay_folder = os.path.join(wiki_folder, 'underlay')
        # For our simple dev wiki we fool the conversion script by adding an empty user folder.
        try:
            os.mkdir(os.path.join(underlay_folder, 'user'))
        except OSError:
            pass
        run(underlay_folder, LocalConfig.backend_uri, only_these)
        successfile = open(successfile, 'w').close()
        rmtree(underlay_folder)


if __name__ == '__main__':
    sys.argv = ["moin.py", "server", "standalone"]
    try:
        create_if_missing()
    except OSError, e:
        print e
        sys.exit("Conversion of underlay failed. Please remove the instance folder and retry.")
    MoinScript().run()

