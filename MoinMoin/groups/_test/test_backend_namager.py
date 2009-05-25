# -*- coding: iso-8859-1 -*-

"""
MoinMoin.groups.BackendManager test

@copyright: 2009 MoinMoin:DmitrijsMilajevs
@license: GPL, see COPYING for details
"""

from py.test import raises

from MoinMoin.groups import BackendManager


class TestBackendManager(object):

    def setup_method(self, method):
        self.admin_group = frozenset([u'Admin', u'JohnDoe'])
        self.editor_group = frozenset([u'MainEditor', u'JohnDoe'])
        self.fruit_group = frozenset([u'Apple', u'Banana'])

        groups = {u'AdminGroup': self.admin_group,
                  u'EditorGroup': self.editor_group,
                  u'FruitGroup': self.fruit_group}

        self.group_backend = BackendManager(backend=groups)

    def test_getitem(self):
        assert self.admin_group == self.group_backend[u'AdminGroup']
        assert self.fruit_group == self.group_backend[u'FruitGroup']

        raises(KeyError, lambda: self.group_backend[u'not existing group'])

    def test_contains(self):
        assert u'AdminGroup' in self.group_backend
        assert u'FruitGroup' in self.group_backend

        assert u'not existing group' not in self.group_backend

    def  test_membergroups(self):
        apple_groups = self.group_backend.membergroups(u'Apple')
        assert 1 == len(apple_groups)
        assert u'FruitGroup' in apple_groups
        assert u'AdminGroup' not in apple_groups

        john_doe_groups = self.group_backend.membergroups(u'JohnDoe')
        assert 2 == len(john_doe_groups)
        assert u'EditorGroup' in john_doe_groups
        assert u'AdminGroup' in john_doe_groups
        assert u'FruitGroup' not in john_doe_groups


coverage_modules = ['MoinMoin.groups']
