# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - XML (de)serialization

    TODO: provide fresh backend per test method.

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from StringIO import StringIO

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.memory import MemoryBackend
from MoinMoin.storage.error import ItemAlreadyExistsError
from MoinMoin.conftest import init_test_request

class TestSerializer(object):

    def update_item(self, name, revno, meta, data):
        try:
            item = self.request.data_backend.create_item(name)
        except ItemAlreadyExistsError:
            item = self.request.data_backend.get_item(name)
        rev = item.create_revision(revno)
        for k, v in meta.items():
            rev[k] = v
        rev.write(data)
        item.commit()
        return item

    def test_serialize_rev(self):
        params = ('foo1', 0, dict(m1="m1"), 'bar1')
        item = self.update_item(*params)
        rev = item.get_revision(0)
        xmlfile = StringIO()
        rev.serialize(xmlfile)
        xml = xmlfile.getvalue()
        assert xml == ('<revision revno="0">'
                       '<meta>'
                       '<entry key="m1">m1</entry>'
                       '</meta>'
                       '<data coding="base64"><chunk>YmFyMQ==</chunk></data>'
                       '</revision>')

    def test_serialize_item(self):
        testparams = [
            ('foo2', 0, dict(m1="m1"), 'bar2'),
            ('foo2', 1, dict(m2="m2"), 'baz2'),
        ]
        for params in testparams:
            item = self.update_item(*params)
        xmlfile = StringIO()
        item.serialize(xmlfile)
        xml = xmlfile.getvalue()
        print xml
        assert xml == ('<item name="foo2">'
                       '<meta></meta>'
                       '<revisions>'
                       '<revision revno="0">'
                       '<meta><entry key="m1">m1</entry></meta>'
                       '<data coding="base64"><chunk>YmFyMg==</chunk></data>'
                       '</revision>'
                       '<revision revno="1">'
                       '<meta><entry key="m2">m2</entry></meta>'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk></data>'
                       '</revision>'
                       '</revisions>'
                       '</item>')

    def test_serialize_backend(self):
        testparams = [
            ('foo3', 0, dict(), ''),
            ('bar3', 0, dict(), ''),
        ]
        for params in testparams:
            self.update_item(*params)
        xmlfile = StringIO()
        self.request.data_backend.serialize(xmlfile)
        xml = xmlfile.getvalue()
        print xml
        assert xml == ('<backend namespace="">'
                       '<items>'
                       '<item name="bar3">'
                       '<meta></meta>'
                       '<revisions>'
                       '<revision revno="0">'
                       '<meta></meta>'
                       '<data coding="base64"></data>'
                       '</revision>'
                       '</revisions>'
                       '</item>'
                       '<item name="foo1">'
                       '<meta></meta>'
                       '<revisions><revision revno="0">'
                       '<meta><entry key="m1">m1</entry></meta>'
                       '<data coding="base64"><chunk>YmFyMQ==</chunk></data>'
                       '</revision>'
                       '</revisions>'
                       '</item>'
                       '<item name="foo2">'
                       '<meta></meta>'
                       '<revisions>'
                       '<revision revno="0">'
                       '<meta><entry key="m1">m1</entry></meta>'
                       '<data coding="base64"><chunk>YmFyMg==</chunk></data>'
                       '</revision>'
                       '<revision revno="1">'
                       '<meta><entry key="m2">m2</entry></meta>'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk></data>'
                       '</revision>'
                       '</revisions>'
                       '</item>'
                       '<item name="foo3">'
                       '<meta></meta>'
                       '<revisions>'
                       '<revision revno="0">'
                       '<meta></meta>'
                       '<data coding="base64"></data>'
                       '</revision>'
                       '</revisions>'
                       '</item>'
                       '</items>'
                       '</backend>')


