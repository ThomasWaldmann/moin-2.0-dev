# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script

    Recreate data from source backend to destination.
    Assumptions:
    - defined user_backend/data_backend in wikiconfig
    - defined user_backend_source/data_backend_source in wikiconfig

    TODO: tests!

    @copyright: 2008 MoinMoin:PawelPacana,
                2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import shutil, sys

from MoinMoin.script import MoinScript, fatal
from MoinMoin.storage.backends import clone

class PluginScript(MoinScript):
    """Backend migration class."""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-v", "--verbose", dest="verbose", action="store_true",
            help="Provide progress information while performing the migration"
        )
        self.parser.add_option(
            "-t", "--type", dest="backend_type",
            help="Migrate specified type of backend: user, data"
        )
        self.parser.add_option(
            "-f", "--fails", dest="show_failed", action="store_true",
            help="Print failed migration items"
        )


    def mainloop(self):
        self.init_request()
        request = self.request
        try:
            if self.options.backend_type == "user":
                dst_backend = request.cfg.user_backend
                src_backend = request.cfg.user_backend_source
            elif self.options.backend_type == "data":
                dst_backend = request.cfg.data_backend
                src_backend = request.cfg.data_backend_source
            else:
                fatal("Please, choose backend type [--type].")
        except AttributeError:
            fatal("Please, configure your %(user)s_backend and %(user)s_backend_source in wikiconfig.py." %
                  {'user': self.options.backend_type})

        cnt, skips, fails = clone(src_backend, dst_backend, self.options.verbose)
        sys.stdout.write("Backend migration finished!\nProcessed revisions: %d >> %d converted, %d skipped, %d failed\n" %
                         (cnt[0] + cnt[1] + cnt[2], cnt[0], cnt[1], cnt[2], ))

        if self.options.show_failed and len(fails):
            sys.stdout.write("\nFailed report\n-------------\n")
            for name in fails.iterkeys():
                sys.stdout.write("%r: %s\n" % (name, fails[name]))

