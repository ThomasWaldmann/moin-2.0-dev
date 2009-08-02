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
from MoinMoin.storage.backends import memory, flatfile, clone, router

class Config(DefaultConfig):
    sitename = u'Developer Test Wiki'
    logo_string = sitename

    _base_dir = os.path.join(os.path.dirname(__file__), 'wiki')
    data_dir = os.path.join(_base_dir, "data") # needed for plugins package TODO
    flat_dir = os.path.join(os.path.dirname(__file__), 'data')

    USER_PREFIX = 'Users/'
    DATA_PREFIX = 'Content/'
    mapping = [(DATA_PREFIX, memory.MemoryBackend()), (USER_PREFIX, memory.MemoryBackend())]
    storage = router.RouterBackend(mapping, default=DATA_PREFIX)
    def provide_fresh_backends(self):
        mapping = [(DATA_PREFIX, memory.MemoryBackend()), (USER_PREFIX, memory.MemoryBackend())]
        self.storage = memory.MemoryBackend()
        self.test_num_pages = len(clone(flatfile.FlatFileBackend(self.flat_dir), self.storage)[0])

    page_front_page = 'FrontPage'

    #show_hosts = 1

    #secrets = 'some not secret string just to make tests happy'

    # used to check if it is really a wiki we may modify
    is_test_wiki = True

