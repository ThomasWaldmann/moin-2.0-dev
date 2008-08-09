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

import shutil

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
        if self.options.verbose:
            from MoinMoin import log
            logging = log.getLogger(__name__)
            logging.info("Processed: %d >> %d skipped, %d failed" % (cnt, len(skips), len(fails), ))
            # TODO: one can add verbosity level to show failed pages

