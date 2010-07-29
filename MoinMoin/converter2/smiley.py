"""
MoinMoin - Smiley converter

Replace all the text corresponding to a smiley, by the corresponding
<object> tag for the DOM Tree.

@copyright: 2009 MoinMoin:ValentinJaniaut
@license: GNU GPL, see COPYING for details.
"""

import re

from emeraldtree import ElementTree as ET

from flask import url_for

from MoinMoin.util.iri import Iri
from MoinMoin.util.tree import moin_page, xlink

class Converter(object):
    """
    Replace each smiley by the corresponding <object> in the DOM Tree
    """
    smileys = {
        # markup: (image filename, w, h)
        'X-(': ('angry.png', 16, 16),
        ':D': ('biggrin.png', 16, 16),
        '<:(': ('frown.png', 16, 16),
        ':o': ('redface.png', 16, 16),
        ':(': ('sad.png', 16, 16),
        ':)': ('smile.png', 16, 16),
        'B)': ('smile2.png', 16, 16),
        ':))': ('smile3.png', 16, 16),
        ';)': ('smile4.png', 16, 16),
        '/!\\': ('alert.png', 16, 16),
        '<!>': ('attention.png', 16, 16),
        '(!)': ('idea.png', 16, 16),
        ':-?': ('tongue.png', 16, 16),
        ':\\': ('ohwell.png', 16, 16),
        '>:>': ('devil.png', 16, 16),
        '|)': ('tired.png', 16, 16),
        ':-(': ('sad.png', 16, 16),
        ':-)': ('smile.png', 16, 16),
        'B-)': ('smile2.png', 16, 16),
        ':-))': ('smile3.png', 16, 16),
        ';-)': ('smile4.png', 16, 16),
        '|-)': ('tired.png', 16, 16),
        '(./)': ('checkmark.png', 16, 16),
        '{OK}': ('thumbs-up.png', 16, 16),
        '{X}': ('icon-error.png', 16, 16),
        '{i}': ('icon-info.png', 16, 16),
        '{1}': ('prio1.png', 15, 13),
        '{2}': ('prio2.png', 15, 13),
        '{3}': ('prio3.png', 15, 13),
        '{*}': ('star_on.png', 16, 16),
        '{o}': ('star_off.png', 16, 16),
    }

    smiley_rule = ur"""
    (^|(?<=\s))  # we require either beginning of line or some space before a smiley
    (%(smiley)s)  # one of the smileys
    (?=\s)  # we require some space after the smiley
""" % {'smiley': u'|'.join([re.escape(s) for s in smileys])}

    smiley_re = re.compile(smiley_rule, re.UNICODE|re.VERBOSE)

    # We do not process any smiley conversion within these elements.
    tags_to_ignore = set(['code', 'blockcode', ])

    @classmethod
    def _factory(cls, input, output, icon=None, **kw):
        if icon == 'smiley':
            return cls()

    def __call__(self, content):
        self.do_children(content)
        return content

    def do_children(self, element):
        if element.tag.name in self.tags_to_ignore:
            return
        for child in element:
            if isinstance(child, ET.Element):
                self.do_children(child)
            else:
                # We delete the text, and recreate a list, with the old text
                # and the new object tags.
                element.remove(child)
                [element.append(item) for item in self.do_smiley(child)]

    def do_smiley(self, element):
        """
        From a text, return a list with smileys replaced
        by object elements, and the former text for the
        other element of the list.
        """
        # We split our string into different element arround
        # the matched smiley.
        splitted_string = re.split(self.smiley_re, element)
        return [self.replace_smiley(item) for item in splitted_string]

    def replace_smiley(self, text):
        """
        Replace a given string by the an object
        element if the string is exactly a smiley.
        Otherwise return the string
        """
        # Remove the space of the smiley_text if any
        smiley_text = text.strip()
        if smiley_text in self.smileys:
            icon, h, w = self.smileys[smiley_text]
            attrib = {}
            key = xlink.href
            # TODO: Retrieve the name of the theme used by the user
            #        to get the correct smiley image
            attrib[key] = Iri(url_for('static', filename="modernized/img/smileys/%s" % icon))
            return ET.Element(moin_page('object'), attrib=attrib, children={})
        return text

from . import default_registry
from MoinMoin.util.mime import type_moin_document
default_registry.register(Converter._factory, type_moin_document, type_moin_document)
