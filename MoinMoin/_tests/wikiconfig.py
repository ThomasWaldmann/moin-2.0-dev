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
from os.path import abspath, dirname, join
from MoinMoin.config.multiconfig import DefaultConfig

class Config(DefaultConfig):
    sitename = u'Developer Test Wiki'
    logo_string = sitename

    _base_dir = os.path.join(os.path.dirname(__file__), 'wiki')
    data_dir = os.path.join(_base_dir, "data") # needed for plugins package TODO
    _test_items_xml = join(abspath(dirname(__file__)), 'testitems.xml')

    shared_intermap_files = [os.path.join(os.path.dirname(__file__), '..', '..',
                                          'contrib', 'interwiki', 'intermap.txt'), ]

    content_acl = None

    page_front_page = 'FrontPage'

    #show_hosts = 1

    #secrets = 'some not secret string just to make tests happy'

    # used to check if it is really a wiki we may modify
    is_test_wiki = True

