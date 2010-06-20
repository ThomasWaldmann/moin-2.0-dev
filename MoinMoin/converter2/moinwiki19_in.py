"""
MoinMoin - Moin Wiki 1.9 input converter

@copyright: 2000-2002 Juergen Hermann <jh@web.de>,
            2006-2008 MoinMoin:ThomasWaldmann,
            2007 MoinMoin:ReimarBauer,
            2008-2010 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config, wikiutil
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xlink

from .moinwiki_in import Converter


class ConverterFormat19(Converter):
    @classmethod
    def factory(cls, input, output, request, **kw):
        return cls(request)

    def __init__(self, request):
        self.request = request

    inline_freelink = r"""
         (?:
          (?<![%(u)s%(l)s/])  # require anything not upper/lower/slash before
          |
          ^  # ... or beginning of line
         )
         (?P<freelink_bang>\!)?  # configurable: avoid getting CamelCase rendered as link
         (?P<freelink>
          (?P<freelink_interwiki_ref>
           [A-Z][a-zA-Z]+
          )
          \:
          (?P<freelink_interwiki_page>
           (?=\S*[%(u)s%(l)s0..9]\S* )  # make sure there is something non-blank with at least one alphanum letter following
           [^\s"\'}\]|:,.\)?!]+  # we take all until we hit some blank or punctuation char ...
          )
          |
          (?P<freelink_page>
           (?:
            (%(parent)s)*  # there might be either ../ parent prefix(es)
            |
            ((?<!%(child)s)%(child)s)?  # or maybe a single / child prefix (but not if we already had it before)
           )
           (
            ((?<!%(child)s)%(child)s)?  # there might be / child prefix (but not if we already had it before)
            (?:[%(u)s][%(l)s]+){2,}  # at least 2 upper>lower transitions make CamelCase
           )+  # we can have MainPage/SubPage/SubSubPage ...
           (?:
            \#  # anchor separator          TODO check if this does not make trouble at places where word_rule is used
            \S+  # some anchor name
           )?
          )
          |
          (?P<freelink_email>
           [-\w._+]+  # name
           \@  # at
           [\w-]+(\.[\w-]+)+  # server/domain
          )
         )
         (?:
          (?![%(u)s%(l)s/])  # require anything not upper/lower/slash following
          |
          $  # ... or end of line
         )
    """ % {
        'u': config.chars_upper,
        'l': config.chars_lower,
        'child': re.escape(wikiutil.CHILD_PREFIX),
        'parent': re.escape(wikiutil.PARENT_PREFIX),
    }

    def inline_freelink_repl(self, stack, freelink, freelink_bang=None,
            freelink_interwiki_page=None, freelink_interwiki_ref=None,
            freelink_page=None, freelink_email=None):
        if freelink_bang:
            stack.top_append(freelink)
            return

        attrib = {}

        if freelink_page:
            page = freelink_page.encode('utf-8')
            if '#' in page:
                path, fragment = page.rsplit('#', 1)
            else:
                path, fragment = page, None
            link = Iri(scheme='wiki.local', path=path, fragment=fragment)
            text = freelink_page

        elif freelink_email:
            link = 'mailto:' + freelink_email
            text = freelink_email

        else:
            wikitag_bad = wikiutil.resolve_interwiki(self.request,
                    freelink_interwiki_ref, freelink_interwiki_page)[3]
            if wikitag_bad:
                stack.top_append(freelink)
                return

            link = Iri(scheme='wiki',
                    authority=freelink_interwiki_ref,
                    path='/' + freelink_interwiki_page)
            text = freelink_interwiki_page

        attrib[xlink.href] = link

        element = moin_page.a(attrib, children=[text])
        stack.top_append(element)

    inline_url = r"""
        (?P<url>
            (
                ^
                |
                (?<=
                    \s
                    |
                    [.,:;!?()/=]
                )
            )
            (?P<url_target>
                # TODO: config.url_schemas
                (http|https|ftp|nntp|news|mailto|telnet|file|irc):
                \S+?
            )
            (
                $
                |
                (?=
                    \s
                    |
                    [,.:;!?()]
                    (\s | $)
                )
            )
        )
    """

    def inline_url_repl(self, stack, url, url_target):
        url = Iri(url_target)
        attrib = {xlink.href: url}
        element = moin_page.a(attrib=attrib, children=[url_target])
        stack.top_append(element)

    inline = Converter.inline + (
        inline_freelink,
        inline_url,
    )
    inline_re = re.compile('|'.join(inline), re.X | re.U)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document, type_moin_wiki
default_registry.register(ConverterFormat19.factory, Type('text/x.moin.wiki;format=1.9'), type_moin_document)
default_registry.register(ConverterFormat19.factory, Type('x-moin/format;name=wiki;format=1.9'), type_moin_document)