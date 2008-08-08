# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script

    Recreate data from source backend to destination.
    Assumptions:
    - defined user_backend/data_backend in wikiconfig
    - defined user_backend_source/data_backend_source in wikiconfig

    TODO: tests, case for comparing already existing items (interrupted migration)

    @copyright: 2008 MoinMoin:PawelPacana,
                2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import shutil

from MoinMoin.script import MoinScript, fatal
from MoinMoin.storage.error import NoSuchItemError

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


def clone(src, dst, verbose):
    """
    From a given source backend src, copy all items (including the items metadata),
    and their revisions (including the revisions metadata) into a given destination
    backend dst.
    """
    # For every item in our old backend...
    for old_item in src.iteritems():
        new_item = dst.create_item(old_item.name)

        # ...copy the items metadata...
        new_item.change_metadata()
        for k, v in old_item.iteritems():
            new_item[k] = v
        new_item.publish_metadata()

        # ...copy each revision of that item...
        for revno in old_item.list_revisions():
            old_rev = old_item.get_revision(revno)
            new_rev = new_item.create_revision(revno)

            # ...copy the metadata of the revision...
            for k, v in old_rev.iteritems():
                try:  # XXX Wrong layer to fix this, imho
                    new_rev[k] = v
                except TypeError:
                    new_rev[k] = tuple(v)
            new_rev.timestamp = old_rev.timestamp

            # ... and copy the data of the revision.
            shutil.copyfileobj(old_rev, new_rev)

            new_item.commit()
