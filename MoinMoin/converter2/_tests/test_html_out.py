"""
MoinMoin - Tests for MoinMoin.converter2.html_out

@copyright: 2007 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

import py.test

from MoinMoin.converter2.html_out import *

namespaces_string = 'xmlns:page="%s" xmlns:html="%s"' % (namespaces.moin_page, namespaces.html)

class TestConverterBase(object):
    def setup_class(self):
        self.conv = ConverterBase()

    def test_unknown(self):
        page = ElementTree.XML("<page:unknown %s/>" % namespaces_string)
        py.test.raises(Exception, self.conv.recurse, page)

