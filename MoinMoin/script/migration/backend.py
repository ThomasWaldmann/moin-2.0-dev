# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script

    Recreate data from source backend either in data_backend or user_backend.
    Assumptions:
    - defined user_backend/data_backend in wikiconfig
    - defined migration source backend (default: migration_source in wikiconfig)

    TODO: tests, case for comparing already existing items (interrupted migration)

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

import shutil

from MoinMoin.script import MoinScript, fatal
from MoinMoin.storage import EDIT_LOG_MTIME


class PluginScript(MoinScript):
    """Backend migration class."""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-t", "--type", dest="backend_type",
            help="Migrate specified type of backend: user, data"
        )
        self.parser.add_option(
            "-s", "--source", dest="source_backend", default='migration_source',
            help="Specify source of migration."
        )

    def mainloop(self):
        self.init_request()
        request = self.request
        if self.options.backend_type == "user":
            dst_backend = request.cfg.user_backend
        elif self.options.backend_type == "data":
            dst_backend = request.cfg.data_backend
        else:
            fatal("Please, choose backend type [--type].")
        src = self.options.source_backend
        try:
            src_backend = getattr(request.cfg, src)
        except AttributeError:
            fatal("No such source backend: %s" % src)

        def clone_item(backend, item):
            new_item = backend.create_item(item.name)
            for revno in item.list_revisions():  # revs
                rev, new_rev = item.get_revision(revno), new_item.create_revision(revno)
                for k, v in rev.iteritems():
                    try:
                        new_rev[k] = v
                    except TypeError:
                        new_rev[k] = tuple(v)  # list to tuple
                if not new_rev._metadata.has_key('__timestamp'):  # __key not accessible through public API
                    new_rev._metadata['__timestamp'] = rev[EDIT_LOG_MTIME]
                shutil.copyfileobj(rev, new_rev)
                new_item.commit()

            new_item.change_metadata()  # meta
            for key in item.keys():
                new_item[key] = item[key]
            new_item.publish_metadata()

        for item in src_backend.iteritems():
            clone_item(dst_backend, item)

