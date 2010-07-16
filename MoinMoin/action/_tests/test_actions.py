# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - Actions

    This defines tests for the Actions.

    @copyright: 2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.wsgiapp import handle_action
from MoinMoin.storage.backends.memory import MemoryBackend

class TestActions(object):

    def create_backend(self):
        return MemoryBackend()

    def setup_method(self, method):
        self.user = self.request.user
        self.backend = self.create_backend()
        item = self.backend.create_item('Foo')
        item.create_revision(0)
        item.commit()

    def test_subscribe(self):
        handle_action(self.request, 'Foo', 'subscribe')

    def test_show(self):
        handle_action(self.request, 'Foo', 'show')

    def test_login(self):
        handle_action(self.request, 'Foo', 'login')

    def test_fullsearch(self):
        handle_action(self.request, 'Foo', 'fullsearch')

    def test_sisterpages(self):
        handle_action(self.request, 'Foo', 'sisterpages')

    def test_rc(self):
        handle_action(self.request, 'Foo', 'rc')

    def test_userprofile(self):
        handle_action(self.request, 'Foo', 'userprofile')

    def test_quicklink(self):
        handle_action(self.request, 'Foo', 'quicklink')

    def test_quickunlink(self):
        handle_action(self.request, 'Foo', 'quickunlink')

    def test_syspages_upgrade(self):
        handle_action(self.request, 'Foo', 'syspages_upgrade')

coverage_modules = ['MoinMoin.actions']
