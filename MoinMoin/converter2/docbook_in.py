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
        docbook_str = u''
        docbook_str = docbook_str.join(content)
        # TODO : Check why the XML parser from Element Tree need ByteString
        tree = ET.XML(docbook_str.encode('utf-8'))

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
        attribute_conversion = {"upperalpha": "upper-alpha",
                                "loweralpha": "lower-alpha",
                                "upperroman": "upper-roman",
                                "lowerroman": "lower-roman"}
        numeration = element.get(docbook.numeration)
        if numeration in attribute_conversion:
            key = moin_page('list-style-type')
            attrib[key] = attribute_conversion[numeration]
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

    def visit_docbook_seglistitem(self, element, labels):
        """
        A seglistitem is a list-item for a segmented list. It is quite
        special because it act list definition with label, but the labels
        are predetermined in the labels list.

        So we generate label/body couple according to the content in
        labels
        """
        new = []
        counter = 0
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == 'seg':
                    label_tag = ET.Element(moin_page('list-item-label'),
                            attrib={}, children=labels[counter % len(labels)])
                    body_tag = ET.Element(moin_page('list-item-body'),
                            attrib={}, children=self.visit(child))
                    item_tag = ET.Element(moin_page('list-item'),
                            attrib={}, children=[label_tag, body_tag])
                    item_tag = (item_tag, )
                    new.extend(item_tag)
                    counter = counter + 1
                else:
                    r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    new.extend(r)
            else:
                new.append(child)
        return new

    def visit_docbook_segmentedlist(self, element):
        """
        A segmented list is a like a list of definition, but the label
        are defined at the start with <segtitle> tag and then for each
        definition, we repeat the label.

        So to convert such list, we will first determine and save the
        labels. Then we will iterate over the object to get the
        definition.
        """
        labels = []
        new = []
        for child in element:
            if isinstance(child, ET.Element):
                r = None
                if child.tag.name == 'segtitle':
                    r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    labels.extend(r)
                else:
                    if child.tag.name == 'seglistitem':
                        r = self.visit_docbook_seglistitem(child, labels)
                    else:
                        r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    new.extend(r)
            else:
                new.append(child)
        return ET.Element(moin_page.list, attrib={}, children=new)

    def visit_docbook_simplelist(self, element):
        # TODO : Add support of the type attribute
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'unordered'
        return self.visit_simple_list(moin_page.list, attrib, element)

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

    def visit_docbook_qandaset(self, element):
        default_label = element.get(docbook.defaultlabel)
        if default_label == 'number':
            return self.visit_qandaset_number(element)
        elif default_label == 'qanda':
            return self.visit_qandaset_qanda(element)
        else:
            return self.do_children(element)

    def visit_docbook_title(self, element):
        """
        Later we should add support for all the different kind of title.

        But currently, only the section title are supported, so we do
        not want to process it.
        """
        pass

    def visit_docbook_table(self, element):
        # we should not have any strings in the child
        list_table_elements = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                list_table_elements.extend(r)
        return ET.Element(moin_page.table, attrib={}, children=list_table_elements)

    def visit_docbook_thead(self, element):
        return self.new_copy(moin_page.table_header, element, attrib={})

    def visit_docbook_tfoot(self, element):
        return self.new_copy(moin_page.table_footer, element, attrib={})

    def visit_docbook_tbody(self, element):
        return self.new_copy(moin_page.table_body, element, attrib={})

    def visit_docbook_tr(self, element):
        return self.new_copy(moin_page.table_row, element, attrib={})

    def visit_docbook_td(self, element):
        attrib = {}
        rowspan = element.get(docbook.rowspan)
        colspan = element.get(docbook.colspan)
        if rowspan:
            attrib[moin_page('number-rows-spanned')] = rowspan
        if colspan:
            attrib[moin_page('number-columns-spanned')] = colspan
        return self.new_copy(moin_page.table_cell, element, attrib=attrib)

    def visit_docbook_variablelist(self, element):
        return self.new_copy(moin_page.list, element, attrib={})

    def visit_docbook_varlistentry(self, element):
        return self.new_copy(moin_page('list-item'), element, attrib={})

    def visit_qandaentry_number(self, element):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == 'question' or child.tag.name == 'answer':
                    r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    items.extend(r)
            else:
                items.append(child)

        item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=items)
        return ET.Element(moin_page('list-item'), attrib={}, children=[item_body])

    def visit_qandaset_number(self, element):
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'ordered'
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == 'qandaentry':
                    r = self.visit_qandaentry_number(child)
                else:
                    r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                items.extend(r, )
            else:
                items.append(child)
        return ET.Element(moin_page('list'), attrib=attrib, children=items)

    def visit_qandaentry_qanda(self, element):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = ()
                item_label = None
                if child.tag.name == 'question':
                    item_label = ET.Element(moin_page('list-item-label'), attrib={}, children="Q:")
                elif child.tag.name == 'answer':
                    item_label = ET.Element(moin_page('list-item-label'), attrib={}, children="A:")
                else:
                    r = self.visit(child)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    items.extend(r)
                if item_label is not None:
                    item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=self.visit(child))
                    r = (item_label, item_body)
                    list_item = ET.Element(moin_page('list-item'), attrib={}, children=r)
                    items.append(list_item)
            else:
                items.append(child)
        return items

    def visit_qandaset_qanda(self, element):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = ()
                if child.tag.name == 'qandaentry':
                    r = self.visit_qandaentry_qanda(child)
                else:
                    r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page('list'), attrib={}, children=items)

    def visit_simple_list(self, moin_page_tag, attrib, element):
        list_item_tags = set(['listitem', 'step', 'member'])
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
