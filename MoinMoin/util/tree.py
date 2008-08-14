"""
MoinMoin - Tree name and element generator

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

class Name(ET.QName):
    """
    QName and factory for elements with this QName
    """
    def __call__(self, attrib=None, children=(), **extra):
        return ET.Element(self, attrib=attrib, children=children, **extra)

class Namespace(unicode):
    def __getattr__(self, key):
        if key.endswith('_'):
            key = key[:-1]
        return Name(key.replace('_', '-'), self)

    def __repr__(self):
        return '<%s(%r)>' % (self.__class__.__name__, self)

    @property
    def namespace(self):
        return self

# Own namespaces
moin_page = Namespace('http://moinmo.in/namespaces/page')

# Well-known namespaces
dc = Namespace('http://purl.org/dc/elements/1.1/')
html = Namespace('http://www.w3.org/1999/xhtml')
mathml = Namespace('http://www.w3.org/1998/Math/MathML')
svg = Namespace('http://www.w3.org/2000/svg')
xinclude = Namespace('http://www.w3.org/2001/XInclude')
xlink = Namespace('http://www.w3.org/1999/xlink')
