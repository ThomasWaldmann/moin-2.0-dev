"""
MoinMoin - DocBook output converter
Converts an internal document tree into a DocBook v5 document.

@copyright: 2010 MoinMoin:ValentinJaniaut,
            table conversion based on html_out table conversion by Bastian Blank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from emeraldtree import ElementTree as ET

from MoinMoin import log
logging = log.getLogger(__name__)
from MoinMoin.util.tree import html, moin_page, xlink, docbook

class Converter(object):
    """
    Converter application/x.moin.document -> application/docbook+xml
    """
    namespaces_visit = {
        moin_page: 'moinpage'
    }

    unsupported_tags = set(['separator', ])

    @classmethod
    def _factory(cls, input, output, request, **kw):
        return cls()

    def __call__(self, element):
        self.section_children = {}
        self.parent_section = 0
        self.current_section = 0
        self.root_section = 10
        return self.visit(element)

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

    def new(self, tag, attrib, children):
        """
        Return a new element in the DocBook tree
        """
        if self.current_section > 0:
            self.section_children[self.current_section].append(
                ET.Element(tag, attrib=attrib, children=children))
        else:
            return ET.Element(tag, attrib=attrib, children=children)

    def new_copy(self, tag, element, attrib):
        """
        Function to copy one element to the DocBook tree

        It first converts the children of the element,
        and then the element itself
        """
        children = self.do_children(element)
        return self.new(tag, attrib, children)

    def visit(self, element):
        """
        Function called at each element, to process it.

        It will just determine the namespace of our element,
        then call a dedicated function to handle conversion
        for the found namespace.
        """
        uri = element.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            method_name = 'visit_' + name
            method = getattr(self, method_name, None)
            if method is not None:
                return method(element)
        # We process children of the unknown element
        return self.do_children(element)

    def visit_moinpage(self, element):
        """
        Function called to handle the conversion of elements
        belonging to the moin_page namespace.

        We will choose the most appropriate procedure to convert
        the element according to his name
        """
        # Check that the tag is supported
        if element.tag.name in self.unsupported_tags:
            logging.warning("Unsupported tag : %s" % element.tag.name)
            return self.do_children(element)
        method_name = 'visit_moinpage_' + element.tag.name.replace('-', '_')
        method = getattr(self, method_name, None)
        if method:
            return method(element)

        # Otherwise we process the children of the unknown element
        logging.warning("Unknown tag : %s" % element.tag.name)
        return self.do_children(element)

    def visit_moinpage_a(self, element):
        """
        LINK Conversion.

        Link are defined using the XLINK namespace either
        for the DOM Tree and in DocBook specification, so
        the converter can just copy each xlink: attribute
        into an <a> tag.
        """
        attrib = {}
        for key, value in element.attrib.iteritems():
            if key.uri == xlink:
                attrib[key] = value
        return self.new_copy(docbook.link, element, attrib=attrib)

    def visit_moinpage_blockcode(self, element):
        code_str = ''.join(element)
        children = ''.join(['<![CDATA[', code_str, ']]>'])
        return self.new(docbook.screen, attrib={}, children=children)

    def visit_moinpage_code(self, element):
        return self.new_copy(docbook.literal, element, attrib={})

    def visit_moinpage_emphasis(self, element):
        return self.new_copy(docbook.emphasis, element, attrib={})

    def visit_moinpage_h(self, element):
        """
        There is not really heading in DocBook, but rather section with
        title. The section is a root tag for all the elements which in
        the dom tree will be between two heading tags.

        So we need to process child manually to determine correctly the
        children of each section.

        A section is closed when we have a new heading with an equal or
        higher level.
        """
        depth = element.get(moin_page('outline-level'))
        # We will have a new section
        # under another section
        if depth > self.current_section:
            self.parent_section = self.current_section
            self.current_section = int(depth)
            self.section_children[self.current_section] = []
            #NB : Error with docbook.title
            title = ET.Element(docbook('title'), attrib={}, children=element[0])
            self.section_children[self.current_section].append(title)

        # We will close a section before starting a new one
        # Need more test
        elif  depth < current_depth:
            if self.parent_section != 0:
                section_tag = 'sect%d' % self.parent_section
                section = ET.Element(docbook(section_tag), attrib={},
                          children=self.section_children[self.current_section])
                self.section_children[self.parent_section].append(section)
                self.current_section = int(depth)

    def visit_moinpage_list(self, element):
        """
        Function called to handle the conversion of list.

        It will called a specific function to handle (un)ordered list,
        with the appropriate DocBook tag.

        Or a specific function to handle definition list.
        """
        item_label_generate = element.get(moin_page('item-label-generate'))
        if 'ordered' == item_label_generate:
            attrib = {}
            # Get the list-style-type to define correctly numeration
            list_style_type = element.get(moin_page('list-style-type'))
            if 'upper-alpha' == list_style_type:
                attrib[docbook('numeration')] = 'upperalpha'
            elif 'upper-roman' == list_style_type:
                attrib[docbook('numeration')] = 'upperroman'
            elif 'lower-alpha' == list_style_type:
                attrib[docbook('numeration')] = 'loweralpha'
            elif 'lower-roman' == list_style_type:
                attrib[docbook('numeration')] = 'lowerroman'
            else:
                attrib[docbook('numeration')] = 'arabic'

            return self.handle_simple_list(docbook.orderedlist,
                                           element, attrib=attrib)
        elif 'unordered' == item_label_generate:
            return self.handle_simple_list(docbook.itemizedlist,
                                           element, attrib={})
        else:
            return self.new_copy(docbook.variablelist, element, attrib={})

    def visit_moinpage_list_item(self, element):
        """
        We can be sure we will have a varlist entry, because the
        two other kind of list we support will ignore <list-item>
        tag.
        """
        return self.new_copy(docbook.varlistentry, element, attrib={})

    def visit_moinpage_list_item_body(self, element):
        items = []
        for child in element:
            if isinstance(child, ET.Element):
                r = self.visit(child)
                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                items.extend(r)
            else:
                an_item = ET.Element(docbook.para, attrib={}, children=child)
                items.append(an_item)
        return ET.Element(docbook.listitem, attrib={}, children=items)

    def visit_moinpage_list_item_label(self, element):
        """
        In our DOM Tree, <list-item-label> only occur for a
        list of definition, so we can convert it as a term
        in the DocBook tree.
        """
        return self.new_copy(docbook.term, element, attrib={})

    def visit_moinpage_note(self, element):
        note_class = element.get(moin_page('note-class'))
        # We only convert footnote, we do not convert endnote yet
        if note_class != 'footnote':
            return

        # We will check the presence of a body
        body = None
        for child in element:
            if isinstance(child, ET.Element):
                if child.tag.uri == moin_page:
                    if child.tag.name == 'note-body':
                        body = self.do_children(child)
        # We process note only with note-body child
        if not(body):
            return

        body = self.new(docbook.para, attrib={}, children=body)
        return self.new(docbook.footnote, attrib={}, children=[body])

    def visit_moinpage_table(self, element):
        # TODO : Attributes conversion
        return self.new_copy(docbook.table, element, attrib={})

    def visit_moinpage_table_body(self, element):
        # TODO : Attributes conversion
        return self.new_copy(docbook.tbody, element, attrib={})

    def visit_moinpage_table_cell(self, element):
        attrib = {}
        rowspan = element.get(moin_page('number-rows-spanned'))
        colspan = element.get(moin_page('number-columns-spanned'))
        print "rowspan : %s" % rowspan
        if rowspan:
            attrib[docbook.rowspan] = rowspan
        if colspan:
            attrib[docbook.colspan] = colspan
        return self.new_copy(docbook.td, element, attrib=attrib)

    def visit_moinpage_table_header(self, element):
        # TODO : Attributes conversion
        return self.new_copy(docbook.thead, element, attrib={})

    def visit_moinpage_table_footer(self, element):
        # TODO : Attributes conversion
        return self.new_copy(docbook.tfoot, element, attrib={})

    def visit_moinpage_table_row(self, element):
        #TODO : Attributes conversion
        return self.new_copy(docbook.tr, element, attrib={})

    def handle_simple_list(self, docbook_tag, element, attrib):
        list_items = []
        for child in element:
            if isinstance(child, ET.Element):
                # We do not care about <list-item>
                if child.tag.name != 'list-item':
                    r = self.visit(child)
                else:
                    r = self.do_children(child)

                if r is None:
                    r = ()
                elif not isinstance(r, (list, tuple)):
                    r = (r, )
                list_items.extend(r)
        return ET.Element(docbook_tag, attrib=attrib, children=list_items)

    def visit_moinpage_page(self, element):
        for item in element:
            if item.tag.uri == moin_page and item.tag.name == 'body':
                c = self.do_children(item)
                if not(c):
                    self.section_children = sorted(self.section_children.items(),
                                                   reverse=True)
                    section = None
                    for k, v in self.section_children:
                        if section:
                            section_tag = 'sect%d' % k
                            v.append(section)
                            section = ET.Element(docbook(section_tag),
                                                 attrib={}, children=v)
                        else:
                            section_tag = 'sect%d' % k
                            section = ET.Element(docbook(section_tag),
                                                 attrib={}, children=v)
                    return ET.Element(docbook.article,
                                      attrib={}, children=[section])
                else:
                    return ET.Element(docbook.article, attrib={}, children=c)

        raise RuntimeError('page:page need to contain exactly one page body tag, got %r'
                            % element[:])

    def visit_moinpage_p(self, element):
        return self.new_copy(docbook.para, element, attrib={})

    def visit_moinpage_span(self, element):
        """
        The span element is used in the DOM Tree to define some specific formatting.
        So each attribute will give different resulting tag.

        TODO : Add support for text-decoration attribute
        TODO : Add support for font-size attribute
        """
        # Check for the attributes of span
        for key, value in element.attrib.iteritems():
            if key.name == 'baseline-shift':
                if value == 'super':
                    return self.new_copy(docbook.superscript,
                                         element, attrib={})
                if value == 'sub':
                    return self.new_copy(docbook.subscript, element, attrib={})

        return self.new_copy(docbook.phrase, element, attrib={})

    def visit_moinpage_strong(self, element):
        attrib = {}
        key = docbook.role
        attrib[key] = "strong"
        return self.new_copy(docbook.emphasis, element, attrib=attrib)

from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(Converter._factory, type_moin_document,
    Type('application/docbook+xml'))
