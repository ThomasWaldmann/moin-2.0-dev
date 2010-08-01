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
        self.current_node = moin_page.body()
        self.root = moin_page.page(children=(self.current_node, ))
        self.path = [self.root, self.current_node]

        self.errors = []
        self.languagelinks = []
        self.categorylinks = []

    def mointree(self):
        return self.root

    def open_moin_page_node(self, mointree_element):
        self.current_node.append(mointree_element)
        self.current_node = mointree_element
        self.path.append(mointree_element)

    def close_moin_page_node(self):
        self.path.pop()
        self.current_node = self.path[-1]

    def asstring(self):
        return ET.tostring(self.getTree())

    def writeText(self, obj):
            self.open_moin_page_node(obj.asText())
            self.close_moin_page_node()

    def writedebug(self, obj, parent, comment=""):
        parent.append(ET.Comment(text.replace("--", " - - "))) # FIXME (hot fix)


    def writeparsetree(self, tree):
        out = StringIO.StringIO()
        parser.show(out, tree)
        self.root.append(ET.Comment(out.getvalue().replace("--", " - - ")))


    def write(self, obj):
        if isinstance(obj, parser.Text):
            self.writeText(obj)
        else:
            # check for method
            m = "mdopen" + obj.__class__.__name__
            m=getattr(self, m, None)
            if m: # find handler
                m(obj)

            for c in obj.children[:]:
                self.write(c)

            m = "mdclose" + obj.__class__.__name__
            m=getattr(self, m, None)
            if m: # find handler
                e = m(obj)


    def writeChildren(self, obj, parent): # use this to avoid bugs!
        "writes only the children of a node"
        for c in obj:
            self.write(c, parent)

    def mdopenArticle(self, a):
        pass

    def mdopenNode(self, obj):
        pass

    def mdopenBreakingReturn(self, obj):
        node = moin_page.line_break()
        self.open_moin_page_node(node)

    def mdcloseBreakingReturn(self, obj):
        self.close_moin_page_node()


    def mdopenChapter(self, obj):
        pass

    def mdopenSection(self, obj):
        level = 1 + obj.getSectionLevel()
        node = moin_page.h(attrib={moin_page.outline_level: level})
        self.open_moin_page_node(node)

    def mdcloseSection(self, obj):
        self.close_moin_page_node()

    def mdopenPreFormatted(self, n):
        node = moin_page.code()
        self.open_moin_page_node(node)

    def mdclosePreFormatted(self, n):
        self.close_moin_page_node()

    def mdopenParagraph(self, obj):
        node = moin_page.p()
        self.open_moin_page_node(node)

    def mdcloseParagraph(self, obj):
        self.close_moin_page_node()

    def mdopenEmphasized(self, obj):
        node = moin_page.emhpasis()
        self.open_moin_page_node(node)

    def mdcloseEmphasized(self, obj):
        self.close_moin_page_node()

    def mdopenStrong(self, obj):
        node = moin_page.strong()
        self.open_moin_page_node(node)

    def mdcloseStrong(self, obj):
        self.close_moin_page_node()

    def mdopenBlockquote(self, s):
        self.open_moin_page_node(moin_page.list())
        self.open_moin_page_node(moin_page.list_item())
        self.open_moin_page_node(moin_page.list_item_body())

    def mdcloseBlockquote(self, s):
        self.close_moin_page_node()
        self.close_moin_page_node()
        self.close_moin_page_node()

    def mdopenIndented(self, s):
        pass

    def mdopenItem(self, item):
        pass

    list_type = {
        "ol": (u'ordered', None),
        "ul": (u'unordered', None),
        None: (None, None)
        }

    def mdopenItemList(self, lst):
        node = moin_page.list()
        type = self.list_type.get(getattr(lst, "tagname", None))
        if type:
            node.set(moin_page.item_label_generate, type[0])
            node.set(moin_page.list_style_type, type[1])
        self.open_moin_page_node(node)

    def mdcloseItemList(self, lst):
        self.close_moin_page_node()

    def mdopenDefinitionList(self, obj):
        pass

    def mdopenDefinitionTerm(self, obj):
        pass

    def mdopenDefinitionDescription(self, obj):
        pass

    def mdopenTable(self, t):
        pass

    def mdopenCell(self, cell):
        pass

    def mdopenRow(self, row):
        pass

    def mdopenCite(self, obj):
        pass

    def mdopenSup(self, obj):
        node = moin_page.span(attrib={moin_page.baseline_shift: "super"})
        self.open_moin_page_node(node)

    def mdcloseSup(self, obj):
        self.close_moin_page_node()

    def mdopenSub(self, obj):
        node = moin_page.span(attrib={moin_page.baseline_shift: "sub"})
        self.open_moin_page_node(node)

    def mdcloseSup(self, obj):
        self.close_moin_page_node()

    def mdopenCode(self, n):
        node = moin_page.code()
        self.open_moin_page_node(node)

    def mdcloseCode(self, n):
        self.close_moin_page_node()

    mdopenSource = mdopenCode
    mdcloseSource = mdcloseCode

    def mdopenTagNode(self, obj):
        if getattr(obj, "rawtagname", None) == u"br":
            self.open_moin_page_node(moin_page.line_break())
            self.close_moin_page_node()

    def mdcloseTagNode(self, obj):
        pass

    def mdopenMath(self, obj):
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
        pass

    def mdopenImageLink(self, obj):
        """
        if not obj.target:
            return
        """
        pass


    # Links ---------------------------------------------------------

    def mdopenLink(self, obj):
        pass
    mdopenArticleLink = mdopenLink
    mdopenLangLink = mdopenLink # FIXME
    mdopenNamespaceLink = mdopenLink# FIXME
    mdopenInterwikiLink = mdopenLink# FIXME
    mdopenSpecialLink = mdopenLink# FIXME

    def mdopenURL(self, obj):
        pass

    def mdopenNamedURL(self, obj):
        pass

    def mdopenCategoryLink(self, obj):
        pass

    def mdopenLangLink(self, obj): # FIXME no valid url (but uri)
        pass

    def mdopenImageMap(self, obj): # FIXME!
        pass

    def mdopenGallery(self, obj):
        pass

# ------------------------------------------------------------------------------

    def mdopenDiv(self, obj):
        return Element("para") # FIXME

    def mdopenSpan(self, obj):
        pass # FIXME

    def mdopenHorizontalRule(self, obj):
        pass # There is no equivalent in docbook

    def mdopenReference(self, t): # FIXME USE DOCBOOK FEATURES (needs parser support)
        pass

    def mdopenReferenceList(self, t): # FIXME USE DOCBOOK FEATURES
        pass


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

import mwlib.uparser

class Converter(ConverterMacro):
    @classmethod
    def factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content, arguments=None):
        from mwlib.dummydb import DummyDB
        from mwlib.uparser import parseString
        db = DummyDB()
        #return mwlib.uparser.simpleparse(content)
        r = parseString(title="Test", raw=content)
        r.show()
        mww = MoinWikiWriter()
        mww.write(r) #maybe just write
        return mww.mointree()

