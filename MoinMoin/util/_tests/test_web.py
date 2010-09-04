# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.util.web Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import web
from MoinMoin.widget import html


class TestMakeSelection:
    """util.web: creating html select"""

    values = ('one', 'two', 'simple', ('complex', 'A tuple & <escaped text>'))

    html._SORT_ATTRS = 1
    expected = (
        u'<select name="test" size="1">'
        u'<option value="one">one</option>'
        u'<option value="two">two</option>'
        u'<option value="simple">simple</option>'
        u'<option value="complex">A tuple &amp; &lt;escaped text&gt;</option>'
        u'</select>'
    )

    def testMakeSelectNoSelection(self):
        """util.web: creating html select with no selection"""
        expected = self.expected
        result = unicode(web.makeSelection('test', self.values, size=1))
        assert result == expected

    def testMakeSelectNoSelection2(self):
        """util.web: creating html select with non existing selection"""
        expected = self.expected
        result = unicode(web.makeSelection('test', self.values, 'three', size=1))
        assert result == expected

    def testMakeSelectWithSelectedItem(self):
        """util.web: creating html select with selected item"""
        expected = self.expected.replace('value="two"', 'selected value="two"')
        result = unicode(web.makeSelection('test', self.values, 'two', size=1))
        assert result == expected


coverage_modules = ['MoinMoin.util.web']

