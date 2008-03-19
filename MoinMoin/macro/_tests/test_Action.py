# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.macro.Action Tests

    @copyright: 2007 MoinMoin:ReimarBauer

    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import macro
from MoinMoin.macro import Action
from MoinMoin.PageEditor import PageEditor


class TestAction:
    """ testing macro Action calling action raw """

    def setup_class(self):
        self.pagename = u'AutoCreatedMoinMoinTemporaryTestPageForAction'
        self.page = PageEditor(self.request, self.pagename)

    def teardown_class(self):
        self.request.cfg.page_backend.remove_item(self.pagename)

    def _make_macro(self):
        """Test helper"""
        from MoinMoin.parser.text import Parser
        from MoinMoin.formatter.text_html import Formatter
        p = Parser("##\n", self.request)
        p.formatter = Formatter(self.request)
        p.formatter.page = self.page
        self.request.formatter = p.formatter
        p.form = self.request.form
        m = macro.Macro(p)
        return m

    def _createTestPage(self, body):
        """ Create temporary page """
        assert body is not None
        self.request.reset()
        self.page.saveText(body, 0)

    def testActionCallingRaw(self):
        """ module_tested: executes raw by macro Action on existing page"""

        expected = '<a href="./AutoCreatedMoinMoinTemporaryTestPageForAction?action=raw">raw</a>'
        text = '= title1 =\n||A||B||\n'
        self._createTestPage(text)
        m = self._make_macro()
        result = Action.macro_Action(m, 'raw')

        assert result == expected


coverage_modules = ['MoinMoin.macro.Action']

