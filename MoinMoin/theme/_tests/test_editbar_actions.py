# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.theme Tests

    @copyright: 2008 MoinMoin:ReimarBauer,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from flask import current_app as app

from flask import flaskg

from MoinMoin.theme import ThemeBase
from MoinMoin.Page import Page


class TestEditBarActions(object):
    #TODO: Made new tests for new ThemeBase

    def setup_method(self, method):
        self.savedValid = flaskg.user.valid
        self.savedMailEnabled = app.cfg.mail_enabled
        app.cfg.mail_enabled = True
        self.page = Page(self.request, u'FrontPage')
        self.ThemeBase = ThemeBase()

    def teardown_method(self, method):
        flaskg.user.valid = self.savedValid
        app.cfg.mail_enabled = self.savedMailEnabled

    def test_editbar_for_anonymous_user(self):
        assert not flaskg.user.valid
        #assert not self.ThemeBase.subscribeLink(self.page)
        #assert not self.ThemeBase.quicklinkLink(self.page)

    def test_editbar_for_valid_user(self):
        flaskg.user.valid = True
        assert flaskg.user.valid
        #assert 'subscribe' in self.ThemeBase.subscribeLink(self.page)
        #assert 'quicklink' in self.ThemeBase.quicklinkLink(self.page)

coverage_modules = ['MoinMoin.theme']
