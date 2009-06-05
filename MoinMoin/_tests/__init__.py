# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - some common code for testing

    @copyright: 2007 MoinMoin:KarolNowak,
                2008 MoinMoin:ThomasWaldmann, MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import os, shutil

from MoinMoin.parser.text import Parser
from MoinMoin.formatter.text_html import Formatter
from MoinMoin.items import Item, ACL
from MoinMoin.util import random_string
from MoinMoin import caching, user
from MoinMoin import config

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

def create_page(request, itemname, content, mimetype='text/moin-wiki', acl=''):
    """ create a page with some content """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(request, itemname)
    meta = {}
    if acl:
        meta[ACL] = acl
    item._save(meta, content, mimetype=mimetype)
    return item

def append_page(request, itemname, content):
    """ appends some content to an existing page """
    if isinstance(content, unicode):
        content = content.encode(config.charset)
    item = Item.create(request, itemname)
    content = "%s\n%s\n"% (item.data, content)
    item._save({}, content)
    return item

def create_random_string_list(length=14, count=10):
    """ creates a list of random strings """
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return [u"%s" % random_string(length, chars) for counter in range(count)]

def make_macro(request, page):
    """ creates the macro """
    from MoinMoin import macro
    p = Parser("##\n", request)
    p.formatter = Formatter(request)
    p.formatter.page = page
    request.page = page
    request.formatter = p.formatter
    p.form = request.form
    m = macro.Macro(p)
    return m
