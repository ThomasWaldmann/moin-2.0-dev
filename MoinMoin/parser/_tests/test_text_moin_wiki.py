# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.parser.text_moin_wiki Tests

    TODO: these are actually parser+formatter tests. We should have
    parser only tests here.

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest # LEGACY UNITTEST, PLEASE DO NOT IMPORT unittest IN NEW TESTS, PLEASE CONSULT THE py.test DOCS
import re
from StringIO import StringIO

import py

from MoinMoin.Page import Page
from MoinMoin.parser.text_moin_wiki import Parser


class ParserTestCase(unittest.TestCase):
    """ Helper class that provide a parsing method """

    def parse(self, body):
        """Parse body and return html

        Create a page with body, then parse it and format using html formatter
        """
        assert body is not None
        self.request.reset()
        page = Page(self.request, 'ThisPageDoesNotExistsAndWillNeverBeReally')
        page.set_raw_body(body)
        from MoinMoin.formatter.text_html import Formatter
        page.formatter = Formatter(self.request)
        self.request.formatter = page.formatter
        page.formatter.setPage(page)
        page.hilite_re = None

        output = StringIO()
        saved_write = self.request.write
        self.request.write = output.write
        self.request.page = page
        try:
            page.send_page(content_only=True, do_cache=False)
        finally:
            self.request.write = saved_write
        return output.getvalue()


class TestParagraphs(ParserTestCase):
    """ Test paragraphs creating

    All tests ignoring white space in output
    """

    def testFirstParagraph(self):
        """ parser.wiki: first paragraph should be in <p> """
        py.test.skip("Broken because of line numbers")
        result = self.parse('First')
        expected = re.compile(r'<p>\s*First\s*</p>')
        self.assert_(expected.search(result),
                      '"%s" not in "%s"' % (expected.pattern, result))

    def testEmptyLineBetweenParagraphs(self):
        """ parser.wiki: empty line separates paragraphs """
        py.test.skip("Broken because of line numbers")
        result = self.parse('First\n\nSecond')
        expected = re.compile(r'<p>\s*Second\s*</p>')
        self.assert_(expected.search(result),
                     '"%s" not in "%s"' % (expected.pattern, result))

    def testParagraphAfterBlockMarkup(self):
        """ parser.wiki: create paragraph after block markup """
        py.test.skip("Broken because of line numbers")

        markup = (
            '----\n',
            '[[en]]\n',
            '|| table ||\n',
            '= heading 1 =\n',
            '== heading 2 ==\n',
            '=== heading 3 ===\n',
            '==== heading 4 ====\n',
            '===== heading 5 =====\n',
            )
        for item in markup:
            text = item + 'Paragraph'
            result = self.parse(text)
            expected = re.compile(r'<p.*?>\s*Paragraph\s*</p>')
            self.assert_(expected.search(result),
                         '"%s" not in "%s"' % (expected.pattern, result))


class TestHeadings(ParserTestCase):
    """ Test various heading problems """

    def setUp(self):
        """ Require show_section_numbers = 0 to workaround counter
        global state saved in request.
        """
        self.config = self.TestConfig(show_section_numbers=0)

    def tearDown(self):
        del self.config

    def testIgnoreWhiteSpaceAroundHeadingText(self):
        """ parser.wiki: ignore white space around heading text

        See bug: TableOfContentsBreakOnExtraSpaces.

        Does not test mapping of '=' to h number, or valid html markup.
        """
        py.test.skip("Broken because of line numbers")
        tests = (
            '=  head =\n', # leading
            '= head  =\n', # trailing
            '=  head  =\n' # both
                 )
        expected = self.parse('= head =')
        for test in tests:
            result = self.parse(test)
            self.assertEqual(result, expected,
                'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestTOC(ParserTestCase):

    def setUp(self):
        """ Require show_section_numbers = 0 to workaround counter
        global state saved in request.
        """
        self.config = self.TestConfig(show_section_numbers=0)

    def tearDown(self):
        del self.config

    def testHeadingWithWhiteSpace(self):
        """ parser.wiki: TOC links to headings with white space

        See bug: TableOfContentsBreakOnExtraSpaces.

        Does not test TOC or heading formating, just verify that spaces
        around heading text does not matter.
        """
        standard = """
[[TableOfContents]]
= heading =
Text
"""
        withWhitespace = """
[[TableOfContents]]
=   heading   =
Text
"""
        expected = self.parse(standard)
        result = self.parse(withWhitespace)
        self.assertEqual(result, expected,
            'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestDateTimeMacro(ParserTestCase):
    """ Test DateTime macro

    If you get failures in these tests, it might be because:
    * libc problems (some are just broken/incorrect)
    * changes in the timezone of a country (e.g. Lithuania seems
      to have changed the tz it is in, see comments below). Our
      timestamps are in UTC, but we use mktime(), which is the inverse
      function of localtime() (NOT of gmtime()), so we have to fix
      our calculation with the tzoffset. Problem: we can't easily find
      out the tzoffset some location had at some time in the past.
      Badly enough, we also don't have an inverse function of gmtime().

    If some of these tests fail and show differences of e.g. 1 hour,
    you might see your timestamps being off by 1 hour in the wiki.
    If you can live with that, this will cause no other problems.
    """

    text = 'AAA %s AAA'
    needle = re.compile(text % r'(.+)')
    _tests = (
        # test                                   expected
        (u'[[DateTime(259200)]]',                '1970-01-04 00:00:00'),
        (u'[[DateTime(2003-03-03T03:03:03)]]',   '2003-03-03 03:03:03'),
        (u'[[DateTime(2000-01-01T00:00:00Z)]]',  '2000-01-01 00:00:00'), # works for Europe/Vilnius
        (u'[[Date(2002-02-02T01:02:03Z)]]',      '2002-02-02'),
        (u'[[DateTime(1970-01-06T00:00:00)]]',   '1970-01-06 00:00:00'), # fails e.g. for Europe/Vilnius
        )

    def setUp(self):
        """ Require default date and time format config values """
        self.config = self.TestConfig(defaults=('date_fmt', 'datetime_fmt'))

    def tearDown(self):
        del self.config

    def testDateTimeMacro(self):
        """ parser.wiki: DateTime macro """
        note = """

    If this fails, it is likely a problem in your python / libc,
    not in moin.  See also: <http://sourceforge.net/tracker/index.php?func=detail&aid=902172&group_id=5470&atid=105470>

    It can also be related to TZ changes a country historically made.
    """

        for test, expected in self._tests:
            html = self.parse(self.text % test)
            result = self.needle.search(html).group(1)
            self.assertEqual(result, expected,
                'Expected "%(expected)s" but got "%(result)s"; %(note)s' % locals())


class TestTextFormatingTestCase(ParserTestCase):
    """ Test wiki markup """

    text = 'AAA %s AAA'
    needle = re.compile(text % r'(.+)')
    _tests = (
        # test,                     expected
        ('no format',               'no format'),
        ("''em''",                  '<em>em</em>'),
        ("'''bold'''",              '<strong>bold</strong>'),
        ("__underline__",           '<span class="u">underline</span>'),
        ("'''''Mix''' at start''",  '<em><strong>Mix</strong> at start</em>'),
        ("'''''Mix'' at start'''",  '<strong><em>Mix</em> at start</strong>'),
        ("'''Mix at ''end'''''",    '<strong>Mix at <em>end</em></strong>'),
        ("''Mix at '''end'''''",    '<em>Mix at <strong>end</strong></em>'),
        )

    def testTextFormating(self):
        """ parser.wiki: text formating """
        for test, expected in self._tests:
            html = self.parse(self.text % test)
            result = self.needle.search(html).group(1)
            self.assertEqual(result, expected,
                             'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestCloseInlineTestCase(ParserTestCase):

    def testCloseOneInline(self):
        """ parser.wiki: close open inline tag when block close """
        py.test.skip("Broken because of line numbers")
        cases = (
            # test, expected
            ("text'''text\n", r"<p>text<strong>text\s*</strong></p>"),
            ("text''text\n", r"<p>text<em>text\s*</em></p>"),
            ("text__text\n", r"<p>text<span class=\"u\">text\s*</span></p>"),
            ("text ''em '''em strong __em strong underline",
             r"text <em>em <strong>em strong <span class=\"u\">em strong underline"
             r"\s*</span></strong></em></p>"),
            )
        for test, expected in cases:
            needle = re.compile(expected)
            result = self.parse(test)
            self.assert_(needle.search(result),
                         'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestInlineCrossing(ParserTestCase):
    """
    This test case fail with current parser/formatter and should be fixed in 2.0
    """

    def disabled_testInlineCrossing(self):
        """ parser.wiki: prevent inline crossing <a><b></a></b> """

        expected = (r"<p><em>a<strong>ab</strong></em><strong>b</strong>\s*</p>")
        test = "''a'''ab''b'''\n"
        needle = re.compile(expected)
        result = self.parse(test)
        self.assert_(needle.search(result),
                     'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestEscapeHTML(ParserTestCase):

    def testEscapeInTT(self):
        """ parser.wiki: escape html markup in `tt` """
        test = 'text `<escape-me>` text\n'
        self._test(test)

    def testEscapeInTT2(self):
        """ parser.wiki: escape html markup in {{{tt}}} """
        test = 'text {{{<escape-me>}}} text\n'
        self._test(test)

    def testEscapeInPre(self):
        """ parser.wiki: escape html markup in pre """
        test = '''{{{
<escape-me>
}}}
'''
        self._test(test)

    def testEscapeInPreHashbang(self):
        """ parser.wiki: escape html markup in pre with hashbang """
        test = '''{{{#!
<escape-me>
}}}
'''
        self._test(test)

    def testEscapeInPythonCodeArea(self):
        """ parser.wiki: escape html markup in python code area """
        test = '''{{{#!python
#<escape-me>
}}}
'''
        self._test(test)

    def testEscapeInGetTextMacro(self):
        """ parser.wiki: escape html markup in GetText macro """
        test = "text [[GetText(<escape-me>)]] text"
        self._test(test)

    def testEscapeInGetTextFormatted(self):
        """ parser.wiki: escape html markup in getText formatted call """
        test = self.request.getText('<escape-me>', formatted=1)
        self._test(test)

    def testEscapeInGetTextFormatedLink(self):
        """ parser.wiki: escape html markup in getText formatted call with link """
        test = self.request.getText('["<escape-me>"]', formatted=1)
        self._test(test)

    def testEscapeInGetTextUnFormatted(self):
        """ parser.wiki: escape html markup in getText non formatted call """
        test = self.request.getText('<escape-me>', formatted=0)
        self._test(test)

    def _test(self, test):
        expected = r'&lt;escape-me&gt;'
        result = self.parse(test)
        self.assert_(re.search(expected, result),
                     'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestEscapeWikiTableMarkup(ParserTestCase):

    def testEscapeInTT(self):
        """ parser.wiki: escape wiki table markup in `tt` """
        test = 'text `||<tablewidth="80"> Table ||` text\n'
        self.do(test)

    def testEscapeInTT2(self):
        """ parser.wiki: escape wiki table markup in {{{tt}}} """
        test = 'text {{{||<tablewidth="80"> Table ||}}} text\n'
        self.do(test)

    def testEscapeInPre(self):
        """ parser.wiki: escape wiki table  markup in pre """
        test = '''{{{
||<tablewidth="80"> Table ||
}}}
'''
        self.do(test)

    def testEscapeInPreHashbang(self):
        """ parser.wiki: escape wiki table  markup in pre with hashbang """
        test = '''{{{#!
||<tablewidth="80"> Table ||
}}}
'''
        self.do(test)

    def testEscapeInPythonCodeArea(self):
        """ parser.wiki: escape wiki table markup in python code area """
        test = '''{{{#!python
# ||<tablewidth="80"> Table ||
}}}
'''
        self.do(test)

    def do(self, test):
        expected = r'&lt;tablewidth="80"&gt;'
        result = self.parse(test)
        self.assert_(re.search(expected, result),
                     'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestRule(ParserTestCase):
    """ Test rules markup """

    def testNotRule(self):
        """ parser.wiki: --- is no rule """
        py.test.skip("Broken because of line numbers")
        result = self.parse('---')
        expected = '---' # inside <p>
        self.assert_(expected in result,
                     'Expected "%(expected)s" but got "%(result)s"' % locals())

    def testStandardRule(self):
        """ parser.wiki: ---- is standard rule """
        py.test.skip("Broken because of line numbers")
        result = self.parse('----')
        expected = '<hr>'
        self.assert_(expected in result,
                     'Expected "%(expected)s" but got "%(result)s"' % locals())

    def testVariableRule(self):
        """ parser.wiki: ----- rules with size """
        py.test.skip("Broken because of line numbers")

        for size in range(5, 11):
            test = '-' * size
            result = self.parse(test)
            expected = '<hr class="hr%d">' % (size - 4)
            self.assert_(expected in result,
                     'Expected "%(expected)s" but got "%(result)s"' % locals())

    def testLongRule(self):
        """ parser.wiki: ------------ long rule shortened to hr6 """
        py.test.skip("Broken because of line numbers")
        test = '-' * 254
        result = self.parse(test)
        expected = '<hr class="hr6">'
        self.assert_(expected in result,
                     'Expected "%(expected)s" but got "%(result)s"' % locals())


class TestBlock(ParserTestCase):
    cases = (
        # test, block start
        ('----\n', '<hr'),
        ('= Heading =\n', '<h2'),
        ('{{{\nPre\n}}}\n', '<pre'),
        ('{{{\n#!python\nPre\n}}}\n', '<div'),
        ('|| Table ||', '<div'),
        (' * unordered list\n', '<ul'),
        (' 1. ordered list\n', '<ol'),
        (' indented text\n', '<ul'),
        )

    def testParagraphBeforeBlock(self):
        """ parser.wiki: paragraph closed before block element """
        py.test.skip("Broken because of line numbers")
        text = """AAA
%s
"""
        for test, blockstart in self.cases:
            # We dont test here formatter white space generation
            expected = r'<p>AAA\s*</p>\n+%s' % blockstart
            needle = re.compile(expected, re.MULTILINE)
            result = self.parse(text % test)
            match = needle.search(result)
            self.assert_(match is not None,
                         'Expected "%(expected)s" but got "%(result)s"' % locals())

    def testEmptyLineBeforeBlock(self):
        """ parser.wiki: empty lines before block element ignored

        Empty lines separate paragraphs, but should be ignored if a block
        element follow.

        Currently an empty paragraph is created, which make no sense but
        no real harm.
        """
        py.test.skip("Broken because of line numbers")
        text = """AAA

%s
"""
        for test, blockstart in self.cases:
            expected = r'<p>AAA\s*</p>\n+%s' % blockstart
            needle = re.compile(expected, re.MULTILINE)
            result = self.parse(text % test)
            match = needle.search(result)
            self.assert_(match is not None,
                         'Expected "%(expected)s" but got "%(result)s"' % locals())

    def testUrlAfterBlock(self):
        """ parser.wiki: tests url after block element """
        case = 'some text {{{some block text\n}}} and a URL http://moinmo.in/'

        result = self.parse(case)
        assert result.find('and a URL <a ') > -1

    def testWikiNameAfterBlock(self):
        """ parser.wiki: tests url after block element """
        case = 'some text {{{some block text\n}}} and a WikiName'

        result = self.parse(case)
        assert result.find('and a <a ') > -1

    def testColorizedPythonParserAndNestingPreBrackets(self):
        """ tests nested {{{ }}} for the python colorized parser
        """

        raw = """{{{
#!python
import re
pattern = re.compile(r'{{{This is some nested text}}}')}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        assert "r'{{{This is some nested text}}}'" in output

    def testColorizedPythonParserAndNestingPreBracketsWithLinebreak(self):
        """ tests nested {{{ }}} for the python colorized parser
        """

        raw = """{{{
#!python
import re
pattern = re.compile(r'{{{This is some nested text}}}')
}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        assert "r'{{{This is some nested text}}}'" in output

    def testNestingPreBrackets(self):
        """ tests nested {{{ }}} for the wiki parser
        """

        raw = """{{{
Example
You can use {{{brackets}}}}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        assert 'You can use {{{brackets}}}' in output

    def testNestingPreBracketsWithLinebreak(self):
        """ tests nested {{{ }}} for the wiki parser
        """

        raw = """{{{
Example
You can use {{{brackets}}}
}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        print output
        assert 'You can use {{{brackets}}}' in output

    def testTextBeforeNestingPreBrackets(self):
        """ tests text before nested {{{ }}} for the wiki parser
        """

        raw = """Example
        {{{
You can use {{{brackets}}}}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        assert 'Example <span class="anchor" id="line-0-1"></span><ul><li style="list-style-type:none"><span class="anchor" id="line-0-2"></span><pre>You can use {{{brackets}}}</pre>' in output

    def testManyNestingPreBrackets(self):
        """ tests two nestings  ({{{ }}} and {{{ }}}) in one line for the wiki parser
        """
        py.test.skip("Broken because not implemented yet")

        raw = """{{{
Test {{{brackets}}} and test {{{brackets}}}
}}}"""
        output = self.parse(raw)
        output = ''.join(output)
        result = '</span><p><pre>Test {{{brackets}}} and test {{{brackets}}}' in output
        expected = True

        assert expected == result

    def testMultipleShortPreSections(self):
        """
        tests two single {{{ }}} in one line
        """
        raw = 'def {{{ghi}}} jkl {{{mno}}} pqr'
        output = ''.join(self.parse(raw))
        # expected output copied from 1.5
        expected = 'def <tt>ghi</tt> jkl <tt>mno</tt><span class="anchor" id="line-0-1"></span>pqr'
        assert expected in output

class TestLinkingMarkup(ParserTestCase):
    """ Test wiki markup """

    text = 'AAA %s AAA'
    needle = re.compile(text % r'(.+)')
    _tests = (
        # test,                       expected
        ('["something"]',             '<a class="nonexistent" href="./something">something</a>'),
        ("['something']",             "['something']"),
        ('MoinMoin:"something"',      '<a class="interwiki" href="http://moinmoin.wikiwikiweb.de/something" title="MoinMoin">something</a>'),
        ('MoinMoin:"with space"',     '<a class="interwiki" href="http://moinmoin.wikiwikiweb.de/with%20space" title="MoinMoin">with space</a>'),
        ('RFC:"1 2 3"',               '<a class="interwiki" href="http://www.ietf.org/rfc/rfc1%202%203" title="RFC">1 2 3</a>'),
        ("RFC:'something else'",      "RFC:'something else'"),
        ('["with "" quote"]',         '<a class="nonexistent" href="./with%20%22%20quote">with " quote</a>'),
        ('MoinMoin:"with "" quote"',  '<a class="interwiki" href="http://moinmoin.wikiwikiweb.de/with%20%22%20quote" title="MoinMoin">with " quote</a>'),
        )

    def testTextFormating(self):
        """ parser.wiki: text formating """
        together_test = []
        together_expected = []
        for test, expected in self._tests:
            html = self.parse(self.text % test)
            result = self.needle.search(html).group(1)
            assert result == expected
            together_test.append(test)
            together_expected.append(expected)

        # now test all together to make sure one quoting doesn't
        # "leak" into the next
        for joint in ('', 'lala " lala ', 'lala "" lala '):
            test = joint.join(together_test)
            expected = joint.join(together_expected)
            html = self.parse(self.text % test)
            result = self.needle.search(html).group(1)
            assert result == expected


coverage_modules = ['MoinMoin.parser.text_moin_wiki']