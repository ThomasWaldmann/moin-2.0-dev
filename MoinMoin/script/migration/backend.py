# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script

    Recreate data from source backend to destination.
    Assumptions:
    - defined user_backend/data_backend in wikiconfig
    - defined user_backend_source/data_backend_source in wikiconfig

    TODO: tests, case for comparing already existing items (interrupted migration)

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

import shutil

from MoinMoin.script import MoinScript, fatal


class PluginScript(MoinScript):
    """Backend migration class."""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
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
        clone(src_backend, dst_backend)


def clone(source, destination):
    """Clone items from source into destination backend."""
    def clone_item(backend, item):
        new_item = backend.create_item(item.name)
        for revno in item.list_revisions():  # revs
            rev, new_rev = item.get_revision(revno), new_item.create_revision(revno)
            for k, v in rev.iteritems():
                try:
                    new_rev[k] = v
                except TypeError:
                    new_rev[k] = tuple(v)  # list to tuple
            new_rev.timestamp = rev.timestamp
            shutil.copyfileobj(rev, new_rev)
            new_item.commit()

        new_item.change_metadata()  # meta
        for key in item.keys():
            new_item[key] = item[key]
        new_item.publish_metadata()

    for item in source.iteritems():
        clone_item(destination, item)

