"""
MoinMoin - Pygments driven syntax highlighting input converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import pygments
import pygments.formatter
import pygments.lexers
from pygments.token import Token

from MoinMoin.util.mime import Type, type_moin_document
from MoinMoin.util.tree import moin_page


class TreeFormatter(pygments.formatter.Formatter):
    classes = {
            Token.Comment: 'Comment',
            Token.Comment.Preproc: 'Preprc',
            Token.Generic.Deleted: 'DiffRemoved',
            Token.Generic.Heading: 'Comment',
            Token.Generic.Inserted: 'DiffAdded',
            Token.Generic.Strong: 'DiffChanged',
            Token.Generic.Subheading: 'DiffSeparator',
            Token.Keyword: 'ResWord',
            Token.Keyword.Constant: 'ConsWord',
            Token.Name.Builtin: 'ResWord',
            Token.Name.Constant: 'ConsWord',
            Token.Name: 'ID',
            Token.Number: 'Number',
            Token.Operator.Word: 'ResWord',
            Token.String: 'String',
            Token.String.Char: 'Char',
            Token.String.Escape: 'SPChar',
    }

    def _append(self, type, value, element):
        class_ = self.classes.get(type)
        if class_:
            value = moin_page.span(attrib={moin_page.class_: class_}, children=(value, ))
        element.append(value)

    def format(self, tokensource, element):
        lastval = ''
        lasttype = None

        for ttype, value in tokensource:
            while ttype and ttype not in self.classes:
                ttype = ttype.parent
            if ttype == lasttype:
                lastval += value
            else:
                if lastval:
                    self._append(lasttype, lastval, element)
                lastval = value
                lasttype = ttype

        if lastval:
            self._append(lasttype, lastval, element)


class Converter(object):
    def __init__(self, request, type):
        self.request, self.type = request, type

    def __call__(self, content, arguments=None):
        blockcode = moin_page.blockcode(attrib={moin_page.class_: 'codearea'})

        content = u'\n'.join(content)
        lexer = pygments.lexers.get_lexer_by_name(self.type)
        pygments.highlight(content, lexer, TreeFormatter(), blockcode)

        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(children=(body, ))


def _factory(_request, type_input, type_output, **kw):
    if type_moin_document.issupertype(type_output):
        if Type('text/x-diff').issupertype(type_input):
            pygments_type = 'diff'
        elif Type('text/x-irclog').issupertype(type_input):
            pygments_type = 'irc'
        elif (Type('text/x-python').issupertype(type_input) or
            Type('x-moin/format;name=python').issupertype(type_input)):
            pygments_type = 'python'
        else:
            return

        def real_factory(request):
            return Converter(request, pygments_type)
        return real_factory

from . import default_registry
default_registry.register(_factory)
