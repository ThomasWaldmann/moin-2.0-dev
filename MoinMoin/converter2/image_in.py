"""
MoinMoin - Image converter

Convert image to <object> tag for the DOM Tree.

@copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Convert an image to the corresponding <object> in the DOM Tree
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content):
        item_name = content # we just give the name of the item in the content
        attrib = {
            xlink.href: Iri(scheme='wiki.local', path=item_name), # TODO: we need "get" url, not "show"
        }
        image = ET.Element(moin_page('object'), attrib=attrib, children={})
        return image


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('image/png'), type_moin_document)
default_registry.register(Converter._factory, Type('image/jpeg'), type_moin_document)
default_registry.register(Converter._factory, Type('image/gif'), type_moin_document)

