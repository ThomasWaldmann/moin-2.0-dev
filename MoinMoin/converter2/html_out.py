"""
@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import namespaces

class ConverterBase(object):
    pass

class Converter(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-moin-document
    """

class ConverterPage(ConverterBase):
    """
    Converter application/x-moin-document -> application/x-xhtml-moin-page
    """

class ConverterDocument(ConverterPage):
    """
    Converter application/x-moin-document -> application/xhtml+xml
    """

