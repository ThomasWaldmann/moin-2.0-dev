# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - New Page macro

    Lets you create new page using an optional template, button text
    and parent page (for automatic subpages).

    Usage:

        <<NewPage(template, buttonLabel, parentPage)>>

    Examples:

        <<NewPage>>

            Create an input field with 'Create New Page' button. The new
            page will not use a template.

        <<NewPage(BugTemplate, Create New Bug, MoinMoinBugs)>>

            Create an input field with button labeled 'Create New
            Bug'.  The new page will use the BugTemplate template,
            and create the page as a subpage of MoinMoinBugs.

    Thanks to Jos Yule's "blogpost" action and his modified Form for
    giving me the pieces I needed to figure all this stuff out: MoinMoin:JosYule

    @copyright: 2004 Vito Miliano (vito_moinnewpagewithtemplate@perilith.com),
                2004 by Nir Soffer <nirs@freeshell.org>,
                2004 Alexander Schremmer <alex AT alexanderweb DOT de>,
                2006-2008 MoinMoin:ReimarBauer,
                2008 MoinMoin:RadomirDopieralski,
                2008 MoinMoin:ThomasWaldmann.
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.macro2._base import MacroBlockBase
from MoinMoin.util.tree import html
from MoinMoin import wikiutil

class Macro(MacroBlockBase):
    def macro(self, template=u'', button_label=u'', parent_page=u'', name_template=u'%s'):
        request = self.request
        _ = request.getText
        self.template = template
        if button_label:
            # Try to get a translation, this will probably not work in
            # most cases, but better than nothing.
            self.label = request.getText(button_label)
        else:
            self.label = _("Create New Page")
        if parent_page == '@ME' and request.user.valid:
            self.parent = request.user.name
        elif parent_page == '@SELF':
            self.parent = self.page_name
        else:
            self.parent = parent_page
        self.nametemplate = name_template
        requires_input = '%s' in self.nametemplate

        xml = [
            u'<form xmlns="%s" class="macro" method="post" action="%s/%s">' % (
                html,
                self.request.getScriptname(),
                wikiutil.quoteWikinameURL(self.page_name)),
            u'<div>',
            u'<input type="hidden" name="action" value="newpage" />',
            u'<input type="hidden" name="parent" value="%s" />' % wikiutil.escape(self.parent, 1),
            u'<input type="hidden" name="template" value="%s" />' % wikiutil.escape(self.template, 1),
            u'<input type="hidden" name="nametemplate" value="%s" />' % wikiutil.escape(self.nametemplate, 1),
        ]
        if requires_input:
            xml += [
                u'<input type="text" name="pagename" size="30" />',
            ]
        xml += [
            u'<input type="submit" value="%s" />' % wikiutil.escape(self.label, 1),
            u'</div>',
            u'</form>',
            ]
        return ET.XML(u''.join(xml))

