# -*- coding: iso-8859-1 -*-
"""
MoinMoin - test wiki configuration

@copyright: 2000-2004 by Juergen Hermann <jh@web.de>
@license: GNU GPL, see COPYING for details.
"""

import os
from MoinMoin.config.multiconfig import DefaultConfig
from MoinMoin.storage.backends import memory

class Config(DefaultConfig):
    sitename = u'Developer Test Wiki'
    logo_string = sitename

    _base_dir = os.path.join(os.path.dirname(__file__), 'wiki')
    data_dir = os.path.join(_base_dir, "data") # needed for plugins package
    #data_underlay_dir = os.path.join(_base_dir, "underlay")

    # configure backends
    data_backend = memory.MemoryBackend()
    user_backend = memory.MemoryBackend()


    show_hosts = 1

    secrets = 'some not secret string just to make tests happy'

    # used to check if it is really a wiki we may modify
    is_test_wiki = True
