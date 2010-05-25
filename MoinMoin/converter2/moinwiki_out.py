"""
MoinMoin - Moinwiki markup output converter

Converts an internal document tree into a moinwiki markup.

This is preprealpha version, do not use it, it doesn't work.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page, xlink

class moinwiki:
    '''
    Moinwiki syntax elements
    It's dummy
    '''
    a_open = '[['
    a_middle = '||'
    a_close = ']]'
    verbatim_open = '{{{'
    verbatim_close = '}}}'
    monospace = '`'
    strong = "'''"
    emphasis = "''"
    underline = '__'
    stroke_open = '--('
    stroke_close = ')--'

    def __init__(self):
        pass

class Converter():
    """
    Converter application/x.moin.document -> text/x.moin.wiki
    """
    @classmethod
    def _factory(cls, request, input, output, **kw):
        if input == 'application/x.moin.document' and \
           output == 'text/x.moin.wiki':
            return cls

    def __init__(self, request):
        self.request = request

    def __call__(self, root):
        opened = [None, ]
        children = [[root], None ]
        output = []
        
        while children[0]:
            if children[0]:
                next_child = children.pop(0)
                output.append(self.open(next_child))
            else:
                next_parent = opened.pop()
                output.append(self.close(next_parent))

        return ''.join(output)

    def open(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            n = 'open_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return ''

    def open_moinpage(self, elem):
        n = 'open_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem) 
        return ''

    def close(self, elem):
        uri = elem.tag.uri
        name = self.namespaces_visit.get(uri, None)
        if name is not None:
            n = 'close_' + name
            f = getattr(self, n, None)
            if f is not None:
                return f(elem)
        return ''

    def close_moinpage(self, elem):
        n = 'close_moinpage_' + elem.tag.name.replace('-', '_')
        f = getattr(self, n, None)
        if f:
            return f(elem)
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem) 
        return ''

    def open_moinpage_a(self, elem):
        href = elem.get(xlink.href, None)
        if href is not None:
            attrib[html.href] = href
        if elem.children:
            href += a_middle
            self.children.append(list(elem.children))
            self.opened.append(elem)
        else:
            href += self.close_moinpage_a(elem)
        return a_open + href

    def close_moinpage_a(self, elem):
        return a_close 

    def open_moinpage_blockcode(self, elem):
        ret = moinwiki.verbatim_open        
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_blockcode(elem)                
        return ret

    def close_moinpage_blockcode(self, elem):
        return moinwiki.verbatim_close

    def open_moinpage_code(self, elem):
        ret = moinwiki.monospace
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_code(elem)           
        return ret

    def close_moinpage_code(self, elem):
        return moinwiki.monospace

    def open_moinpage_div(self, elem):
        return ''

    def close_moinpage_div(self, elem):
        return ''

    def open_moinpage_emphasis(self, elem):
        ret = moinwiki.emphasis
        if elem.children:
            self.children.append(list(elem.children))
            self.opened_nodes.append(elem)
        else:
            ret += self.close_moinpage_emphasis(elem)
        return ret

    def close_moinpage_emphasis(self, elem):
        return moinwiki.emphasis


    def open_moinpage_h(self, elem):
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        ret = moinwiki.h * level
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_h(elem)                
        return ret

    def close_moinpage_h():
        level = elem.get(moin_page.outline_level, 1)
        try:
            level = int(level)
        except ValueError:
            raise ElementException('page:outline-level needs to be an integer')
        if level < 1:
            level = 1
        elif level > 6:
            level = 6
        return moinwiki.h * level 

    def open_moinpage_line_break(self, elem):
        return moinwiki.linebreak

    def open_moinpage_list(self, elem):
        #TODO
        return ''

    def open_moinpage_object(self, elem):
        #TODO
        return ''

    def open_moinpage_p(self, elem):
        ret = moinwiki.p
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_p(elem)           
        return ret

    def close_moinpage_p(self, elem):
        return moinwiki.p

    def open_moinpage_page(self, elem):
        #TODO
        return ''

    def open_moinpage_part(self, elem):
        #TODO
        return ''

    def open_moinpage_separator(self, elem):
        return moinwiki.separator

    def open_moinpage_span(self, elem):
        # TODO
        return ''

    def open_moinpage_strong(self, elem):
        ret = moinwiki.strong
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_h(elem)                
        return ret

    def close_moinpage_strong(self, elem):
        return moinwiki.strong


    #TODO: convertrion for moinpage.table*
    def open_moinpage_table(self, elem):
        return ''

    def open_moinpage_table_cell(self, elem):
        return ''

    def open_moinpage_table_row(self, elem):
        return ''



from . import default_registry
default_registry.register(Converter._factory)

