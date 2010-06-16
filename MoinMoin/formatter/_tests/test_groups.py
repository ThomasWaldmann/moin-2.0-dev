# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.formatter.groups Tests

    @copyright: 2009 by MoinMoin:DmitrijsMilajevs
    @license: GNU GPL, see COPYING for details.
"""

import py.test
py.test.skip("mostly broken")

from  MoinMoin.formatter.groups import Formatter
from MoinMoin.Page import Page
from MoinMoin._tests import become_trusted, create_item

class TestGroupFormatterWikiMarkup(object):

    def get_members(self, text):
        request = self.request
        formatter = Formatter(self.request)

        become_trusted(request)
        create_item(request, u'TestPageGroup', text, mimetype='text/x.moin.wiki')
        page = Page(request, 'TestPageGroup', formatter=formatter)
        page.send_page(content_only=True)

        return formatter.members

    def test_CamelCase(self):
        text = """
 * CamelCase
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'CamelCase' in members

    def test_extended_name(self):
        text = """
 * extended name
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'extended name' in members

    def test_extended_link(self):
        text = """
 * [[extended link]]
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'extended link' in members

    def test_extended_link_with_label(self):
        text = """
 * [[extended link| label]]
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'extended link' in members

    def test_extended_link_and_text(self):
        text = """
 * [[extended link]] other text
 * other text [[extended link]]
 * other text [[extended link]] other text

"""
        members = self.get_members(text)
        assert len(members) == 3
        assert u'extended link other text' in members
        assert u'other text extended link' in members
        assert u'other text extended link other text' in members

    def test_ignore_not_first_level_list(self):
        text = """
 * first level
  * second level
   * [[SomeLink]]
    * forth level
     * and then some...
 * again first level
"""
        members = self.get_members(text)
        assert len(members) == 2
        assert 'first level' in members
        assert 'again first level' in members

    def test_indented_list(self):
        text = """
    * first level
     * second level
      * [[SomeLink|label]]
       * forth level
        * and then some...
    * again first level
"""
        members = self.get_members(text)
        assert len(members) == 2
        assert 'first level' in members
        assert 'again first level' in members

    def test_ignore_other(self):
        text = """
= ignore this =
 * take this

Ignore previous line and this text.
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'take this' in members

    def test_strip_whitespace(self):
        text = """
 *   take this
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'take this' in members


class TestGroupFormatterCreole(object):

    def get_members(self, text):
        request = self.request
        formatter = Formatter(self.request)

        become_trusted(request)
        create_item(request, u'TestPageGroup', text, mimetype='text/x.moin.creole')
        page = Page(request, 'TestPageGroup', formatter=formatter)
        page.send_page(content_only=True)

        return formatter.members

    def test_CamelCase(self):
        text = """
 * CamelCase
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'CamelCase' in members

    def test_extended_name(self):
        text = """
 * extended name
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'extended name' in members

    def test_extended_link(self):
        text = """
 * [[extended link]]
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'extended link' in members

    def test_extended_link_with_label(self):
        text = """
 * [[FrontPage|named link]]
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'FrontPage' in members

    def test_extended_link_and_text(self):
        text = """
 * [[extended link]] other text
 * other text [[extended link]]
 * other text [[extended link]] other text

"""
        members = self.get_members(text)
        assert len(members) == 3
        assert u'extended link other text' in members
        assert u'other text extended link' in members
        assert u'other text extended link other text' in members

    def test_ignore_not_first_level_list(self):
        text = """
* first level
** second level
*** [[SomeLink]]
**** forth level
***** and then some...
* again first level
"""
        members = self.get_members(text)
        assert len(members) == 2
        assert 'first level' in members
        assert 'again first level' in members

    def test_indented_list(self):
        text = """
    * first level
    ** second level
    *** [[SomeLink|label]]
    **** forth level
    ***** and then some...
    * again first level
"""
        members = self.get_members(text)
        assert len(members) == 2
        assert 'first level' in members
        assert 'again first level' in members

    def test_ignore_other(self):
        text = """
= ignore this =
 * take this

Ignore previous line and this text.
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'take this' in members

    def test_strip_whitespace(self):
        text = """
 *   take this
"""
        members = self.get_members(text)
        assert len(members) == 1
        assert u'take this' in members


coverage_modules = ['MoinMoin.formtter.groups']