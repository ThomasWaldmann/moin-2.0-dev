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


def clone(src, dst):
    """Clone items from source into destination backend with revision creation order preservation."""
    revs = []
    for item in src.iteritems():
        for revno in item.list_revisions():
            rev = item.get_revision(revno)
            revs.append((rev.timestamp, rev.revno, item.name, ))
    revs.sort()

    for revitem in revs:
        timestamp, revno, name = revitem
        item = src.get_item(name)
        try:
            new_item = dst.get_item(name)
        except NoSuchItemError:
            new_item = dst.create_item(name)
            new_item.change_metadata()
            for k, v in item.iteritems():
                new_item[k] = v
            new_item.publish_metadata()

        new_rev = new_item.create_revision(revno)
        new_rev.timestamp = timestamp
        revision = item.get_revision(revno)
        for k, v in revision.iteritems():
            try:
                new_rev[k] = v
            except TypeError:
                new_rev[k] = tuple(v)
        shutil.copyfileobj(revision, new_rev)
        new_item.commit()

