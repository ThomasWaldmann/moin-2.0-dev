# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MailTo Macro displays an E-Mail address (either a valid mailto:
    link for logged in users or an obfuscated display as given as the macro argument.

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from emeraldtree import ElementTree as ET

from MoinMoin.util import namespaces
from MoinMoin.macro2._base import MacroInlineBase

class Macro(MacroInlineBase):
    def macro(self, email=unicode, text=u''):
        if not email:
            raise ValueError("You need to give an (obfuscated) email address")

        from MoinMoin.mail.sendmail import decodeSpamSafeEmail

        if self.request.user.valid:
            # decode address and generate mailto: link
            email = decodeSpamSafeEmail(email)

            tag_a = ET.QName('a', namespaces.moin_page)
            attr_href_xlink = ET.QName('href', namespaces.xlink)
            result = ET.Element(tag_a, attrib={attr_href_xlink: u'mailto:%s' % email},
                                children=[text or email])

        else:
            # unknown user, maybe even a spambot, so just return text as given in macro args
            if text:
                text += " "

            tag_code = ET.QName('code', namespaces.moin_page)
            result = ET.Element(tag_code, children=[text, "<%s>" % email])

        return result





