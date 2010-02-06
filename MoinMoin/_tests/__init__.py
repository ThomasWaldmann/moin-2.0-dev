# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - some common code for testing

    @copyright: 2007 MoinMoin:KarolNowak,
                2008 MoinMoin:ThomasWaldmann, MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import os, shutil

from MoinMoin.formatter.text_html import Formatter
from MoinMoin.items import Item, ACL
from MoinMoin.util import random_string
from MoinMoin import caching, user
from MoinMoin import config, security

# Promoting the test user -------------------------------------------
# Usually the tests run as anonymous user, but for some stuff, you
# need more privs...

def become_valid(request, username=u"ValidUser"):
    """ modify request.user to make the user valid.
        Note that a valid user will only be in ACL special group "Known", if
        we have a user profile for this user as the ACL system will check if
        there is a userid for this username.
        Thus, for testing purposes (e.g. if you need delete rights), it is
        easier to use become_trusted().
    """
    request.user.name = username
    request.user.may.name = username
    request.user.valid = 1


def become_trusted(request, username=u"TrustedUser"):
    """ modify request.user to make the user valid and trusted, so it is in acl group Trusted """
    become_valid(request, username)
    request.user.auth_method = request.cfg.auth_methods_trusted[0]


def become_superuser(request):
    """ modify request.user so it is in the superuser list,
        also make the user valid (see notes in become_valid()),
        also make the user trusted (and thus in "Trusted" ACL pseudo group).

        Note: being superuser is completely unrelated to ACL rights,
              especially it is not related to ACL admin rights.
    """
    su_name = u"SuperUser"
    become_trusted(request, su_name)
    if su_name not in request.cfg.superuser:
        request.cfg.superuser.append(su_name)

# Creating and destroying test pages --------------------------------

def create_item(request, itemname, content, mimetype='text/moin-wiki', acl=None):
    """ create a page with some content """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(request, itemname)
    meta = {}
    if acl is not None:
        meta[ACL] = acl
    item._save(meta, content, mimetype=mimetype)
    return Item.create(request, itemname)

def append_item(request, itemname, content):
    """ appends some content to an existing page """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(request, itemname)
    content = "%s\n%s\n"% (item.data, content)
    item._save({}, content)
    return Item.create(request, itemname)

def create_random_string_list(length=14, count=10):
    """ creates a list of random strings """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return [u"%s" % random_string(length, chars) for counter in range(count)]

def make_macro(request, page):
    """ creates the macro """

    class _PseudoParser(object):
        def __init__(self, request, formatter):
            self.request, self.formatter = request, formatter
            self.form = request.form

    from MoinMoin import macro
    from MoinMoin.formatter.text_html import Formatter
    p = _PseudoParser(self.request, Formatter(self.request))
    p.formatter.page = self.page
    self.request.formatter = p.formatter
    m = macro.Macro(p)
    return m

def nuke_xapian_index(request):
    """ completely delete everything in xapian index dir """
    fpath = os.path.join(request.cfg.cache_dir, 'xapian')
    if os.path.exists(fpath):
        shutil.rmtree(fpath, True)

def nuke_item(request, item_name):
    """ complete destroys an item """
    item = Item.create(request, item_name)
    item.destroy()
