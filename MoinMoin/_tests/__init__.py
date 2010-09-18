# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - some common code for testing

    @copyright: 2007 MoinMoin:KarolNowak,
                2008 MoinMoin:ThomasWaldmann,
                2008, 2010 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import os, shutil

from flask import current_app as app
from flask import flaskg

from MoinMoin.items import Item, ACL, SOMEDICT, USERGROUP
from MoinMoin.util import random_string
from MoinMoin import user
from MoinMoin import config, security

# Promoting the test user -------------------------------------------
# Usually the tests run as anonymous user, but for some stuff, you
# need more privs...

def become_valid(username=u"ValidUser"):
    """ modify flaskg.user to make the user valid.
        Note that a valid user will only be in ACL special group "Known", if
        we have a user profile for this user as the ACL system will check if
        there is a userid for this username.
        Thus, for testing purposes (e.g. if you need delete rights), it is
        easier to use become_trusted().
    """
    flaskg.user.name = username
    flaskg.user.may.name = username
    flaskg.user.valid = 1


def become_trusted(username=u"TrustedUser"):
    """ modify flaskg.user to make the user valid and trusted, so it is in acl group Trusted """
    become_valid(username)
    flaskg.user.auth_method = app.cfg.auth_methods_trusted[0]


def become_superuser(username=u"SuperUser"):
    """ modify flaskg.user so it is in the superuser list,
        also make the user valid (see notes in become_valid()),
        also make the user trusted (and thus in "Trusted" ACL pseudo group).

        Note: being superuser is completely unrelated to ACL rights,
              especially it is not related to ACL admin rights.
    """
    become_trusted(username)
    if username not in app.cfg.superuser:
        app.cfg.superuser.append(username)

# Creating and destroying test items --------------------------------

def create_item(itemname, content, mimetype='text/x.moin.wiki', acl=None,
                somedict=None, groupmember=None):
    """ create a item with some content """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(itemname)
    meta = {}
    if acl is not None:
        meta[ACL] = acl
    if somedict is not None:
        meta[SOMEDICT] = somedict
    if groupmember is not None:
        meta[USERGROUP] = groupmember
    item._save(meta, content, mimetype=mimetype)
    return Item.create(itemname)

def append_item(itemname, content, groupmember=None):
    """ appends some content to an existing item """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    meta = {}
    if flaskg.storage.has_item(itemname):
        item = flaskg.storage.get_item(itemname)
        rev = item.get_revision(-1)
        group = rev.get(USERGROUP, {})
        mimetype = rev.get("mimetype", {})
    if groupmember is not None:
        item = Item.create(itemname)
        group.extend(groupmember)
        meta[USERGROUP] = group

    item._save(meta, content, mimetype=mimetype)
    return Item.create(itemname)

def create_random_string_list(length=14, count=10):
    """ creates a list of random strings """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return [u"%s" % random_string(length, chars) for counter in range(count)]

def nuke_xapian_index():
    """ completely delete everything in xapian index dir """
    fpath = app.cfg.xapian_index_dir
    if os.path.exists(fpath):
        shutil.rmtree(fpath, True)

def nuke_item(item_name):
    """ complete destroys an item """
    item = Item.create(item_name)
    item.destroy()
