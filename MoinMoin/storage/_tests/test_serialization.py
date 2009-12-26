# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - XML (de)serialization

    TODO: provide fresh backend per test class (or even per test method?).

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from StringIO import StringIO

from MoinMoin._tests import become_trusted
from MoinMoin.storage.error import ItemAlreadyExistsError
from MoinMoin.storage.serialization import Entry, create_value_object, serialize


def update_item(request, name, revno, meta, data):
    become_trusted(request)
    try:
        item = request.storage.create_item(name)
    except ItemAlreadyExistsError:
        item = request.storage.get_item(name)
    rev = item.create_revision(revno)
    for k, v in meta.items():
        rev[k] = v
    rev.write(data)
    item.commit()
    return item


class TestSerializeRev(object):

    def test_serialize_rev(self):
        params = ('foo1', 0, dict(m1="m1"), 'bar1')
        item = update_item(self.request, *params)
        rev = item.get_revision(0)
        xmlfile = StringIO()
        serialize(rev, xmlfile)
        xml = xmlfile.getvalue()
        assert xml == ('<revision revno="0">'
                       '<meta>'
                       '<entry key="m1"><str>m1</str>\n</entry>\n'
                       '</meta>\n'
                       '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>\n'
                       '</revision>\n')


class TestSerializeItem(object):

    def test_serialize_item(self):
        testparams = [
            ('foo2', 0, dict(m1="m1"), 'bar2'),
            ('foo2', 1, dict(m2="m2"), 'baz2'),
        ]
        for params in testparams:
            item = update_item(self.request, *params)
        xmlfile = StringIO()
        serialize(item, xmlfile)
        xml = xmlfile.getvalue()
        assert xml == ('<item name="foo2">'
                       '<meta></meta>\n'
                       '<revision revno="0">'
                       '<meta><entry key="m1"><str>m1</str>\n</entry>\n</meta>\n'
                       '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>\n'
                       '</revision>\n'
                       '<revision revno="1">'
                       '<meta><entry key="m2"><str>m2</str>\n</entry>\n</meta>\n'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>\n'
                       '</revision>\n'
                       '</item>\n')


class TestSerializeBackend(object):

    def test_serialize_backend(self):
        testparams = [
            ('foo3', 0, dict(m3="m3"), 'bar1'),
            ('foo4', 0, dict(m4="m4"), 'bar2'),
            ('foo4', 1, dict(m4="m4"), 'baz2'),
        ]
        for params in testparams:
            update_item(self.request, *params)
        xmlfile = StringIO()
        serialize(self.request.storage, xmlfile)
        xml = xmlfile.getvalue()
        assert xml.startswith('<backend>')
        assert xml.endswith('</backend>\n')
        assert ('<item name="foo3">'
                '<meta></meta>\n'
                '<revision revno="0">'
                '<meta><entry key="m3"><str>m3</str>\n</entry>\n</meta>\n'
                '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>\n'
                '</revision>\n'
                '</item>') in xml
        assert ('<item name="foo4">'
                '<meta></meta>\n'
                '<revision revno="0">'
                '<meta><entry key="m4"><str>m4</str>\n</entry>\n</meta>\n'
                '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>\n'
                '</revision>\n'
                '<revision revno="1">'
                '<meta><entry key="m4"><str>m4</str>\n</entry>\n</meta>\n'
                '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>\n'
                '</revision>\n'
                '</item>') in xml


class TestSerializer2(object):
    def test_Entry(self):
        test_data = [
            ('foo', 'bar', '<entry key="foo"><str>bar</str>\n</entry>\n'),
            (u'foo', u'bar', '<entry key="foo"><unicode>bar</unicode>\n</entry>\n'),
        ]
        for k, v, expected_xml in test_data:
            e = Entry(k, v)
            xmlfile = StringIO()
            serialize(e, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == expected_xml

    def test_Values(self):
        test_data = [
            ('bar', '<str>bar</str>\n'),
            (u'bar', '<unicode>bar</unicode>\n'),
            (42, '<int>42</int>\n'),
            (True, '<bool>True</bool>\n'),
            (23.42, '<float>23.42</float>\n'),
            (complex(1.2, 2.3), '<complex>(1.2+2.3j)</complex>\n'),
            ((1, 2), '<tuple><int>1</int>\n<int>2</int>\n</tuple>\n'),
            ((1, 'bar'), '<tuple><int>1</int>\n<str>bar</str>\n</tuple>\n'),
            ((1, ('bar', 'baz')), '<tuple><int>1</int>\n<tuple><str>bar</str>\n<str>baz</str>\n</tuple>\n</tuple>\n'),
        ]
        for v, expected_xml in test_data:
            v = create_value_object(v)
            xmlfile = StringIO()
            serialize(v, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == expected_xml

