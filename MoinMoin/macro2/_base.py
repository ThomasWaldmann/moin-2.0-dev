"""
MoinMoin - Macro base class

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces, uri

class MacroBase(object):
    """
    Macro base class.

    Supports argument parsing with wikiutil.invoke_extension_function.
    """

    # The output of a immutable macro only depends on the arguments and the content
    immutable = False

    def __init__(self, request, page_name, alt, context, args=None):
        self.request, self.page_name = request, page_name
        self.alt, self.context, self._args = alt, context, args

    def call_macro(self, content):
        try:
            return wikiutil.invoke_extension_function(self.request, self.macro, self._args)
        except ValueError:
            # TODO: Real error
            return 'Error'

    def macro(self):
        raise NotImplementedError

class MacroBlockBase(MacroBase):
    """
    Macro base class for block element macros.

    The macro gets only expanded in block context. In inline context the
    alternative text is used instead.
    """
    def __call__(self, content=()):
        if self.context == 'block':
            return self.call_macro(content)
        return self.alt

class MacroInlineBase(MacroBase):
    """
    Macro base class for inline element macros.

    The macro is wrapped into a paragraph in block context.
    """
    def __call__(self, content=()):
        ret = self.call_macro(content)
        if self.context == 'inline':
            return ret
        return ET.Element(ET.QName('p', namespaces.moin_page), children=[ret])

class MacroInlineOnlyBase(MacroBase):
    """
    Macro base class for strict inline element macros.

    The macro is onl< expanded in inline context. In block context it expands
    to nothing.
    """
    def __call__(self, content=()):
        if self.context == 'inline':
            return self.call_macro(content)

class MacroPageLinkListBase(MacroBlockBase):
    def create_pagelink_list(self, pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        tag_l = ET.QName('list', namespaces.moin_page)
        attr_generate = ET.QName('item-label-generate', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        page_list = ET.Element(tag_l, attrib={attr_generate: ordered and 'ordered' or 'unordered'})
        for pagename in pagenames:
            # TODO: unicode URI
            # This link can never reach pagelinks
            url = str(uri.Uri(scheme='wiki', authority='', path='/' + pagename.encode('utf-8')))
            pagelink = ET.Element(tag_a, attrib={attr_href_xlink: url}, children=[pagename])
            item_body = ET.Element(tag_li_body, children=[pagelink])
            item = ET.Element(tag_li, children=[item_body])
            page_list.append(item)
        return page_list

class MacroNumberPageLinkListBase(MacroBlockBase):
    def create_number_pagelink_list(self, num_pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        tag_l = ET.QName('list', namespaces.moin_page)
        attr_generate = ET.QName('item-label-generate', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)
        tag_code = ET.QName('code', namespaces.moin_page)
        tag_a = ET.QName('a', namespaces.moin_page)
        attr_href_xlink = ET.QName('href', namespaces.xlink)

        num_page_list = ET.Element(tag_l, attrib={attr_generate: ordered and 'ordered' or 'unordered'})
        for num, pagename in num_pagenames:
            num_code = ET.Element(tag_code, children=["%6d " % num])
            # TODO: unicode URI
            # This link can never reach pagelinks
            url = str(uri.Uri(scheme='wiki', authority='', path='/' + pagename.encode('utf-8')))
            pagelink = ET.Element(tag_a, attrib={attr_href_xlink: url}, children=[pagename])
            item_body = ET.Element(tag_li_body, children=[num_code, pagelink])
            item = ET.Element(tag_li, children=[item_body])
            num_page_list.append(item)
        return num_page_list

class MacroDefinitionListBase(MacroBlockBase):
    def create_definition_list(self, items):
        """ creates an ET with a definition list made from items """
        tag_l = ET.QName('list', namespaces.moin_page)
        tag_li = ET.QName('list-item', namespaces.moin_page)
        tag_li_label = ET.QName('list-item-label', namespaces.moin_page)
        tag_li_body = ET.QName('list-item-body', namespaces.moin_page)

        def_list = ET.Element(tag_l)
        for label, body in items:
            item_label = ET.Element(tag_li_label, children=[label])
            item_body = ET.Element(tag_li_body, children=[body])
            item = ET.Element(tag_li, children=[item_label, item_body])
            def_list.append(item)
        return def_list


