"""
MoinMoin - Text highlighting converter

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil
from MoinMoin.util.tree import html, moin_page


class Converter(object):
    @classmethod
    def _factory(cls, request, input, output):
        if input == 'application/x.moin.document' and \
                output == 'application/x.moin.document;highlight=regex':
            return cls

    def recurse(self, elem):
        new_childs = []

        for child in elem:
            if isinstance(child, unicode):
                pos = 0

                # Restrict it to our own namespace for now
                if elem.tag.uri == moin_page.namespace:
                    for match in self.re.finditer(child):
                        text = child[pos:match.start()]
                        new_childs.append(text)

                        text = child[match.start():match.end()]
                        attrib = {html.class_: 'highlight'}
                        e = moin_page.strong(attrib=attrib, children=[text])
                        new_childs.append(e)

                        pos = match.end()

                new_childs.append(child[pos:])
            else:
                self.recurse(child)
                new_childs.append(child)

        # Use inline replacement to avoid a complete tree copy
        if len(new_childs) > len(elem):
            elem[:] = new_childs

    def __init__(self, request, re):
        self.request, self.re = request, re

    def __call__(self, tree):
        self.recurse(tree)
        return tree

from _registry import default_registry
default_registry.register(Converter._factory)
