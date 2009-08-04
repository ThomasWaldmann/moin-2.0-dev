# -*- coding: iso-8859-1 -*-
"""MoinMoin Desktop Edition (MMDE) - Configuration

ONLY to be used for MMDE - if you run a personal wiki on your notebook or PC.

This is NOT intended for internet or server or multiuser use due to relaxed security settings!
"""

import sys, os

from MoinMoin.config import multiconfig, url_prefix_static
from MoinMoin.storage.backends import fs


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
    #instance_dir = '/where/ever/your/instance/is'
    instance_dir = os.path.join(wikiconfig_dir, 'wiki')

    preloaded_xml = os.path.join(instance_dir, 'syspages.xml')

    data_dir = os.path.join(instance_dir, 'data') # Note: this used to have a trailing / in the past

    #backend_uri = 'fs:instance'
    content_backend = fs.FSBackend(os.path.join(data_dir, 'content'))
    user_profile_backend = fs.FSBackend(os.path.join(data_dir, 'userprofiles'))
    trash_backend = fs.FSBackend(os.path.join(data_dir, 'trash'))
    content_acl = dict(
        before="",
        default="All:read,write,admin,create,destroy", # MMDE -> superpowers by default
        after="",
        hierarchic=False,
    )
    user_profile_acl = dict(
        before="All:read,write,admin,create,destroy", # TODO: change this before release, just for development
        default="",
        after="",
        hierarchic=False,
    )
    namespace_mapping = [
            # order of list entries is important, first prefix match wins
            # (prefix, unprotected backend, protection to be applied as dict)
            ('Trash', trash_backend, content_acl),  # trash bin for "deleted" items
            ('UserProfile', user_profile_backend, user_profile_acl),  # user profiles / accounts
            ('', content_backend, content_acl),  # '' (wiki content) - must be LAST entry!
    ]

    DesktopEdition = True # give all local users full powers
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

