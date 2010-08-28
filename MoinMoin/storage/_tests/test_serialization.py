# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - XML (de)serialization

    TODO: provide fresh backend per test class (or even per test method?).
    TODO: use xpath for testing (or any other way so sequence of metadata
          keys does not matter)

    @copyright: 2009-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from StringIO import StringIO

from flask import flaskg

from MoinMoin._tests import become_trusted
from MoinMoin.storage.error import ItemAlreadyExistsError
from MoinMoin.storage.serialization import Entry, create_value_object, serialize, unserialize

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'

def update_item(request, name, revno, meta, data):
    become_trusted(request)
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


class TestSerializeRev(object):

    def test_serialize_rev(self):
        params = (u'foo1', 0, dict(m1=u"m1"), 'bar1')
        item = update_item(self.request, *params)
        rev = item.get_revision(0)
        xmlfile = StringIO()
        serialize(rev, xmlfile)
        xml = xmlfile.getvalue()
        assert xml == (XML_DECL +
                       '<revision revno="0">'
                       '<meta>'
                       '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                       '<entry key="m1"><str>m1</str>\n</entry>\n'
                       '<entry key="name"><str>foo1</str>\n</entry>\n'
                       '</meta>\n'
                       '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>\n'
                       '</revision>\n')


class TestSerializeItem(object):

    def test_serialize_item(self):
        testparams = [
            (u'foo2', 0, dict(m1=u"m1r0"), 'bar2'),
            (u'foo2', 1, dict(m1=u"m1r1"), 'baz2'),
        ]
        for params in testparams:
            item = update_item(self.request, *params)
        xmlfile = StringIO()
        serialize(item, xmlfile)
        xml = xmlfile.getvalue()
        assert xml == (XML_DECL +
                       '<item name="foo2">'
                       '<meta></meta>\n'
                       '<revision revno="0">'
                       '<meta>'
                       '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                       '<entry key="m1"><str>m1r0</str>\n</entry>\n'
                       '<entry key="name"><str>foo2</str>\n</entry>\n'
                       '</meta>\n'
                       '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>\n'
                       '</revision>\n'
                       '<revision revno="1">'
                       '<meta>'
                       '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                       '<entry key="m1"><str>m1r1</str>\n</entry>\n'
                       '<entry key="name"><str>foo2</str>\n</entry>\n'
                       '</meta>\n'
                       '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>\n'
                       '</revision>\n'
                       '</item>\n')


class TestSerializeBackend(object):

    def test_serialize_backend(self):
        testparams = [
            (u'foo3', 0, dict(m1=u"m1r0foo3"), 'bar1'),
            (u'foo4', 0, dict(m1=u"m1r0foo4"), 'bar2'),
            (u'foo4', 1, dict(m1=u"m1r1foo4"), 'baz2'),
        ]
        for params in testparams:
            update_item(self.request, *params)
        xmlfile = StringIO()
        serialize(flaskg.storage, xmlfile)
        xml = xmlfile.getvalue()
        assert xml.startswith(XML_DECL + '<backend>')
        assert xml.endswith('</backend>\n')
        assert ('<item name="foo3">'
                '<meta></meta>\n'
                '<revision revno="0">'
                '<meta>'
                '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                '<entry key="m1"><str>m1r0foo3</str>\n</entry>\n'
                '<entry key="name"><str>foo3</str>\n</entry>\n'
                '</meta>\n'
                '<data coding="base64"><chunk>YmFyMQ==</chunk>\n</data>\n'
                '</revision>\n'
                '</item>') in xml
        assert ('<item name="foo4">'
                '<meta></meta>\n'
                '<revision revno="0">'
                '<meta>'
                '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                '<entry key="m1"><str>m1r0foo4</str>\n</entry>\n'
                '<entry key="name"><str>foo4</str>\n</entry>\n'
                '</meta>\n'
                '<data coding="base64"><chunk>YmFyMg==</chunk>\n</data>\n'
                '</revision>\n'
                '<revision revno="1">'
                '<meta>'
                '<entry key="mimetype"><str>application/octet-stream</str>\n</entry>\n'
                '<entry key="m1"><str>m1r1foo4</str>\n</entry>\n'
                '<entry key="name"><str>foo4</str>\n</entry>\n'
                '</meta>\n'
                '<data coding="base64"><chunk>YmF6Mg==</chunk>\n</data>\n'
                '</revision>\n'
                '</item>') in xml


class TestSerializer2(object):
    def test_Entry(self):
        test_data = [
            ('foo', 'bar', '<entry key="foo"><bytes>bar</bytes>\n</entry>\n'),
            (u'foo', u'bar', '<entry key="foo"><str>bar</str>\n</entry>\n'),
            ('''<"a"&'b'>''', '<c&d>', '''<entry key="&lt;&quot;a&quot;&amp;'b'&gt;"><bytes>&lt;c&amp;d&gt;</bytes>\n</entry>\n'''),
        ]
        for k, v, expected_xml in test_data:
            e = Entry(k, v)
            xmlfile = StringIO()
            serialize(e, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == XML_DECL + expected_xml

        for expected_k, expected_v, xml in test_data:
            xmlfile = StringIO(xml)
            result = {}
            unserialize(Entry(attrs={'key': expected_k}, rev_or_item=result), xmlfile)
            assert expected_k in result
            assert result[expected_k] == expected_v

    def test_Values(self):
        test_data = [
            ('bar', '<bytes>bar</bytes>\n'),
            (u'bar', '<str>bar</str>\n'),
            (42, '<int>42</int>\n'),
            (True, '<bool>True</bool>\n'),
            (23.42, '<float>23.42</float>\n'),
            (complex(1.2, 2.3), '<complex>(1.2+2.3j)</complex>\n'),
            ((1, 2), '<tuple><int>1</int>\n<int>2</int>\n</tuple>\n'),
            ((1, u'bar'), '<tuple><int>1</int>\n<str>bar</str>\n</tuple>\n'),
            ((1, (u'bar', u'baz')), '<tuple><int>1</int>\n<tuple><str>bar</str>\n<str>baz</str>\n</tuple>\n</tuple>\n'),
        ]
        for v, expected_xml in test_data:
            v = create_value_object(v)
            xmlfile = StringIO()
            serialize(v, xmlfile)
            xml = xmlfile.getvalue()
            assert xml == XML_DECL + expected_xml

