# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.macro.Action Tests

    @copyright: 2007 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import macro
from MoinMoin.macro import Action
from MoinMoin.PageEditor import PageEditor

from MoinMoin._tests import become_trusted, create_page, make_macro

class TestAction:
    """ testing macro Action calling action raw """
    pagename = u'AutoCreatedMoinMoinTemporaryTestPageForAction'

    def testActionCallingRaw(self):
        """ module_tested: executes raw by macro Action on existing page"""
        request = self.request
        become_trusted(request)
        self.page = create_page(request, self.pagename, u'= title1 =\n||A||B||\n')
        m = make_macro(self.request, self.page)
        result = Action.macro_Action(m, 'raw')
        expected = '<a href="/AutoCreatedMoinMoinTemporaryTestPageForAction?action=raw">raw</a>'
        assert result == expected

coverage_modules = ['MoinMoin.macro.Action']

