"""
MoinMoin - Tests for MoinMoin.util.tree

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.util.tree import *

def test_Name():
    uri = 'uri:a'

    name = Name('a', uri)
    assert isinstance(name, ET.QName)
    assert name.name == 'a'
    assert name.uri == uri
    assert name == '{uri:a}a'

    element = name()
    assert isinstance(element, ET.Element)
    assert element.tag == name

def test_Namespace():
    uri = 'uri:a'

    namespace = Namespace(uri)
    assert namespace.namespace == uri

    name = namespace.a
    assert isinstance(name, Name)
    assert name.name == 'a'
    assert name.uri == uri

    name = namespace.outline_level
    assert name.name == 'outline-level'
    assert name.uri == uri

def test_html():
    assert isinstance(html, Namespace)
    assert html.namespace == namespaces.html

def test_moin_page():
    assert isinstance(moin_page, Namespace)
    assert moin_page.namespace == namespaces.moin_page
