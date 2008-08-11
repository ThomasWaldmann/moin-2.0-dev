"""
MoinMoin - Macro base class

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil
from MoinMoin.util import tree, uri

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
        return tree.moin_page.p(children=[ret])

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
        page_list = tree.moin_page.list(attrib={tree.moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for pagename in pagenames:
            # TODO: unicode URI
            # This link can never reach pagelinks
            url = str(uri.Uri(scheme='wiki', authority='', path='/' + pagename.encode('utf-8')))
            pagelink = tree.moin_page.a(attrib={tree.xlink.href: url}, children=[pagename])
            item_body = tree.moin_page.list_item_body(children=[pagelink])
            item = tree.moin_page.list_item(children=[item_body])
            page_list.append(item)
        return page_list

class MacroNumberPageLinkListBase(MacroBlockBase):
    def create_number_pagelink_list(self, num_pagenames, ordered=False):
        """ creates an ET with a list of pagelinks from a list of pagenames """
        page_list = tree.moin_page.list(attrib={tree.moin_page.item_label_generate: ordered and 'ordered' or 'unordered'})
        for num, pagename in num_pagenames:
            num_code = tree.moin_page.code(children=["%6d " % num])
            # TODO: unicode URI
            # This link can never reach pagelinks
            url = str(uri.Uri(scheme='wiki', authority='', path='/' + pagename.encode('utf-8')))
            pagelink = tree.moin_page.a(attrib={attr_href_xlink: url}, children=[pagename])
            item_body = tree.moin_page.list_item_body(children=[num_code, pagelink])
            item = tree.moin_page.list_item(children=[item_body])
            num_page_list.append(item)
        return num_page_list

class MacroDefinitionListBase(MacroBlockBase):
    def create_definition_list(self, items):
        """ creates an ET with a definition list made from items """
        def_list = tree.moin_page.list()
        for label, body in items:
            item_label = tree.moin_page.list_item_label(children=[label])
            item_body = tree.moin_page.list_item_body(children=[body])
            item = tree.moin_page.list_item(children=[item_label, item_body])
            def_list.append(item)
        return def_list


