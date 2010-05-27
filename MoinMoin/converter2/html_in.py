# -*- coding: iso-8859-1 -*-
"""
MoinMoin - HTML input converter

Converts an HTML Tree into an internal document tree.

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from emeraldtree import ElementTree as ET

from MoinMoin import wikiutil
from MoinMoin.util.tree import html, moin_page, xlink
from ._wiki_macro import ConverterMacro

# What is the purpose of this class ?
class ElementException(RuntimeError):
    pass

# I do not know well why we need this
# But all the other convert use it
class _Iter(object):
    """
    Iterator with push back support

    Collected items can be pushed back into the iterator and further calls will
    return them.
    """

    def __init__(self, parent):
        self.__finished = False
        self.__parent = iter(parent)
        self.__prepend = []

    def __iter__(self):
        return self

    def next(self):
        if self.__finished:
            raise StopIteration

        if self.__prepend:
            return self.__prepend.pop(0)

        try:
            return self.__parent.next()
        except StopIteration:
            self.__finished = True
            raise

    def push(self, item):
        self.__prepend.append(item)

class _Stack(list):
    def clear(self):
        del self[1:]

    def pop_name(self, *names):
        """
        Remove anything from the stack including the given node.
        """
        while len(self) > 2 and not self.top_check(*names):
            self.pop()
        self.pop()

    def push(self, elem):
        self.top_append(elem)
        self.append(elem)

    def top(self):
        return self[-1]

    def top_append(self, elem):
        self[-1].append(elem)

    def top_append_ifnotempty(self, elem):
        if elem:
            self.top_append(elem)

    def top_check(self, *names):
        """
        Checks if the name of the top of the stack matches the parameters.
        """
        tag = self[-1].tag
        return tag.uri == moin_page.namespace and tag.name in names

class Converter(ConverterMacro):
    @classmethod
    def _factory(cls, _request, input, output, **kw):
        if output == 'application/x.moin.document' and \
           input == 'application/x-xhtml-moin-page':
            return cls

    # TODO : * Add Arguments
    def __call__(self, content, arguments=None):
        iter_content = _Iter(content)

        # Add Attrib for the page
        body = moin_page.body()
        stack = _Stack(body)

        # Should explore each tag here
        root = moin_page.page(children=[body])
        return root
