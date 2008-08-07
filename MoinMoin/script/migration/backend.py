# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script


    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.script import MoinScript

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
        if self.options.backend_type == "user":
            src_backend = request.cfg.user_backend
        elif self.options.backend_type == "data":
            src_backend = request.cfg.data_backend

        # XXX: how to sanely define destination with all possible
        # different config options?
        # and what about migrating to/from MemoryBackend
        dst_backend = request.cfg.migration_backend

        def clone_item(backend, item):
            new_item = backend.create_item(item.name)
            for revno in item.list_revisions():  # revs
                new_rev, rev = new_item.create_revision(revno), item.get_revision(revno)
                rev.keys()  # loaded lazily
                new_rev.update(rev)
                new_rev.write(rev.read())
                new_item.commit()

            new_item.change_metadata()  # meta
            for key in item.keys():
                new_item[key] = item[key]
            new_item.publish_metadata()

        for item in src_backend.iteritems():
            clone_item(dst_backend, item)

