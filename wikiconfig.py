# -*- coding: iso-8859-1 -*-
"""MoinMoin Desktop Edition (MMDE) - Configuration

ONLY to be used for MMDE - if you run a personal wiki on your notebook or PC.

This is NOT intended for internet or server or multiuser use due to relaxed security settings!
"""

import sys, os

from MoinMoin.config import multiconfig, url_prefix_static
from MoinMoin.storage.backends import create_simple_mapping


class LocalConfig(multiconfig.DefaultConfig):
    # vvv DON'T TOUCH THIS EXCEPT IF YOU KNOW WHAT YOU DO vvv
    # Directory containing THIS wikiconfig:
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))

    # We assume this structure for a simple "unpack and run" scenario:
    # wikiconfig.py
    # wiki/
    #      data/
    #      syspages.xml
    # If that's not true, feel free to just set instance_dir to the real path
    # where data/ and syspages.xml is located:
    # instance_dir = '/where/ever/your/instance/is'
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')
    data_dir = os.path.join(instance_dir, 'data') # Note: this used to have a trailing / in the past

    # This puts the contents from the specified xml file (a serialized backend) into your
    # backend(s). You can remove this after the first request to your wiki or
    # from the beginning if you don't want to use this feature at all.
    load_xml = os.path.join(instance_dir, 'preloaded_items.xml')
    #save_xml = os.path.join(instance_dir, 'saved_items.xml')

    # This provides a simple default setup for your backend configuration.
    # 'fs:' indicates that you want to use the filesystem backend. You can also use
    # 'hg:' instead to indicate that you want to use the mercurial backend.
    # Alternatively you can set up the mapping yourself (see HelpOnStorageConfiguration).
    namespace_mapping, router_index_uri = create_simple_mapping(
                            backend_uri='fs2:%s/%%(nsname)s' % data_dir,
                            # XXX we use rather relaxed ACLs for the development wiki:
                            content_acl=dict(before=u'',
                                             default=u'All:read,write,create,destroy,admin',
                                             after=u'', ),
                            user_profile_acl=dict(before=u'',
                                             default=u'All:read,write,create,destroy,admin',
                                             after=u'', ),
                            )

    DesktopEdition = True # treat all local users like superuser
    surge_action_limits = None # no surge protection
    sitename = u'MoinMoin DesktopEdition'
    logo_string = u'<img src="%s/common/moinmoin.png" alt="MoinMoin Logo">' % url_prefix_static
    # ^^^ DON'T TOUCH THIS EXCEPT IF YOU KNOW WHAT YOU DO ^^^

    #page_front_page = u'FrontPage' # change to some better value

    # Add your configuration items here.
    secrets = 'This string is NOT a secret, please make up your own, long, random secret string!'

# DEVELOPERS! Do not add your configuration items there,
# you could accidentally commit them! Instead, create a
# wikiconfig_local.py file containing this:
#
# from wikiconfig import LocalConfig
#
# class Config(LocalConfig):
#     configuration_item_1 = 'value1'
#

try:
    from wikiconfig_local import Config
except ImportError, err:
    if not str(err).endswith('wikiconfig_local'):
        raise
    Config = LocalConfig

