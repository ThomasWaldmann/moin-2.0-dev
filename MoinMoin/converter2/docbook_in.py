# -*- coding: iso-8859-1 -*-
"""
MoinMoin - DocBook input converter

Converts a DocBook tree into an internal document tree.

Currently support DocBook v.5.0

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util.tree import moin_page, xlink, docbook
from ._wiki_macro import ConverterMacro

from MoinMoin import log
logging = log.getLogger(__name__)

import re

class Converter(object):
    """
    Converter application/docbook+xml -> x.moin.document
    """

    # Namespace of our input data
    docbook_namespace = {
        docbook.namespace: 'docbook'
    }

    sect_re = re.compile('sect[1-5]')

    @classmethod
    def _factory(cls, input, output, request, **kw):
        return cls()

    def __call__(self, content, aruments=None):
        """
        Function called by the converter to process
        the conversion.
        """
        # We will create an element tree from the DocBook content
        # The content is given to the converter as a list of string,
        # line per line.
        # So we will concatenate all in one string.
        docbook_str = ''
        docbook_str = docbook_str.join(content)
        tree = ET.XML(docbook_str)

        return self.visit(tree)

    def do_children(self, element):
        """
        Function to process the conversion of the child of
        a given elements.
        """
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                new.extend(r)
            else:
                new.append(child)
        return new

    def new(self, tag, attrib, children):
        """
        Return a new element for the DocBook Tree
        """
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib):
        """
        Function to copy one element to the DocBook Tree.

        It first converts the child of the element,
        and the element itself.
        """
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def visit(self, element):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the given namespace.
        """
        uri = element.tag.uri
        name = self.docbook_namespace.get(uri, None)
        if name is not None:
            method_name = 'visit_' + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)

            # We process children of the unknown element
            return self.do_children(element)

    def visit_docbook(self, element):
        """
        Function called to handle the conversion of DocBook elements
        to the Moin_page DOM Tree.

        We will detect the name of the tag, and pick the correct method
        to convert it.
        """

        # We have a section tag
        if self.sect_re.match(element.tag.name):
            result = []
            result.append(self.visit_docbook_sect(element))
            result.extend(self.do_children(element))
            return result
        method_name = 'visit_docbook_' + element.tag.name
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # Otherwise we process children of the unknown element
        return self.do_children(element)

    def visit_docbook_article(self, element):
        children = self.do_children(element)
        body = moin_page.body(children=children)
        return moin_page.page(children=[body])

    def visit_docbook_glossdef(self, element):
        return self.new_copy(moin_page('list-item-body'), element, attrib={})

    def visit_docbook_glossentry(self, element):
        return self.new_copy(moin_page('list-item'), element, attrib={})

    def visit_docbook_glosslist(self, element):
        return self.new_copy(moin_page.list, element, attrib={})

    def visit_docbook_glossterm(self, element):
        return self.new_copy(moin_page('list-item-label'), element, attrib={})

    def visit_docbook_itemizedlist(self, element):
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'unordered'
        return self.visit_simple_list(moin_page.list, attrib, element)

    def visit_docbook_orderedlist(self, element):
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'ordered'
        return self.visit_simple_list(moin_page.list, attrib, element)

    def visit_docbook_para(self, element):
        return self.new_copy(moin_page.p, element, attrib={})

    def visit_docbook_sect(self, element):
        title = ''
        for child in element:
            if isinstance(child, ET.Element):
                uri = child.tag.uri
                name = self.docbook_namespace.get(uri, None)
                if name == 'docbook' and child.tag.name == 'title':
                    title = child
        heading_level = element.tag.name[4]
        key = moin_page('outline-level')
        attrib = {}
        attrib[key] = heading_level
        return self.new(moin_page.h, attrib=attrib, children=title)

    def visit_docbook_term(self, element):
        return self.new_copy(moin_page('list-item-label'), element, attrib={})

    def visit_docbook_listitem(self, element):
        # NB : We need to be sure it is only called for a variablelist
        return self.new_copy(moin_page('list-item-body'), element, attrib={})

    def visit_docbook_procedure(self, element):
        # TODO : See to add Procedure text (if needed)
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'ordered'
        return self.visit_simple_list(moin_page.list, attrib, element)

    def visit_docbook_title(self, element):
        """
        Later we should add support for all the different kind of title.

        But currently, only the section title are supported, so we do
        not want to process it.
        """
        pass

    def visit_docbook_variablelist(self, element):
        return self.new_copy(moin_page.list, element, attrib={})

    def visit_docbook_varlistentry(self, element):
        return self.new_copy(moin_page('list-item'), element, attrib={})

    def visit_simple_list(self, moin_page_tag, attrib, element):
        list_item_tags = set(['listitem', 'step'])
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name in list_item_tags:
                    children = self.visit(child)
                    list_item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=children)
                    tag = ET.Element(moin_page('list-item'), attrib={},
                                     children=[list_item_body])
                    tag = (tag, )
                    items.extend(tag)
                else:
                    r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page.list, attrib=attrib, children=items)

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('application/docbook+xml'), type_moin_document)
