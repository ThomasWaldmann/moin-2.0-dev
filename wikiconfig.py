# -*- coding: iso-8859-1 -*-
"""MoinMoin Desktop Edition (MMDE) - Configuration

ONLY to be used for MMDE - if you run a personal wiki on your notebook or PC.

This is NOT intended for internet or server or multiuser use due to relaxed security settings!
"""

import sys, os

from MoinMoin.config import multiconfig, url_prefix_static
from MoinMoin.storage.backends import fs, router, acl


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

    preloaded_xml = "wiki/syspages.xml"

    #backend_uri = 'fs:instance'
    content_backend = fs.FSBackend('instance/data')
    user_profile_backend = fs.FSBackend('instance/user')
    content_acl = dict(
        hierarchic=False,
        before="TheAdmin:read,write,destroy,create,admin",
        default="All:read,write,create",
        after=""
    )
    user_profile_acl = dict(
        hierarchic=False,
        before="TheAdmin:read,write,destroy,create,admin",
        default="All:",
        after="",
    )
    namespace_mapping = ([
            # (prefix, unprotected backend, protection to be applied), order of list entries is important

            # talk/discussion/supplementation pages, use e.g. content_acl for it:
            #('Talk', talk_backend, acl(request, talk_backend, **content_acl)),
            # trashed pages, use e.g. content_acl for it:
            #('Trash', trash_backend, acl(request, trash_backend, **content_acl)),

            # User homepages, use a relaxed acl (secpol!?) for them, giving special
            # powers when username == pagename:
            #('User', user_homepage_backend, acl(request, user_homepage_backend, **user_homepage_acl)),

            # User profiles: noone except superuser and moin internally should be able to access:
            ('UserProfile', user_profile_backend, user_profile_acl),

            # the fileserver backend is just read-only, we use a simple fs_acl to enforce that:
            #('FS', fileserver_backend, acl(request, fileserver_backend, before="All:read")),
            # IMPORTANT: the default content_backend needs to be mapped to '' and be the LAST ENTRY, use the usual content_acl for it:
            ('', content_backend, content_acl),
        ])

    # Where your own wiki pages are (make regular backups of this directory):
    data_dir = os.path.join(instance_dir, 'data', '') # path with trailing /

    DesktopEdition = True # give all local users full powers
    acl_rights_default = u"All:read,write,delete,create,admin"
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

