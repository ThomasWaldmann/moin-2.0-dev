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

from MoinMoin import caching, config, security, user
from MoinMoin.items import Item, ACL, SOMEDICT, USERGROUP
from MoinMoin.util import random_string
from MoinMoin.storage.error import ItemAlreadyExistsError

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

def create_item(name, content, mimetype='text/x.moin.wiki', meta=None):
    """ create a item with some content """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(name)
    if meta is None:
        meta = {}
    item._save(meta, content, mimetype=mimetype)
    return Item.create(name)

def update_item(name, revno, meta, data):
    try:
        item = flaskg.storage.create_item(name)
    except ItemAlreadyExistsError:
        item = flaskg.storage.get_item(name)
    rev = item.create_revision(revno)
    for k, v in meta.items():
        rev[k] = v
    if not 'name' in rev:
        rev['name'] = name
    if not 'mimetype' in rev:
        rev['mimetype'] = u'application/octet-stream'
    rev.write(data)
    item.commit()
    return item

def append_item(name, content, meta=None):
    """ appends some content to an existing item """
    # require existing item
    assert flaskg.storage.has_item(name)
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = flaskg.storage.get_item(name)
    rev = item.get_revision(-1)
    data = rev.read()
    item_meta = dict(rev)
    if meta is not None:
        for key in meta:
            attr = rev.get(key, {})
            attr.extend(meta[key])
            item_meta[key] = attr
    return update_item(name, rev.revno + 1, item_meta, data + content)

def create_random_string_list(length=14, count=10):
    """ creates a list of random strings """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return [u"%s" % random_string(length, chars) for counter in range(count)]

def nuke_xapian_index():
    """ completely delete everything in xapian index dir """
    fpath = os.path.join(app.cfg.cache_dir, 'xapian')
    if os.path.exists(fpath):
        shutil.rmtree(fpath, True)

def nuke_item(name):
    """ complete destroys an item """
    item = Item.create(name)
    item.destroy()
