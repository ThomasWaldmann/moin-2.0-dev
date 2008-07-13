# -*- coding: iso-8859-1 -*-
"""
MoinMoin - Macro handling

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET
import htmlentitydefs
from HTMLParser import HTMLParser as _HTMLParserBase

from MoinMoin import macro, wikiutil
from MoinMoin.util import namespaces

class _HTMLParser(_HTMLParserBase):
    AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
    IGNOREEND = "img", "hr", "meta", "link", "br"

    def __init__(self, encoding=None):
        self.__stack = []
        self.__builder = ET.TreeBuilder()
        self.encoding = encoding or "iso-8859-1"
        _HTMLParserBase.__init__(self)

    ##
    # Flushes parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        _HTMLParserBase.close(self)
        return self.__builder.close()

    ##
    # (Internal) Handles start tags.

    def handle_starttag(self, tag, attrs):
        tag = ET.QName(tag.lower(), namespaces.html)
        if tag.name == "meta":
            return
        if tag.name in self.AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for key, value in attrs:
                key = ET.QName(key.lower(), namespaces.html)
                attrib[key] = value
        self.__builder.start(tag, attrib)
        if tag in self.IGNOREEND:
            self.__stack.pop()
            self.__builder.end(tag)

    ##
    # (Internal) Handles end tags.

    def handle_endtag(self, tag):
        if not isinstance(tag, ET.QName):
            tag = ET.QName(tag, namespaces.html)
        if tag.name in self.IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in self.AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.__builder.end(tag)

    ##
    # (Internal) Handles character references.

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.__builder.data(chr(char))
        else:
            self.__builder.data(unichr(char))

    ##
    # (Internal) Handles entity references.

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.__builder.data(chr(entity))
            else:
                self.__builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    ##
    # (Internal) Handles character data.

    def handle_data(self, data):
        if isinstance(data, type('')) and is_not_ascii(data):
            # convert to unicode, but only if necessary
            data = unicode(data, self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary

class _PseudoParser(object):
    def __init__(self, request):
        self.request = request
        self.form = request.form

        self.formatter = wikiutil.searchAndImportPlugin(request.cfg, "formatter", 'text/html')

class Converter(object):
    tag_alt = ET.QName('alt', namespaces.moin_page)
    tag_macro = ET.QName('macro', namespaces.moin_page)
    tag_macro_args = ET.QName('macro-args', namespaces.moin_page)
    tag_macro_body = ET.QName('macro-body', namespaces.moin_page)
    tag_macro_name = ET.QName('macro-name', namespaces.moin_page)
    tag_page_href = ET.QName('page-href', namespaces.moin_page)

    @classmethod
    def _factory(cls, input, output):
        if input == 'application/x-moin-document' and \
                output == 'application/x-moin-document;macros=expandall':
            return cls()

    def handle_macro(self, elem, page_href):
        name = elem.get(self.tag_macro_name)
        args = elem.get(self.tag_macro_args)

        elem_body = ET.Element(self.tag_macro_body)

        try:
            ret = self.macro.execute(name, args)
            parser = _HTMLParser()
            parser.feed(ret)
            doc = parser.close()
            elem_body.append(doc)
        except ImportError, err:
            errmsg = unicode(err)
            if not name in errmsg:
                raise
            alt = elem.get(self.tag_alt, None)
            if alt:
                attrib_error = {ET.QName('title', namespaces.moin_page): errmsg}
                elem_error = ET.Element(ET.QName('span', namespaces.moin_page), attrib=attrib_error)
                elem_error.append(alt)
                elem_body.append(elem_error)
            else:
                elem_body.append(errmsg)

        elem.append(elem_body)

    def recurse(self, elem, page_href):
        page_href = elem.get(self.tag_page_href, page_href)

        if elem.tag == self.tag_macro:
            yield elem, page_href

        for child in elem:
            if isinstance(child, ET.Node):
                for i in self.recurse(child, page_href):
                    yield i

    def __call__(self, tree, request):
        self.macro = macro.Macro(_PseudoParser(request))

        for elem, page_href in self.recurse(tree, None):
            self.handle_macro(elem, page_href)

        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
