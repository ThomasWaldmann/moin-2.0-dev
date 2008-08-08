# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - backend migration script
    
    Recreate data from source backend either in data_backend or user_backend.    
    Assumptions:
    - defined user_backend/data_backend in wikiconfig
    - defined migration source backend (default: migration_source in wikiconfig)
    
    TODO: tests

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

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
                rev.keys()  # metadata loaded lazily
                # filter out deprecated meta
                meta = dict(filter(lambda x: x[0] != EDIT_LOG_MTIME, rev.iteritems()))                                
                # this didn't work: new_rev.update(rev)
                new_rev._metadata.update(meta)
                if not new_rev.has_key('__timestamp'):
                    new_rev._metadata['__timestamp'] = rev[EDIT_LOG_MTIME]                   
                new_rev.write(rev.read())
                new_item.commit()

            new_item.change_metadata()  # meta
            for key in item.keys():
                new_item[key] = item[key]
            new_item.publish_metadata()

        for item in src_backend.iteritems():
            clone_item(dst_backend, item)

