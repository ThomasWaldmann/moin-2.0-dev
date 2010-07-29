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
    def __init__(self, request, name=None, mimetype=None):
        """
        Create a Pygments Converter, either name (the pygments alias name / short
        name of the wanted lexer) or the mimetype needs to be given.

        @param name: pygments lexer name
        @param mimetype: mimetype for pygments lexer lookup
        """
        self.request, self.name, self.mimetype = request, name, mimetype
        assert name or mimetype

    def __call__(self, content, arguments=None):
        blockcode = moin_page.blockcode(attrib={moin_page.class_: 'codearea'})

        content = u'\n'.join(content)
        if self.name:
            lexer = pygments.lexers.get_lexer_by_name(self.name)
        elif self.mimetype:
            lexer = pygments.lexers.get_lexer_for_mimetype(self.mimetype)
        pygments.highlight(content, lexer, TreeFormatter(), blockcode)

        body = moin_page.body(children=(blockcode, ))
        return moin_page.page(children=(body, ))


def _factory(type_input, type_output, **kw):
    if type_moin_document.issupertype(type_output):
        pygments_name = None
        # first we check the input type against all mimetypes pygments knows:
        for name, short_names, patterns, mime_types in pygments.lexers.get_all_lexers():
            for mt in mime_types:
                if Type(mt).issupertype(type_input):
                    pygments_name = short_names[0]
                    break
            if pygments_name:
                break
        # if we still don't know the lexer name for pygments, check some formats
        # that were supported by special parsers in moin 1.x:
        if pygments_name is None:
            moin_pygments = [
                ('python', 'python'),
                ('diff', 'diff'),
                ('irssi', 'irc'),
                ('irc', 'irc'),
                ('java', 'java'),
                ('cplusplus', 'cpp'),
                ('pascal', 'pascal'),
            ]
            for moin_format, pygments_name in moin_pygments:
                if Type('x-moin/format;name=%s' % moin_format).issupertype(type_input):
                    break
            else:
                pygments_name = None

        if pygments_name:
            def real_factory(request):
                return Converter(request, name=pygments_name)
            return real_factory


from . import default_registry
# Pygments type detection is rather expensive, therefore we want to register
# after all normal parsers but before the compatibility parsers and wildcard
#default_registry.register(_factory, default_registry.PRIORITY_MIDDLE + 1)

