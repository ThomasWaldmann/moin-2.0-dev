"""
MoinMoin - ReStructured Text input converter

This is preprealpha version, do not use it, it doesn't work.

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config, wikiutil
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xlink
#### TODO: try block
from docutils import nodes, utils
from docutils.parsers.rst import Parser
#####

class NodeVisitor(nodes.NodeVisitor):

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        root = None

    def tree(self):
        return self.root 

    def visit_Text(self, node):
        text = node.astext()
        self.children.append(text)

    def depart_Text(self, node):
        pass

    def visit_block_quote(self, node):
        self.children.append(text)

    def depart_block_quote(self, node):
        pass

    def visit_bullet_list(self, node):
        pass

    def visit_caption(self, node):
        pass

    def depart_bullet_list(self, node):
        pass

    def visit_definition(self, node):
        pass

    def depart_definition(self, node):
        pass

    def visit_definition_list(self, node):
        pass

    def depart_definition_list(self, node):
        pass

    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    def visit_emphasis(self, node):
        pass

    def depart_emphasis(self, node):
        pass

    def visit_entry(self, node):
    # table cell?
        pass

    def depart_entry(self, node):
        pass

    def visit_enumerated_list(self, node):
        pass

    def depart_enumerated_list(self, node):
        pass

    def visit_field(self, node):
    # table row?
        pass

    def depart_field(self, node):
        pass

    def visit_field_body(self, node):
        pass

    def depart_field_body(self, node):
        pass

    def visit_field_list(self, node):
        pass

    def depart_field_list(self, node):
        pass

    def visit_field_name(self, node):
        pass

    def depart_field_name(self, node):
        pass

    def visit_figure(self, node):
        pass

    def depart_figure(self, node):
        pass

    def visit_footer(self, node):
        pass

    def depart_footer(self, node):
        pass

    def visit_footnote(self, node):
        pass

    def depart_footnote(self, node):
        pass

    def visit_footnote_reference(self, node):
        pass

    def depart_footnote_reference(self, node):
        pass

    def visit_header(self, node):
        pass

    def depart_header(self, node):
        pass

    def visit_image(self, node):
        pass

    def depart_image(self, node):
        pass

    def visit_inline(self, node):
        pass

    def depart_inline(self, node):
        pass

    def visit_label(self, node):
        pass

    def depart_label(self, node):
        pass

    def visit_line(self, node):
        pass

    def depart_line(self, node):
        pass

    def visit_line_block(self, node):
        pass

    def depart_line_block(self, node):
        pass

    def visit_list_item(self, node):
        pass

    def depart_list_item(self, node):
        pass

    def visit_literal(self, node):
        pass

    def visit_literal_block(self, node):
        pass

    def depart_literal_block(self, node):
        pass

    def visit_paragraph(self, node):
        pass

    def depart_paragraph(self, node):
        pass

    def visit_problematic(self, node):
        pass

    def depart_problematic(self, node):
        pass

    def visit_reference(self, node):
    # <a>
        pass

    def depart_reference(self, node):
        pass

    def visit_row(self, node):
        pass

    def depart_row(self, node):
        pass

    def visit_rubric(self, node):
    # <p>
        pass

    def depart_rubric(self, node):
        pass

    def visit_section(self, node):
        pass

    def depart_section(self, node):
        pass

    def visit_sidebar(self, node):
        pass

    def depart_sidebar(self, node):
        pass

    def visit_strong(self, node):
        pass

    def depart_strong(self, node):
        pass

    def visit_subscript(self, node):
        pass

    def depart_subscript(self, node):
        pass

    def visit_subtitle(self, node):
        pass

    def depart_subtitle(self, node):
        pass

    def visit_superscript(self, node):
        pass

    def depart_superscript(self, node):
        pass

    def visit_system_message(self, node):
        pass

    def depart_system_message(self, node):
        pass

    def visit_table(self, node):
        pass

    def depart_table(self, node):
        pass

    def visit_tbody(self, node):
        pass

    def depart_tbody(self, node):
        pass

    def visit_tgroup(self, node):
        pass

    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        pass

    def depart_thead(self, node):
        pass

    def visit_title(self, node):
        pass

    def depart_title(self, node):
        pass

    def visit_title_reference(self, node):
        pass

    def depart_title_reference(self, node):
        pass

    def unimplemented_visit(self, node):
        pass

class Converter(object):
    @classmethod
    def factory(cls, input,output, **kw):
        return cls()

    def __call__(self, input, arguments=None):
        parser = Parser()
        docutils_internal_document = utils.new_document()
        parser.parse(input, docutils_internal_document)
        visitor = NodeVisitor()
        docutils_internal_document.walk(visitor)
        return visitor.tree()

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter.factory, Type('x-moin/format;name=rst', type_moin_document))

