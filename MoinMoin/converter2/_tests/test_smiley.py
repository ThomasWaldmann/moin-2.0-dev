"""
MoinMoin - Tests for MoinMoin.converter2.smiley

@copyright: 2010 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details
"""

import re
import StringIO

import py.test
try:
    from lxml import etree
except:
    py.test.skip("lxml module required to run test for docbook_out converter.")
import flask

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin.converter2.smiley import *

class Base(object):
    input_namespaces = ns_all = 'xmlns="%s" xmlns:page="%s" xmlns:xlink="%s"' % (
        moin_page.namespace,
        moin_page.namespace,
        xlink.namespace)
    output_namespaces = {
        moin_page.namespace: '',
        xlink.namespace: 'xlink'
    }

    namespaces_xpath = {'xlink': xlink.namespace}

    input_re = re.compile(r'^(<[a-z:]+)')
    output_re = re.compile(r'\s+xmlns="[^"]+"')

    def handle_input(self, input):
        i = self.input_re.sub(r'\1 ' + self.input_namespaces, input)
        return ET.XML(i)

    def handle_output(self, elem, **options):
        file = StringIO.StringIO()
        tree = ET.ElementTree(elem)
        tree.write(file, namespaces=self.output_namespaces, **options)
        return self.output_re.sub(u'', file.getvalue())

    def do(self, input, xpath_query, args={}):
        with self.app.test_client() as c:
            rv = c.get('/')
            out = self.conv(self.handle_input(input), **args)
        after_conversion = self.handle_output(out)
        logging.debug("After the SMILEY conversion : %s" % after_conversion)
        tree = etree.parse(StringIO.StringIO(after_conversion))
        assert (tree.xpath(xpath_query, namespaces=self.namespaces_xpath))

class TestConverter(Base):
    def setup_class(self):
        self.conv = Converter()
        self.app = flask.Flask('MoinMoin')

    def test_base(self):
        data = [
            ('<page><body><p>bla bla :-) bla bla</p></body></page>',
              '/page/body/p/object[@xlink:href="/static/modernized/img/smileys/smile.png"]'),
            ('<page><body><code>bla bla :-) bla bla</code></body></page>',
             '/page/body[code="bla bla :-) bla bla"]'),
            ('<page><body><p>:-) :-(</p></body></page>',
             '/page/body/p[object[1][@xlink:href="/static/modernized/img/smileys/smile.png"]][object[2][@xlink:href="/static/modernized/img/smileys/sad.png"]]'),
            # Test to check we do not have bug with newline in the string
            ('<page><body><p>1\n2\n3\n4</p></body></page>',
             '/page/body[p="1\n2\n3\n4"]'),
           ]
        for i in data:
            yield (self.do, ) + i


