"""
MoinMoin - Moinwiki markup output converter

Converts an internal document tree into moinwiki markup.

This is preprealpha version, do not use it, it doesn't work.

@copyright: 2008 MoinMoin:BastianBlank
            2010 MoinMoin:DmitryAndreev
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

from MoinMoin.util.tree import moin_page, xlink

class Moinwiki(object):
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

    # TODO: list type[(*,'lower-*')]
    list_type = {\
        ('definition', None):'',\
        ('ordered', None):'1.',\
        ('ordered', 'upper-alpha'):'A.',\
        ('ordered', 'upper-roman'):'I.',\
        ('unordered', None):'*'
    }

    def __init__(self):
        pass

class Converter(object):
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
        self.opened = [None, ]
        self.children = [[root], None ]
        self.output = []
        self.list_item_lable = []
        
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
        ret = Moinwiki.verbatim_open        
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_blockcode(elem)                
        return ret

    def close_moinpage_blockcode(self, elem):
        return Moinwiki.verbatim_close

    def open_moinpage_code(self, elem):
        ret = Moinwiki.monospace
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_code(elem)           
        return ret

    def close_moinpage_code(self, elem):
        return Moinwiki.monospace

    def open_moinpage_div(self, elem):
        return ''

    def close_moinpage_div(self, elem):
        return ''

    def open_moinpage_emphasis(self, elem):
        ret = Moinwiki.emphasis
        if elem.children:
            self.children.append(list(elem.children))
            self.opened_nodes.append(elem)
        else:
            ret += self.close_moinpage_emphasis(elem)
        return ret

    def close_moinpage_emphasis(self, elem):
        return Moinwiki.emphasis


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
        ret = Moinwiki.h * level
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
        return Moinwiki.h * level 

    def open_moinpage_line_break(self, elem):
        return Moinwiki.linebreak

    def open_moinpage_list(self, elem):
        if elem.children:
            label_type = (elem.get(moin_page.item_label_generate, None), elem.get(moin_page.list_style_type, None))
            self.list_item_labels.append(Moinwiki.list_label_type.get(label_type, ''))
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''
        
    def close__moinpage_list(self, elem):
        self.list_item_labels.pop()
        return ''


    def open_moinpage_list_item(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        # TODO: return shift, equal list level + list_label
        return ''

    def close_moinpage_list_item(self, elem):
        return ''

    def open_moinpage_list_label(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def close_moinpage_list_label(self, elem):
        return ''

    def open_moinpage_list_item_body(self, elem):
        if elem.children:
            self.children.append(list(elem.children))
            self.opened.append(elem)
        return ''

    def close_moinpage_list_item_body(self, elem):
        return ''
        
    def open_moinpage_object(self, elem):
        # TODO
        return ''

    def open_moinpage_p(self, elem):
        ret = moinpage_list_Moinwiki.p
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_p(elem)           
        return ret

    def close_moinpage_p(self, elem):
        return Moinwiki.p

    def open_moinpage_page(self, elem):
        # TODO
        return ''

    def open_moinpage_part(self, elem):
        # TODO
        return ''

    def open_moinpage_separator(self, elem):
        return Moinwiki.separator

    def open_moinpage_span(self, elem):
        # TODO
        return ''

    def open_moinpage_strong(self, elem):
        ret = Moinwiki.strong
        if elem.children:
            children.append(list(elem.children))
            opened.append(elem)
        else:
            ret += close_moinpage_h(elem)                
        return ret

    def close_moinpage_strong(self, elem):
        return Moinwiki.strong


    # TODO:conversion for moinpage.table*

    def open_moinpage_table(self, elem):
        return ''

    def open_moinpage_table_cell(self, elem):
        return ''

    def open_moinpage_table_row(self, elem):
        return ''



from . import default_registry
default_registry.register(Converter._factory)

