# -*- coding: ascii -*-
"""
    MoinMoin - Table - build and render simple html tables

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""


class Table(object):
    """
    build and render simple tables
    """
    template = u"""
<table{{ ' class="%s"' % table.css_class if table.css_class }}>
{% if table.caption -%}
<caption>{{ table.caption }}</caption>
{%- endif %}
{% if table.header %}
<thead>
    <tr>
        {% for col in table.columns -%}
        <th class="{{ col.css_class }}">{{ col.head | e }}</th>
        {%- endfor %}
    </tr>
</thead>
{% endif %}
{% if table.footer %}
<tfoot>
    <tr>
        {% for col in table.columns -%}
        <th class="{{ col.css_class }}">{{ col.foot | e }}</th>
        {%- endfor %}
    </tr>
</tfoot>
{% endif %}
<tbody>
    {% for row in table.rows -%}
    <tr>
        {% for col in table.columns -%}
        <td class="{{ row[col.key].css_class }}">{{ row[col.key].value | e }}</td>
        {%- endfor %}
    </tr>
    {%- endfor %}
</tbody>
</table>
"""

    def __init__(self, css_class=None, caption=None, empty='', header=True, footer=False):
        """
        Create a table

        @param css_class: class attr of the table element
        @param caption: add a caption element with the text given
        @param empty: if given, put this text into otherwise empty data cells
        @param header: if True, render the table header (default: True)
        @param footer: if True, render the table footer (default: False)
        """
        self.css_class = css_class
        self.caption = caption
        self.empty = empty
        self.header = header
        self.footer = footer
        self.columns = []
        self.rows = []

    def add_column(self, **col):
        """
        add a table column

        @arg key: key for row dict (required)
        @arg head: label text for col header (optional, defaults to key)
        @arg foot: label text for col footer (optional, defaults to key)
        @arg css_class: for each element in this column (optional, defaults to key)
        """
        if self.header and col.get('head') is None:
            col['head'] = col.get('key')
        if self.footer and col.get('foot') is None:
            col['foot'] = col.get('key')
        if col.get('css_class') is None:
            col['css_class'] = col.get('key')
        self.columns.append(col)

    def add_row(self, **row):
        """
        add a table row, give a dict of key:value for this row

        keys need to be those as specified with add_column

        values can either be dicts (having required 'value' and optional
        'css_class' keys - if css_class is missing, default from column will be
        used) or non-dicts (then an appropriate dict will be auto-created)
        """
        # make sure we have a value for each column key
        # make sure each value is a dict with 'value' and 'css_class'
        for col in self.columns:
            key = col['key']
            default_css_class = col['css_class']
            if key in row:
                value = row[key]
                if not isinstance(value, dict):
                    value = dict(value=value, css_class=default_css_class)
                elif value.get('css_class') is None:
                    value['css_class'] = default_css_class
            else:
                value = dict(value=self.empty, css_class=default_css_class)
            row[key] = value
        self.rows.append(row)

    def render(self, env):
        """
        render the table

        @param env: templating environment of jinja2
        """
        t = env.from_string(self.template)
        return t.render(table=self)


if __name__ == '__main__':
    from jinja2 import Environment
    env = Environment()

    t = Table(css_class="sometable", caption="Table Caption", empty='-', header=True, footer=True)
    t.add_column(key="c1", head="Column 1 Head", css_class="class1")
    t.add_column(key="c2", foot="Column 2 Foot")
    t.add_row(c1=1)
    t.add_row(c2=2)
    t.add_row(c1=1, c2=2)
    print t.render(env)

