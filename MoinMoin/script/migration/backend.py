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
from operator import attrgetter

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


def clone(src, dst):
    """Clone items from source into destination backend with revision creation order preservation."""
    revs = []
    for item in src.iteritems():
        revs.extend([item.get_revision(revno) for revno in item.list_revisions()])
    revs.sort(key = attrgetter("timestamp"))
    for revision in revs:
        name = revision.item.name
        if revision.revno == 0:  # first rev, create item
            new_item = dst.create_item(name)
            new_item.change_metadata()
            for key in item.iterkeys():
                new_item[key] = revision.item[key]
            new_item.publish_metadata()
        else:
            new_item = dst.get_item(name)
        new_rev = new_item.create_revision(revision.revno)
        new_rev.timestamp = revision.timestamp
        for k, v in revision.iteritems():
            try:
                new_rev[k] = v
            except TypeError:
                new_rev[k] = tuple(v)
        shutil.copyfileobj(revision, new_rev)
        new_item.commit()

