# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - convert content in wiki markup

    Assuming we have this "renames" map:
    -------------------------------------------------------
    'PAGE', 'some_page'        -> 'some page'
    'FILE', 'with%20blank.txt' -> 'with blank.txt'

    Markup transformations needed:
    -------------------------------------------------------
    ["some_page"]           -> ["some page"] # renamed
    [:some_page:some text]  -> ["some page" some text] # NEW: free link with link text
    [:page:text]            -> ["page" text] # NEW: free link with link text
                               (with a page not being renamed)

    attachment:with%20blank.txt -> attachment:"with blank.txt"
    attachment:some_page/with%20blank.txt -> attachment:"some page/with blank.txt"
    The attachment processing should also urllib.unquote the filename (or at
    least replace %20 by space) and put it into "quotes" if it contains spaces.

    @copyright: 2007 MoinMoin:JohannesBerg,
                2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import re, codecs
from MoinMoin import i18n
i18n.wikiLanguages = lambda : []
from MoinMoin import config, wikiutil
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.action import AttachFile

class Converter(Parser):
    def __init__(self, request, pagename, raw, renames):
        self.request = request
        self.pagename = pagename
        self.raw = raw
        self.renames = renames
        self.in_pre = False
        self._ = None

    def _replace(self, key):
        """ replace a item_name if it is in the renames dict """
        if key[0] == 'PAGE':
            item_name = key[1] # pagename
        elif key[0] == 'FILE':
            item_name = key[2] # filename, key[1] is pagename
        try:
            return self.renames[key] # new pagename or new filename
        except KeyError:
            return item_name

    def return_word(self, word):
        return word
    _remark_repl = return_word
    _table_repl = return_word
    _tableZ_repl = return_word
    _emph_repl = return_word
    _emph_ibb_repl = return_word
    _emph_ibi_repl = return_word
    _emph_ib_or_bi_repl = return_word
    _u_repl = return_word
    _strike_repl = return_word
    _sup_repl = return_word
    _sub_repl = return_word
    _small_repl = return_word
    _big_repl = return_word
    _tt_repl = return_word
    _tt_bt_repl = return_word
    _notword_repl = return_word
    _rule_repl = return_word
    _smiley_repl = return_word
    _smileyA_repl = return_word
    _ent_repl = return_word
    _ent_numeric_repl = return_word
    _ent_symbolic_repl = return_word
    _heading_repl = return_word
    _email_repl = return_word
    _macro_repl = return_word
    _word_repl = return_word
    _indent_repl = return_word
    _li_none_repl = return_word
    _li_repl = return_word
    _ol_repl = return_word
    _dl_repl = return_word
    _comment_repl = return_word

    # PRE SECTION HANDLING ---------------------------------------------------

    def _pre_repl(self, word):
        origw = word
        word = word.strip()
        if word == '{{{' and not self.in_pre:
            self.in_pre = True
            return origw
        elif word == '}}}' and self.in_pre:
            self.in_pre = False
            return origw
        return word

    def _parser_repl(self, word):
        origw = word
        if word.startswith('{{{'):
            word = word[3:]

        s_word = word.strip()
        self.in_pre = True
        return origw

    # LINKS ------------------------------------------------------------------

    def _replace_target(self, target):
        target_and_anchor = target.split('#', 1)
        if len(target_and_anchor) > 1:
            target, anchor = target_and_anchor
            target = self._replace(('PAGE', target))
            return '%s#%s' % (target, anchor)
        else:
            target = self._replace(('PAGE', target))
            return target

    def interwiki(self, target_and_text, **kw):
        # TODO: maybe support [wiki:Page http://wherever/image.png] ?
        scheme, rest = target_and_text.split(':', 1)
        wikiname, pagename, text = wikiutil.split_wiki(rest)
        #self.request.log("interwiki: split_wiki -> %s.%s.%s" % (wikiname,pagename,text))

        if wikiname.lower() == 'self': # [wiki:Self:LocalPage text] or [:LocalPage:text]
            pagename = self._replace(('PAGE', pagename))
            if not text:
                return '[%s]' % wikiutil.quoteName(pagename) # ["LocalPage"]
            else:
                return '[%s %s]' % (wikiutil.quoteName(pagename), text) # ["LocalPage" text]

        # check for image URL, and possibly return IMG tag
        if not kw.get('pretty_url', 0) and wikiutil.isPicture(pagename):
            dummy, wikiurl, dummy, wikitag_bad = wikiutil.resolve_wiki(self.request, rest)
            href = wikiutil.join_wiki(wikiurl, pagename)
            #self.request.log("interwiki: join_wiki -> %s.%s.%s" % (wikiurl,pagename,href))
            return target_and_text # self.formatter.image(src=href)

        return target_and_text # wikiname, pagename, text

    def attachment(self, target_and_text, **kw):
        """ This gets called on attachment URLs """
        _ = self._
        #self.request.log("attachment: target_and_text %s" % target_and_text)
        scheme, fname, text = wikiutil.split_wiki(target_and_text)
        pagename, fname = AttachFile.absoluteName(fname, self.pagename)
        from_this_page = pagename == self.pagename
        fname = self._replace(('FILE', pagename, fname))
        if '%20' in fname:
            fname = fname.replace('%20', ' ')
        fname = self._replace(('FILE', pagename, fname))
        pagename = self._replace(('PAGE', pagename))
        if from_this_page:
            name = fname
        else:
            name = "%s/%s" % (pagename, fname)
        if ' ' in name:
            qname = wikiutil.quoteName(name)
        else:
            qname = name

        if text:
            text = ' ' + text
        return "%s:%s%s" % (scheme, qname, text)

    def _interwiki_repl(self, word):
        """Handle InterWiki links."""
        # XXX if we have access to the cfg, we can limit this to really existings interwiki identifiers
        return self.interwiki("wiki:" + word)

    def _url_repl(self, word):
        """Handle literal URLs including inline images."""
        scheme = word.split(":", 1)[0]

        if scheme == "wiki":
            return self.interwiki(word)

        if scheme in self.attachment_schemas:
            return self.attachment(word)

        if wikiutil.isPicture(word):
            # Get image name http://here.com/dir/image.gif -> image
            name = word.split('/')[-1]
            name = ''.join(name.split('.')[:-1])
            return word # self.formatter.image(src=word, alt=name)
        else:
            return word # word, scheme

    def _wikiname_bracket_repl(self, text):
        """Handle special-char wikinames with link text, like:
           ["Jim O'Brian" Jim's home page] or ['Hello "world"!' a page with doublequotes]i
        """
        word = text[1:-1] # strip brackets
        first_char = word[0]
        if first_char in wikiutil.QUOTE_CHARS:
            # split on closing quote
            target, linktext = word[1:].split(first_char, 1)
            target = self._replace_target(target)
            target = wikiutil.quoteName(target)
        else: # not quoted
            # split on whitespace
            target, linktext = word.split(None, 1)
            target = self._replace_target(target)
            if ' ' in target:
                target = wikiutil.quoteName(target)
        if linktext:
            linktext = ' ' + linktext
        return '[%s%s]' % (target, linktext)


    def _url_bracket_repl(self, word):
        """Handle bracketed URLs."""
        word = word[1:-1] # strip brackets

        # Local extended link? [:page name:link text]
        if word[0] == ':':
            words = word[1:].split(':', 1)
            words[0] = self._replace_target(words[0])
            if len(words) == 1:
                link = words[0]
                link = wikiutil.quoteName(link)
                return '[%s]' % link # use freelink
            else:
                link, text = words
                link = wikiutil.quoteName(link)
                if text:
                    text = ' ' + text
                return '[%s%s]' % (link, text) # use freelink with text

        scheme_and_rest = word.split(":", 1)
        if len(scheme_and_rest) == 2: # scheme given
            scheme, rest = scheme_and_rest
            if scheme == "wiki":
                return self.interwiki(word, pretty_url=1)
            if scheme in self.attachment_schemas:
                return self.attachment(word, pretty_url=1)

        words = word.split(None, 1)
        if len(words) == 1:
            link, text = words[0], ''
        else:
            link, text = words
        if text:
            text = ' ' + text
        return '[%s%s]' % (link, text)

    # SCANNING ---------------------------------------------------------------
    def scan(self, scan_re, line):
        """ Scans one line

        Append text before match, invoke replace() with match, and add text after match.
        """
        result = []
        lastpos = 0

        for match in scan_re.finditer(line):
            # Add text before the match
            if lastpos < match.start():
                result.append(line[lastpos:match.start()])
            # Replace match with markup
            result.append(self.replace(match))
            lastpos = match.end()

        # Add remainder of the line
        result.append(line[lastpos:])
        return u''.join(result)

    def replace(self, match):
        """ Replace match using type name """
        result = []
        for _type, hit in match.groupdict().items():
            if hit is not None and not _type in ["hmarker", ]:
                # Get replace method and replace hit
                replace = getattr(self, '_' + _type + '_repl')
                result.append(replace(hit))
                return ''.join(result)
        else:
            # We should never get here
            import pprint
            raise Exception("Can't handle match %r\n%s\n%s" % (
                match,
                pprint.pformat(match.groupdict()),
                pprint.pformat(match.groups()),
            ))

        return ""

    def convert(self):
        """ For each line, scan through looking for magic
            strings, outputting verbatim any intervening text.
        """
        # prepare regex patterns
        rules = self.formatting_rules.replace('\n', '|')
        if 1: # self.cfg.bang_meta:
            rules = ur'(?P<notword>!%(word_rule)s)|%(rules)s' % {
                'word_rule': self.word_rule,
                'rules': rules,
            }
        pre_rules = self.pre_formatting_rules.replace('\n', '|')
        scan_re = re.compile(rules, re.UNICODE)
        pre_scan_re = re.compile(pre_rules, re.UNICODE)
        eol_re = re.compile(r'\r?\n', re.UNICODE)

        rawtext = self.raw

        # remove last item because it's guaranteed to be empty
        self.lines = eol_re.split(rawtext)[:-1]
        self.in_processing_instructions = 1

        # Main loop
        for line in self.lines:
            # ignore processing instructions
            if self.in_processing_instructions:
                found = False
                for pi in ("##", "#format", "#refresh", "#redirect", "#deprecated",
                           "#pragma", "#form", "#acl", "#language"):
                    if line.lower().startswith(pi):
                        self.request.write(line + '\r\n')
                        found = True
                        break
                if not found:
                    self.in_processing_instructions = 0
                else:
                    continue # do not parse this line
            if self.in_pre:
                # still looking for processing instructions
                if self.in_pre == 'search_parser':
                    if line.strip().startswith("#!"):
                        self.in_pre = True
                        self.request.write(line + '\r\n')
                        continue
                    else:
                        self.in_pre = True
            else:
                # Paragraph break on empty lines
                if not line.strip():
                    self.request.write(line + '\r\n')
                    continue

            # Scan line, format and write
            scanning_re = self.in_pre and pre_scan_re or scan_re
            formatted_line = self.scan(scanning_re, line)
            self.request.write(formatted_line + '\r\n')

def convert_wiki(pagename, intext, renames):
    """ Convert content written in wiki markup """
    import StringIO
    request = StringIO.StringIO()
    noeol = False
    if not intext.endswith('\r\n'):
        intext += '\r\n'
        noeol = True
    p = Converter(request, pagename, intext, renames)
    p.convert()
    res = request.getvalue()
    if noeol:
        res = res[:-2]
    return res
