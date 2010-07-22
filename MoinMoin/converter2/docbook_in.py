# -*- coding: iso-8859-1 -*-
"""
MoinMoin - DocBook input converter
Converts a DocBook document into an internal document tree.

Currently supports DocBook v5.

Some elements of DocBook v4 specification are also supported
for backward compatibility :
  * ulink

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from emeraldtree import ElementTree as ET

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin.util.tree import moin_page, xlink, docbook

from ._wiki_macro import ConverterMacro

class Converter(object):
    """
    Converter application/docbook+xml -> x.moin.document
    """
    # Namespace of our input data
    docbook_namespace = {
        docbook.namespace: 'docbook'
    }

    sect_re = re.compile('sect[1-5]')
    section_depth = 0
    heading_level = 0

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

        return self.visit(tree, 0)

    def do_children(self, element, depth):
        """
        Function to process the conversion of the child of
        a given elements.
        """
        new = []
        depth = depth + 1
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child, depth)
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

    def new_copy(self, tag, element, depth, attrib):
        """
        Function to copy one element to the DocBook Tree.

        It first converts the child of the element,
        and the element itself.
        """
        children = self.do_children(element, depth)
        return self.new(tag, attrib, children)

    def visit(self, element, depth):
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
                return method(element, depth)

            # We process children of the unknown element
            return self.do_children(element, depth)

    def visit_docbook(self, element, depth):
        """
        Function called to handle the conversion of DocBook elements
        to the Moin_page DOM Tree.

        We will detect the name of the tag, and pick the correct method
        to convert it.
        """
        # We have a section tag
        if self.sect_re.match(element.tag.name):
            result = []
            result.append(self.visit_docbook_sect(element, depth))
            result.extend(self.do_children(element, depth))
            return result
        method_name = 'visit_docbook_' + element.tag.name
        method = getattr(self, method_name, None)
        if method:
            return method(element, depth)

        # Otherwise we process children of the unknown element
        return self.do_children(element, depth)

    def visit_docbook_article(self, element, depth):
        # TODO : Automatically add a ToC, need to see how to let
        # the user specify it.
        children = []
        children.append(ET.Element(moin_page('table-of-content')))
        children.extend(self.do_children(element, depth))

        body = moin_page.body(children=children)
        return moin_page.page(children=[body])

    def visit_docbook_emphasis(self, element, depth):
        """
        emphasis element, is the only way to apply some style
        on a DocBook element directly from the DocBook tree.

        Basically, you can use it for "italic" and "bold" style.

        However, it is still semantic, so we call it emphasis and strong.
        """
        for key, value in element.attrib.iteritems():
            if key.name == 'role' and value == 'strong':
                return self.new_copy(moin_page.strong, element,
                                     depth, attrib={})
        return self.new_copy(moin_page.emphasis, element,
                             depth, attrib={})

    def visit_docbook_footnote(self, element, depth):
        attrib = {}
        key = moin_page('note-class')
        attrib[key] = "footnote"
        children = self.new(moin_page('note-body'), attrib={},
                            children=self.do_children(element, depth))
        return self.new(moin_page.note, attrib=attrib, children=[children])

    def visit_docbook_glossdef(self, element, depth):
        return self.new_copy(moin_page('list-item-body'),
                             element, depth, attrib={})

    def visit_docbook_glossentry(self, element, depth):
        return self.new_copy(moin_page('list-item'),
                             element, depth, attrib={})

    def visit_docbook_glosslist(self, element, depth):
        return self.new_copy(moin_page.list, element,
                             depth, attrib={})

    def visit_docbook_glossterm(self, element, depth):
        return self.new_copy(moin_page('list-item-label'),
                             element, depth, attrib={})

    def visit_docbook_imagedata(self, element, depth):
        attrib = {}
        href = element.get('fileref')
        key = xlink.href
        attrib[key] = href
        return ET.Element(moin_page.object, attrib=attrib)

    def visit_docbook_itemizedlist(self, element, depth):
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'unordered'
        return self.visit_simple_list(moin_page.list, attrib,
                                      element, depth)

    def visit_docbook_link(self, element, depth):
        """
        LINK Conversion.

        There is two kind of links in DocBook :
        One using the xlink namespace.
        The other one using linkend attribute.

        The xlink attribute can directly be used in the <a> tag of the
        DOM Tree.

        For the linkend attribute, we need to have a system supporting
        the anchors.
        """
        attrib = {}
        for key, value in element.attrib.iteritems():
            if key.uri == xlink:
                attrib[key] = value
        return self.new_copy(moin_page.a, element, depth, attrib=attrib)

    def visit_docbook_literal(self, element, depth):
        return self.new_copy(moin_page.code, element, depth, attrib={})

    def visit_docbook_orderedlist(self, element, depth):
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
        return self.visit_simple_list(moin_page.list, attrib,
                                      element, depth)

    def visit_docbook_para(self, element, depth):
        return self.new_copy(moin_page.p, element, depth, attrib={})

    def visit_docbook_phrase(self, element, depth):
        return self.new_copy(moin_page.span, element, depth, attrib={})

    def visit_docbook_programlisting(self, element, depth):
        return self.new_copy(moin_page.blockcode, element, depth, attrib={})

    def visit_docbook_screen(self, element, depth):
        return self.new_copy(moin_page.blockcode, element, depth, attrib={})

    def visit_docbook_sect(self, element, depth):
        """
        This is the function to convert numbered section.

        Numbered section use tag like <sectN> where N is the number
        of the section between 1 and 5.

        The section are supposed to be correctly nested.

        We only convert a section to an heading if one of the children
        is a title element.

        TODO : See if we can unify with recursive section below.
        TODO : Add div element, with specific id
        """
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

    def visit_docbook_section(self, element, depth):
        """
        This is the function to convert recursive section.

        Recursive section use tag like <section> only.

        Each section, inside another section is a subsection.

        To convert it, we will use the depth of the element, and
        two attributes of the converter which indicate the
        current depth of the section and the current level heading.
        """
        if depth > self.section_depth:
            self.section_depth = self.section_depth + 1
            self.heading_level = self.heading_level + 1
        elif depth < self.section_depth:
            self.heading_level = self.heading_level - (self.section_depth - depth)
            self.section_depth = depth

        title = ''
        result = []
        for child in element:
            if isinstance(child, ET.Element):
                uri = child.tag.uri
                name = self.docbook_namespace.get(uri, None)
                if name == 'docbook' and child.tag.name == 'title':
                    title = child
        key = moin_page('outline-level')
        attrib = {}
        attrib[key] = self.heading_level
        result.append(self.new(moin_page.h, attrib=attrib, children=title))
        result.extend(self.do_children(element, depth))
        return result

    def visit_docbook_seglistitem(self, element, labels, depth):
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
                            attrib={}, children=self.visit(child, depth))
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

    def visit_docbook_segmentedlist(self, element, depth):
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
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    labels.extend(r)
                else:
                    if child.tag.name == 'seglistitem':
                        r = self.visit_docbook_seglistitem(child,
                            labels, depth)
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

    def visit_docbook_simplelist(self, element, depth):
        # TODO : Add support of the type attribute
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'unordered'
        return self.visit_simple_list(moin_page.list, attrib, element, depth)

    def visit_docbook_subscript(self, element, depth):
        attrib = {}
        key = moin_page('baseline-shift')
        attrib[key] = 'sub'
        return self.new_copy(moin_page.span, element,
                             depth, attrib=attrib)

    def visit_docbook_superscript(self, element, depth):
        attrib = {}
        key = moin_page('baseline-shift')
        attrib[key] = 'super'
        return self.new_copy(moin_page.span, element,
                             depth, attrib=attrib)

    def visit_docbook_term(self, element, depth):
        return self.new_copy(moin_page('list-item-label'),
                             element, depth, attrib={})

    def visit_docbook_listitem(self, element, depth):
        # NB : We need to be sure it is only called for a variablelist
        return self.new_copy(moin_page('list-item-body'),
                             element, depth, attrib={})

    def visit_docbook_procedure(self, element, depth):
        # TODO : See to add Procedure text (if needed)
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'ordered'
        return self.visit_simple_list(moin_page.list, attrib,
                                      element, depth)

    def visit_docbook_qandaset(self, element, depth):
        default_label = element.get(docbook.defaultlabel)
        if default_label == 'number':
            return self.visit_qandaset_number(element, depth)
        elif default_label == 'qanda':
            return self.visit_qandaset_qanda(element, depth)
        else:
            return self.do_children(element, depth)

    def visit_docbook_title(self, element, depth):
        """
        Later we should add support for all the different kind of title.

        But currently, only the section title are supported, so we do
        not want to process it.
        """
        pass

    def visit_docbook_table(self, element, depth):
        # we should not have any strings in the child
        list_table_elements = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                list_table_elements.extend(r)
        return ET.Element(moin_page.table, attrib={}, children=list_table_elements)

    def visit_docbook_thead(self, element, depth):
        return self.new_copy(moin_page.table_header,
                             element, depth, attrib={})

    def visit_docbook_tfoot(self, element, depth):
        return self.new_copy(moin_page.table_footer,
                             element, depth, attrib={})

    def visit_docbook_tbody(self, element, depth):
        return self.new_copy(moin_page.table_body,
                             element, depth, attrib={})

    def visit_docbook_tr(self, element, depth):
        return self.new_copy(moin_page.table_row,
                             element, depth, attrib={})

    def visit_docbook_td(self, element, depth):
        attrib = {}
        rowspan = element.get(docbook.rowspan)
        colspan = element.get(docbook.colspan)
        if rowspan:
            attrib[moin_page('number-rows-spanned')] = rowspan
        if colspan:
            attrib[moin_page('number-columns-spanned')] = colspan
        return self.new_copy(moin_page.table_cell,
                             element, depth, attrib=attrib)

    def visit_docbook_ulink(self, element, depth):
        """
        NB : <ulink> is not a part of DocBook v.5 however we
        support it in our converter since it is still widely used
        and it helps to keep a compatibility with DocBook v.4
        """
        attrib = {}
        href = element.get(docbook.url)
        # Since it is an element of DocBook v.4,
        # The namespace does not always work, so we will try to retrive the attribute whatever
        if not(href):
            for key, value in element.attrib.iteritems():
                if key.name == 'url':
                    href = value
        key = xlink.href
        attrib[key] = href
        return self.new_copy(moin_page.a, element, depth, attrib=attrib)

    def visit_docbook_variablelist(self, element, depth):
        return self.new_copy(moin_page.list, element, depth, attrib={})

    def visit_docbook_varlistentry(self, element, depth):
        return self.new_copy(moin_page('list-item'), element,
                             depth, attrib={})

    def visit_qandaentry_number(self, element, depth):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == 'question' or child.tag.name == 'answer':
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    items.extend(r)
            else:
                items.append(child)

        item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=items)
        return ET.Element(moin_page('list-item'), attrib={}, children=[item_body])

    def visit_qandaset_number(self, element, depth):
        attrib = {}
        key = moin_page('item-label-generate')
        attrib[key] = 'ordered'
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name == 'qandaentry':
                    r = self.visit_qandaentry_number(child, depth)
                else:
                    r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                items.extend(r, )
            else:
                items.append(child)
        return ET.Element(moin_page('list'), attrib=attrib, children=items)

    def visit_qandaentry_qanda(self, element, depth):
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
                    r = self.visit(child, depth)
                    if r is None:
                        r = ()
                    elif not isinstance(r, (list, tuple)):
                        r = (r, )
                    items.extend(r)
                if item_label is not None:
                    item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=self.visit(child, depth))
                    r = (item_label, item_body)
                    list_item = ET.Element(moin_page('list-item'), attrib={}, children=r)
                    items.append(list_item)
            else:
                items.append(child)
        return items

    def visit_qandaset_qanda(self, element, depth):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = ()
                if child.tag.name == 'qandaentry':
                    r = self.visit_qandaentry_qanda(child, depth)
                else:
                    r = self.visit(child, depth)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                items.extend(r)
            else:
                items.append(child)
        return ET.Element(moin_page('list'), attrib={}, children=items)

    def visit_simple_list(self, moin_page_tag, attrib, element, depth):
        list_item_tags = set(['listitem', 'step', 'member'])
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.name in list_item_tags:
                    children = self.visit(child, depth)
                    list_item_body = ET.Element(moin_page('list-item-body'), attrib={}, children=children)
                    tag = ET.Element(moin_page('list-item'), attrib={},
                                     children=[list_item_body])
                    tag = (tag, )
                    items.extend(tag)
                else:
                    r = self.visit(child, depth)
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