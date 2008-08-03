"""
MoinMoin - GoTo macro

Provides a goto box.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details
"""

from emeraldtree import ElementTree as ET

from MoinMoin.macro2._base import MacroBlockBase
from MoinMoin.util import namespaces

class Macro(MacroBlockBase):
    def macro(self):
        _ = self.request.getText

        return ET.XML("""
<form xmlns="%s" method="get" action="%s/%s">
    <input type="hidden" name="action" value="goto" />
    <p>
        <input type="text" name="target" size="30" />
        <input type="submit" value="%s" />
    </p>
</form>
""" % (namespaces.html,
        self.request.getScriptname(),
        self.page_name,
        _("Go To Page")))

