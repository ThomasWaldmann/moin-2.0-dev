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

# What is the purpose of this class ?
class ElementException(RuntimeError):
    pass

class Converter(ConverterMacro):
    """
    Converter html -> .x.moin.document
    """

    html_namespace = {
        html.namespace: 'xhtml',
        }

    @classmethod
    def _factory(cls, _request, input, output, **kw):
        if output == 'application/x.moin.document' and \
           input == 'application/x-xhtml-moin-page':
            return cls

    def __call__(self, content, arguments=None):
        """
        Function called by the converter to process the
        conversion.

        TODO : Add support for different arguments
        """
        # We create an element tree from the HTML content
        html_tree = HTML(content)

        # Add Attrib for the page
        element = self.visit(html_tree)
        body = moin_page.body(children=[element])
        root = moin_page.page(children=[body])
        return root

    def do_children(self, element):
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
        return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib={}):
        # TODO : Attributes
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def visit(self, element):
        uri = element.tag.uri
        name = self.html_namespace.get(uri, None)
        if name is not None:
            n = 'visit_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(element)
        # TODO : Unknown element

    def visit_xhtml(self, element):
        n = 'visit_xhtml_' + element.tag.name
        print "n : %s" % n
        f = getattr(self, n, None)
        if f:
            return f(element)
        # TODO : Unknown element

    def visit_xhtml_div(self, element):
        # No equivalence in DOM Tree ??
        return self.new_copy(moin_page.div, element)

    def visit_xhtml_p(self, element):
        return self.new_copy(moin_page.p, element)
