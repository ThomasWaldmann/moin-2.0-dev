# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Hack: Glue new converters into old parser interface

    @copyright: 2008 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree.ElementTree import ElementTree

from MoinMoin.converter2.creole_in import Converter as CreoleConverter
from MoinMoin.converter2.html_out import ConverterPage as HtmlConverter
from MoinMoin.util import namespaces

class Parser:
    def __init__(self, raw, request, **kw):
        self.raw = raw
        self.request = request

    def format(self, formatter):
        document = CreoleConverter()(self.raw)
        result = HtmlConverter()(document)
        tree = ElementTree(result)
        tree.write(self.request, default_namespace = namespaces.html)

