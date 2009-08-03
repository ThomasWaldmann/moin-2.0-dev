# -*- coding: iso-8859-1 -*-
"""
MoinMoin - test wiki configuration

Do not change any values without good reason.

We mostly want to have default values here, except for stuff that doesn't
work without setting them (like data_dir).

@copyright: 2000-2004 by Juergen Hermann <jh@web.de>
@license: GNU GPL, see COPYING for details.
"""

import os
from MoinMoin.config.multiconfig import DefaultConfig
from MoinMoin.storage.backends import flatfile, clone, enduser, memory

class Config(DefaultConfig):
    sitename = u'Developer Test Wiki'
    logo_string = sitename

    _base_dir = os.path.join(os.path.dirname(__file__), 'wiki')
    data_dir = os.path.join(_base_dir, "data") # needed for plugins package TODO
    flat_dir = os.path.join(os.path.dirname(__file__), 'data')

    # configure backends
    class DummyStorage(object):
        # This is neccessary so the 'if not request.cfg.storage' test in conftest.py can succeed...
        def __nonzero__(self):
            return False
        def get_backend(self, prefix):
            return None
    storage = DummyStorage()
    default = 'All:read,write,destroy,create,admin'
    namespace_mapping = [('/', memory.MemoryBackend(), {'default': default}), ]
    def provide_fresh_backends(self):
        self.namespace_mapping = [('/', memory.MemoryBackend(), {'default': self.default}), ]
        self.storage = enduser.get_enduser_backend('memory:')
        self.test_num_pages = len(clone(flatfile.FlatFileBackend(self.flat_dir), self.storage)[0])

    page_front_page = 'FrontPage'

    #show_hosts = 1

    #secrets = 'some not secret string just to make tests happy'

    # used to check if it is really a wiki we may modify
    is_test_wiki = True

