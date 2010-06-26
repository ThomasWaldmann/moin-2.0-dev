# -*- coding: iso-8859-1 -*-
"""
MoinMoin - HTML input converter

Converts an HTML Tree into an internal document tree.

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from emeraldtree import ElementTree as ET
from emeraldtree.html import HTML

from MoinMoin import wikiutil
from MoinMoin.util.tree import html, moin_page, xlink
from ._wiki_macro import ConverterMacro

from MoinMoin import log
logging = log.getLogger(__name__)

import re

# What is the purpose of this class?
class ElementException(RuntimeError):
    pass

class Converter(object):
    """
    Converter html -> .x.moin.document
    """

    # Namespace of our input data
    html_namespace = {
        html.namespace: 'xhtml',
        }

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags = set(['div', 'p', 'strong', 'code', 'table'])

    # HTML tags which can be convert without attributes in a different DOM tag
    simple_tags = {# Emphasis
                   'em':moin_page.emphasis, 'i':moin_page.emphasis,
                   # Strong 
                   'b':moin_page.strong, 'strong':moin_page.strong,
                   # Code and Blockcode
                   'pre':moin_page.blockcode, 'tt':moin_page.code,
                   'samp':moin_page.code,
                   # Lists
                   'li':moin_page.list_item_body, 'dt':moin_page.list_item_label,
                   'dd':moin_page.list_item_body,
                  }


    # Regular expression to detect an html heading tag
    heading_re = re.compile('h[1-6]')

    # Store the Base URL for all the URL of the document
    base_url = ""

    @classmethod
    def _factory(cls, input, output, request, **kw):
        return cls(request)

    def __call__(self, content, arguments=None):
        """
        Function called by the converter to process the
        conversion.

        TODO: Add support for different arguments
        """

        # Be sure we have empty string in the base url
        self.base_url = ""

        # We create an element tree from the HTML content
        # The content is a list of string, line per line
        # We can concatenate all in one string
        html_str = ''
        html_str = html_str.join(content)
        html_tree = HTML(html_str)

        if html_tree.tag.name != 'html':
            raise TypeError(u"Unvalid html document, it should start with <html> tag")

        # Start the conversion of the first element
        # Every child of each element will be recursively convert too
        element = self.visit(html_tree)

        # Add Global element to our DOM Tree
        body = moin_page.body(children=element)
        root = moin_page.page(children=[body])
        return root

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

    def new(self, tag, attrib={}, children=[]):
        """
        Return a new element for the DOM Tree
        """
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib={}):
        """
        Function to copy one element to the DOM Tree.

        It first converts the child of the element,
        and the element itself.
        """
        # TODO: Handle Attributes correctly
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def new_copy_symmetric(self, element, attrib={}):
        """
        Create a new QName, with the same tag of the element,
        but with a different namespace.

        Then, we handle the copy normally.
        """
        tag = ET.QName(element.tag.name, moin_page)
        return self.new_copy(tag, element, attrib)

    def visit(self, element):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the found namespace.
        """
        uri = element.tag.uri
        name = self.html_namespace.get(uri, None)
        if name is not None:
            method_name = 'visit_' + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)

            # We process children of the unknown element
            return self.do_children(element)

    def visit_xhtml(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the XHTML namespace.

        We will detect the name of the tag, and apply an appropriate
        procedure to convert it.
        """
        print element.tag.name
        if element.tag.name in self.symmetric_tags:
        # Our element can be converted directly, just by changing the namespace
            return self.new_copy_symmetric(element)
        if element.tag.name in self.simple_tags:
        # Our element is enough simple to just change the tag name
            return self.new_copy(self.simple_tags[element.tag.name], element)
        if self.heading_re.match(element.tag.name):
        # We have an heading tag
            return self.visit_xhtml_heading(element)
        else:
        # Otherwise we need a specific procedure to handle it
            method_name = 'visit_xhtml_' + element.tag.name
            method = getattr(self, method_name, None)
            if method:
                return method(element)

            # We process children of the unknown element
            return self.do_children(element)

    def visit_xhtml_base(self, element):
        """
        Function to store the base url for the relative url of the document
        """
        self.base_url = element.get(html.href)

    def visit_xhtml_heading(self, element):
        """
        Function to convert an heading tag into the proper
        element in our moin_page namespace
        """
        heading_level = element.tag.name[1]
        # TODO: Maybe add some verification about the level

        key = moin_page('outline-level')
        attrib = {}
        attrib[key] = heading_level
        return self.new_copy(moin_page.h, element, attrib)

    def visit_xhtml_br(self, element):
        return moin_page.line_break()

    def visit_xhtml_big(self, element):
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '120%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_small(self, element):
        key = moin_page('font-size')
        attrib = {}
        attrib[key] = '85%'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sub(self, element):
        key = moin_page('base-line-shift')
        attrib = {}
        attrib[key] = 'sub'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_sup(self, element):
        key = moin_page('base-line-shift')
        attrib = {}
        attrib[key] = 'super'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_u(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_ins(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'underline'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_del(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_s(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_strike(self, element):
        key = moin_page('text-decoration')
        attrib = {}
        attrib[key] = 'line-through'
        return self.new_copy(moin_page.span, element, attrib)

    def visit_xhtml_hr(self, element):
        return moin_page.separator()

    def visit_xhtml_a(self, element):
        key = xlink('href')
        attrib = {}
        attrib[key] = ''.join([self.base_url, element.get(html.href)])
        return self.new_copy(moin_page.a, element, attrib)

    def visit_xhtml_img(self, element):
        key = xlink('href')
        attrib = {}
        attrib[key] = ''.join([self.base_url, element.get(html.src)])
        return moin_page.object(attrib)

    def visit_xhtml_ul(self, element):
        # We will process all children (which should be list element normally
        list_items_elements = self.do_children(element)
        list_item = ET.Element(moin_page.list_item, attrib={}, children=list_items_elements)
        attrib = {}
        attrib[moin_page('item-label-generate')] = 'unordered'
        return ET.Element(moin_page.list, attrib=attrib, children=[list_item])

    def visit_xhtml_dir(self, element):
        # We will process all children (which should be list element normally
        list_items_elements = self.do_children(element)
        list_item = ET.Element(moin_page.list_item, attrib={}, children=list_items_elements)
        attrib = {}
        attrib[moin_page('item-label-generate')] = 'unordered'
        return ET.Element(moin_page.list, attrib=attrib, children=[list_item])

    def visit_xhtml_ol(self, element):
        # We will process all children (which should be list element normally
        list_items_elements = self.do_children(element)
        list_item = ET.Element(moin_page.list_item, attrib={}, children=list_items_elements)

        # We create attributes according to the type of the list
        attrib = {}
        attrib[moin_page('item-label-generate')] = 'ordered'

        # We check which kind of style we have
        style = element.get(html.type)
        if 'A' == style:
            attrib[moin_page('list-style-type')] = 'upper-alpha'
        elif 'I' == style:
            attrib[moin_page('list-style-type')] = 'upper-roman'
        elif 'a' == style:
            attrib[moin_page('list-style-type')] = 'downer-alpha'
        elif 'i' == style:
            attrib[moin_page('list-style-type')] = 'downer-roman'

        return ET.Element(moin_page.list, attrib=attrib, children=[list_item])

    def visit_xhtml_dl(self, element):
        # We will process all children (which should be list element normally
        list_items_elements = self.do_children(element)
        list_item = ET.Element(moin_page.list_item, attrib={}, children=list_items_elements)
        return ET.Element(moin_page.list, attrib={}, children=[list_item])

    def visit_xhtml_theader(self, element):
        return self.new_copy(moin_page.table_header, element)

    def visit_xhtml_tfooter(self, element):
        return self.new_copy(moin_page.table_footer, element)

    def visit_xhtml_tbody(self, element):
        return self.new_copy(moin_page.table_body, element)

    def visit_xhtml_tr(self, element):
        return self.new_copy(moin_page.table_row, element)

    def visit_xhtml_td(self, element):
        attrib = {}
        rowspan = element.get(html.rowspan)
        colspan = element.get(html.colspan)
        if rowspan:
            attrib[moin_page('number-rows-spanned')] = rowspan
        if colspan:
            attrib[moin_page('number-columns-spanned')] = colspan
        return self.new_copy(moin_page.table_cell, element, attrib=attrib)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, Type('text/x.moin.xhtml'), type_moin_document)
