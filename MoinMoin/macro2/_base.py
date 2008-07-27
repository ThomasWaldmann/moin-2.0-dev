"""
MoinMoin - Macro base class

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util import namespaces

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

