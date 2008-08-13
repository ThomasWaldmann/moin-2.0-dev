"""
MoinMoin - Tree name and element generator

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces

class Name(ET.QName):
    """
    QName and factory for elements with this QName
    """
    def __call__(self, attrib=None, children=(), **extra):
        return ET.Element(self, attrib=attrib, children=children, **extra)

class Namespace(object):
    def __init__(self, namespace):
        self.namespace = namespace

    def __getattr__(self, key):
        if key.endswith('_'):
            key = key[:-1]
        return Name(key.replace('_', '-'), self.namespace)

html = Namespace(namespaces.html)
moin_page = Namespace(namespaces.moin_page)
xlink = Namespace(namespaces.xlink)
