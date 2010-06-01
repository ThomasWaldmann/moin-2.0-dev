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

class Converter(ConverterMacro):
    """
    Converter html -> .x.moin.document
    """

    # Namespace of our input data
    html_namespace = {
        html.namespace: 'xhtml',
        }

    # HTML tags which can be converted directly to the moin_page namespace
    symmetric_tags = set(['div', 'p', 'strong'])

    # Regular expression to detect an html heading tag
    heading_re = re.compile('h[1-6]')

    @classmethod
    def _factory(cls, _request, input, output, **kw):
        if output == 'application/x.moin.document' and \
           input == 'application/x-xhtml-moin-page':
            return cls

    def __call__(self, content, arguments=None):
        """
        Function called by the converter to process the
        conversion.

        TODO: Add support for different arguments
        """
        # We create an element tree from the HTML content
        html_tree = HTML(content)

        # Start the conversion of the first element
        # Every child of each element will be recursively convert too
        element = self.visit(html_tree)

        # Add Global element to our DOM Tree
        body = moin_page.body(children=[element])
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
        # TODO: Unknown namespace

    def visit_xhtml(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the XHTML namespace.

        We will detect the name of the tag, and apply an appropriate
        procedure to convert it.
        """
        if element.tag.name in self.symmetric_tags:
        # Our element can be converted directly, just by changing the namespace
            return self.new_copy_symmetric(element)
        if self.heading_re.match(element.tag.name):
        # We have an heading tag
            return self.visit_xhtml_heading(element)
        else:
        # Otherwise we need a specific procedure to handle it
            method_name = 'visit_xhtml_' + element.tag.name
            method = getattr(self, method_name, None)
            if method:
                return method(element)
        # TODO: Unknown element

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

    def visit_xhtml_em(self, element):
        return self.new_copy(moin_page.emphasis, element)

    def visit_xhtml_pre(self, element):
        return self.new_copy(moin_page.blockcode, element)

    def visit_xhtml_tt(self, element):
        return self.new_copy(moin_page.code, element)

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

    def visit_xhtml_a(self, element):
        key = moin_page('href')
        attrib = {}
        attrib[key] = element.get(html.href)
        return self.new_copy(moin_page.a, element, attrib)
