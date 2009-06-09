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
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.util import random_string
from MoinMoin import caching, user

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

def create_page(request, pagename, content, do_editor_backup=False):
    """ create a page with some content """
    # create page from scratch:
    page = PageEditor(request, pagename, do_editor_backup=do_editor_backup)
    try:
        page.saveText(content, None)
    except PageEditor.Unchanged:
        pass
    return page

def append_page(request, pagename, content, do_editor_backup=False):
    """ appends some conetent to an existing page """
    # reads the raw text of the existing page
    raw = Page(request, pagename).get_raw_body()
    # adds the new content to the old
    content = "%s\n%s\n"% (raw, content)
    page = PageEditor(request, pagename, do_editor_backup=do_editor_backup)
    page.saveText(content, None)
    return page

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
