# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - XML (de)serialization

    TODO: provide fresh backend per test method.

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from StringIO import StringIO

from MoinMoin.storage.error import ItemAlreadyExistsError
from MoinMoin.conftest import init_test_request
from MoinMoin.storage.serialization import Entry, create_value_object, serialize

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
        serialize(rev, xmlfile)
        xml = xmlfile.getvalue()
        assert xml == ('<revision revno="0">'
                       '<meta>'
                       '<entry key="m1"><str>m1</str></entry>'
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
        serialize(item, xmlfile)
        xml = xmlfile.getvalue()
        print xml
        assert xml == ('<item name="foo2">'
                       '<meta></meta>'
                       '<revision revno="0">'
                       '<meta><entry key="m1"><str>m1</str></entry></meta>'
                       '<data coding="base64"><chunk>YmFyMg==</chunk></data>'
                       '</revision>'
                       '<revision revno="1">'
                       '<meta><entry key="m2"><str>m2</str></entry></meta>'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk></data>'
                       '</revision>'
                       '</item>')

    def test_serialize_backend(self):
        testparams = [
            ('foo3', 0, dict(), ''),
            ('bar3', 0, dict(), ''),
        ]
        for params in testparams:
            self.update_item(*params)
        xmlfile = StringIO()
        serialize(self.request.data_backend, xmlfile)
        xml = xmlfile.getvalue()
        print xml
        assert xml == ('<backend>'
                       '<item name="bar3">'
                       '<meta></meta>'
                       '<revision revno="0">'
                       '<meta></meta>'
                       '<data coding="base64"></data>'
                       '</revision>'
                       '</item>'
                       '<item name="foo1">'
                       '<meta></meta>'
                       '<revision revno="0">'
                       '<meta><entry key="m1"><str>m1</str></entry></meta>'
                       '<data coding="base64"><chunk>YmFyMQ==</chunk></data>'
                       '</revision>'
                       '</item>'
                       '<item name="foo2">'
                       '<meta></meta>'
                       '<revision revno="0">'
                       '<meta><entry key="m1"><str>m1</str></entry></meta>'
                       '<data coding="base64"><chunk>YmFyMg==</chunk></data>'
                       '</revision>'
                       '<revision revno="1">'
                       '<meta><entry key="m2"><str>m2</str></entry></meta>'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk></data>'
                       '</revision>'
                       '</item>'
                       '<item name="foo3">'
                       '<meta></meta>'
                       '<revision revno="0">'
                       '<meta></meta>'
                       '<data coding="base64"></data>'
                       '</revision>'
                       '</item>'
                       '</backend>')


class TestSerializer2(object):
    def test_Entry(self):
        test_data = [
            ('foo', 'bar', '<entry key="foo"><str>bar</str></entry>'),
            (u'foo', u'bar', '<entry key="foo"><unicode>bar</unicode></entry>'),
        ]
        for k, v, expected_xml in test_data:
            e = Entry(k, v)
            xmlfile = StringIO()
            serialize(e, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == expected_xml

    def test_Values(self):
        test_data = [
            ('bar', '<str>bar</str>'),
            (u'bar', '<unicode>bar</unicode>'),
            (42, '<int>42</int>'),
            (True, '<bool>True</bool>'),
            (23.42, '<float>23.42</float>'),
            (complex(1.2, 2.3), '<complex>(1.2+2.3j)</complex>'),
            ((1, 2), '<tuple><int>1</int><int>2</int></tuple>'),
            ((1, 'bar'), '<tuple><int>1</int><str>bar</str></tuple>'),
            ((1, ('bar', 'baz')), '<tuple><int>1</int><tuple><str>bar</str><str>baz</str></tuple></tuple>'),
        ]
        for v, expected_xml in test_data:
            v = create_value_object(v)
            xmlfile = StringIO()
            serialize(v, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == expected_xml

