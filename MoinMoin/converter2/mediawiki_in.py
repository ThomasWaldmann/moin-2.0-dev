"""
MoinMoin - Media Wiki input converter

@copyright: 2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from werkzeug import url_encode

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config
from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import html, moin_page, xlink

from ._args import Arguments
from ._args_wiki import parse as parse_arguments
from ._wiki_macro import ConverterMacro

import sys
import StringIO

from mwlib import parser
from mwlib import advtree
#from mwlib import xmltreecleaner
from mwlib import writerbase

#from mwlib.treecleaner import TreeCleaner

# writer ---------------------------------------------

class SkipChildren(object):
    "if returned by the writer no children are processed"
    def __init__(self, element=None):
        self.element = element


class MoinWikiWriter(object):
    ignoreUnknownNodes = True
    namedLinkCount = 1

    def __init__(self, env=None, status_callback=None, documenttype="article", language="en", imagesrcresolver=None, debug=False):
        assert documenttype in ("article", "book")
        self.documenttype = documenttype
        self.environment = env
        self.status_callback = status_callback
        self.language = language
        self.imagesrcresolver = imagesrcresolver # e.g. "http://anyhost/redir?img=IMAGENAME" where IMAGENAME is substituted
        self.debug = debug
        self.references = []
        self.root = None
        self.errors = []
        self.languagelinks = []
        self.categorylinks = []

    def mointree(self):
        return self.root

    def asstring(self):
        return ET.tostring(self.getTree())

    def writeText(self, obj, parent):
        if parent.getchildren(): # add to tail of last tag
            t = parent.getchildren()[-1]
            if not t.tail:
                t.tail = obj.caption
            else:
                t.tail += obj.caption
        else:
            if not parent.text:
                parent.text = obj.caption
            else:
                parent.text += obj.caption

    def writedebug(self, obj, parent, comment=""):
        parent.append(ET.Comment(text.replace("--", " - - "))) # FIXME (hot fix)


    def writeparsetree(self, tree):
        out = StringIO.StringIO()
        parser.show(out, tree)
        self.root.append(ET.Comment(out.getvalue().replace("--", " - - ")))


    def write(self, obj, parent=None):
        if isinstance(obj, parser.Text):
            self.writeText(obj, parent)
        else:
            # check for method
            m = "mdwrite" + obj.__class__.__name__
            m=getattr(self, m, None)
            if m: # find handler
                e = m(obj)
            if isinstance(e, SkipChildren): # do not process children of this node
                if e.element is not None:
                    saveAddChild(parent, e.element)
                return # skip
            elif e is None:
                pass # do nothing
                e = parent
            else:
                if not saveAddChild(parent, e):
                    return #

            for c in obj.children[:]:
                ce = self.write(c, e)


    def writeChildren(self, obj, parent): # use this to avoid bugs!
        "writes only the children of a node"
        for c in obj:
            self.write(c, parent)

    def mdwriteArticle(self, a):
        """
        this generates the root element if not available
        """
        pass

    def mdwriteNode(self, obj):
        pass

    def mdwriteBreakingReturn(self, obj):
        pass

    def mdwriteChapter(self, obj):
        pass


    def mdwriteSection(self, obj):
        pass

    def mdwritePreFormatted(self, n):
        pass


    def mdwriteParagraph(self, obj):
        pass

    def mdwriteEmphasized(self, obj):
        pass

    def mdwriteStrong(self, obj):
        pass

    def mdwriteBlockquote(self, s):
        pass

    def mdwriteIndented(self, s):
        pass

    def mdwriteItem(self, item):
        pass

    def mdwriteItemList(self, lst):
        pass

    def mdwriteDefinitionList(self, obj):
        pass

    def mdwriteDefinitionTerm(self, obj):
        pass

    def mdwriteDefinitionDescription(self, obj):
        pass

    def mdwriteTable(self, t):
        pass

    def mdwriteCell(self, cell):
        pass
    def mdwriteRow(self, row):
        pass

    def mdwriteCite(self, obj):
        pass

    def mdwriteSup(self, obj):
        pass

    def mdwriteSub(self, obj):
        pass

    def mdwriteCode(self, n):
        pass

    mdwriteSource = mdwriteCode

    def mdwriteMath(self, obj):
        """
        r = writerbase.renderMath(obj.caption, output_mode='mathml', render_engine='blahtexml')
        if not r:
            r = Element("phrase", role="texmath")
            r.text = obj.caption
            return r
        def _withETElement(e, parent):
            # translate to lxml.Elements
            for c in e.getchildren():
                #n = math.Element(qname=(math.MATHNS, str(c.tag)))
                n = Element(str(c.tag))
                parent.append(n)
                if c.text:
                    n.text = c.text
                _withETElement(c, n)

        m = Element("math", xmlns="http://www.w3.org/1998/Math/MathML")
        _withETElement(r, m)
        return m
        """

    def mdwriteImageLink(self, obj):
        """
        if not obj.target:
            return
        """
        pass


    # Links ---------------------------------------------------------

    def mdwriteLink(self, obj):
        pass
    mdwriteArticleLink = mdwriteLink
    mdwriteLangLink = mdwriteLink # FIXME
    mdwriteNamespaceLink = mdwriteLink# FIXME
    mdwriteInterwikiLink = mdwriteLink# FIXME
    mdwriteSpecialLink = mdwriteLink# FIXME

    def mdwriteURL(self, obj):
        pass

    def mdwriteNamedURL(self, obj):
        pass

    def mdwriteCategoryLink(self, obj):
        pass

    def mdwriteLangLink(self, obj): # FIXME no valid url (but uri)
        pass

    def mdwriteImageMap(self, obj): # FIXME!
        pass

    def mdwriteGallery(self, obj):
        pass

# ------------------------------------------------------------------------------

    def mdwriteDiv(self, obj):
        return Element("para") # FIXME

    def mdwriteSpan(self, obj):
        pass # FIXME

    def mdwriteHorizontalRule(self, obj):
        pass # There is no equivalent in docbook

    def mdwriteReference(self, t): # FIXME USE DOCBOOK FEATURES (needs parser support)
        pass

    def mdwriteReferenceList(self, t): # FIXME USE DOCBOOK FEATURES
        pass

# ----------------------------------- old xhtml writer stuff --------------

    # Special Objects

    def xwriteTimeline(self, obj):
        pass

    def xwriteHiero(self, obj): # FIXME parser support
        pass

    # others: Index, Gallery, ImageMap  FIXME
    # see http://meta.wikimedia.org/wiki/Help:HTML_in_wikitext

    # ------- TAG nodes (deprecated) ----------------

    def xwriteOverline(self, s):
        pass

    def xwriteUnderline(self, s):
        pass

    def xwriteCenter(self, s):
        pass

    def xwriteStrike(self, s):
        pass

    def xwriteNode(self, n):
        pass # simply write children

"""
def preprocess(root):
    advtree.buildAdvancedTree(root)
    tc = TreeCleaner(root)
    tc.cleanAll()
"""

# - func  ---------------------------------------------------


def writer(env, output, status_callback):
    if status_callback:
        buildbook_status = status_callback.getSubRange(0, 50)
    else:
        buildbook_status = None
    book = writerbase.build_book(env, status_callback=buildbook_status)
    scb = lambda status, progress:  status_callback is not None and status_callback(status=status, progress=progress)
    scb(status='preprocessing', progress=50)
    for c in book.children:
        preprocess(c)
    scb(status='rendering', progress=60)
    DocBookWriter(env, status_callback=scb, documenttype="book").writeBook(book, output=output)

writer.description = 'DocBook XML'
writer.content_type = 'text/xml'
writer.file_extension = 'xml'


class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        from mwlib.dummydb import DummyDB
        from mwlib.uparser import parseString
        db = DummyDB()
        r = parseString(title=fn, raw=input, wikidb=db)
        mww = MoinWikiWriter()
        mww.write(r) #maybe just write
        return mww.mointree()
