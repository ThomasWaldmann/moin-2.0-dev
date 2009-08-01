# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - GraphInfo action

    This action is replacement for standard info action. It draws nice revision
    graph tree. Because of depending on extended API, can only be used with
    MercurialBackend.

    This action shows Page history in a form of tree.
    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from mercurial.templatefilters import json

from MoinMoin import wikiutil
from MoinMoin import user
from MoinMoin.widget import html
from MoinMoin.Page import Page
from MoinMoin.items import EDIT_LOG_ACTION, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
                           EDIT_LOG_USERID, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME


def execute(pagename, request):
    """Show page history drawing revision graph."""
    page = Page(request, pagename)

    if not request.user.may.read(pagename) or not page.exists():
        page.send_page()
        return

    def history(page, pagename, request):
        """Render graphical information about page revisions."""
        _ = request.getText

        def render_action(text, query, **kw):
            kw.update(dict(rel='nofollow'))
            return page.link_to(request, text, querystr=query, **kw)

        default_count, limit_max_count = request.cfg.history_count
        try:
            max_count = int(request.form.get('max_count', [default_count])[0])
        except:
            max_count = default_count
        max_count = min(max_count, limit_max_count)

        try:
            item = request.storage.get_item(pagename)
        except NoSuchItemError:
            pass  # TODO: move from storage branch, when done there

        history, revs = [], []
        colors = {}
        new_color = 1
        cnt = None
        for cnt, revno in enumerate(reversed(item.list_revisions())):
            actions = []
            try:
                revision = item.get_revision(revno)
            except NoSuchRevisionError:
                pass  # TODO: move from storage branch, when done there

            if revision[EDIT_LOG_ACTION] in ('SAVE', 'SAVENEW', 'SAVE/REVERT', 'SAVE/RENAME', ):
                size = revision.size

                if cnt == 0:
                    lchecked, rchecked = '', 'checked="checked"'
                elif cnt == 1:
                    lchecked, rchecked = 'checked="checked"', ''
                else:
                    lchecked = rchecked = ''
                diff = '<input type="radio" name="rev1" value="%d" %s> \
                        <input type="radio" name="rev2" value="%d" %s>' % (revno, lchecked, revno, rchecked)

                comment = revision[EDIT_LOG_COMMENT]
                if not comment:
                    if '/REVERT' in revision[EDIT_LOG_ACTION]:
                        comment = _("Revert to revision %(revno)d.") % {'revno': int(revision[EDIT_LOG_EXTRA])}
                    elif '/RENAME' in revision[EDIT_LOG_ACTION]:
                        comment = _("Renamed from '%(oldpagename)s'.") % {'oldpagename': revision[EDIT_LOG_EXTRA]}
            else:
                raise "ATT* in editlog?"

            # Compute revs and next_revs
            if revno not in revs:
                revs.append(revno)  # new head
                colors[revno] = new_color
                new_color += 1

            idx = revs.index(revno)
            color = colors.pop(revno)
            next = revs[:]
            # Add parents to next_revs
            parents = revision.get_parents()
            addparents = [p for p in parents if p not in next]
            next[idx:idx + 1] = addparents
            # Set colors for the parents
            for i, p in enumerate(addparents):
                if not i:
                    colors[p] = color
                else:
                    colors[p] = new_color
                    new_color += 1
            # Add edges to the graph
            edges = []
            for col, r in enumerate(revs):
                if r in next:
                    edges.append((col, next.index(r), colors[r]))
                elif r == revno:
                    for p in parents:
                        edges.append((col, next.index(p), colors[p]))
            revs = next

            url = page.url(request, {'action': 'recall', 'rev': '%d' % revno})
            editor = user.get_printable_editor(request, revision[EDIT_LOG_USERID], revision[EDIT_LOG_ADDR],
                                          revision[EDIT_LOG_HOSTNAME]) or _("N/A")
            date = request.user.getFormattedDateTime(float(revision.timestamp))
            comment = wikiutil.escape(comment) or '&nbsp;'
            node = "%d:%s" % (revno, request.storage._get_revision_node(revision)[1])

            history.append((url, (idx, color), edges, node, editor, date, comment, "%d B" % size, diff, "&nbsp;".join(actions)))
            if cnt >= max_count:
                break

        bg_height = 39   # these values come form mercurial.hgweb.webcommands or graph.tmpl
        canvasheight = (len(history) + 1) * bg_height - 27
        canvaswidth = 224

        request.write(unicode(html.H2().append(_('Revision History'))))
        if cnt is None:  # there was no entry in logfile
            request.write(_('No log entries found.'))
            return

        div = html.DIV(id="page-history")
        buttons ='<input type="submit" value="%s">' % (_("Diff"), )
        # TODO: <input type="submit" value="%s">' % (_("Merge"), ) and merge related stuff, see global SOC TODO
        div.append(buttons)
        div.append(html.INPUT(type="hidden", name="action", value="diff"))

        div.append('<!--[if IE]><script type="text/javascript" src="%s/graph/excanvas.js"></script><![endif]-->' % request.cfg.url_prefix_static)
        noscript = html.DIV(id="noscript")
        noscript.append("This action only works with JavaScript-enabled browsers.")
        wrapper = html.DIV(id="wrapper")
        nodebgs = '<ul id="nodebgs"></ul>'
        graphnodes = '<ul id="graphnodes"></ul>'
        wrapper.append(nodebgs)
        wrapper.append('<canvas id="graph" width="%d" height="%d"></canvas>' % (canvaswidth, canvasheight, ))
        wrapper.append(graphnodes)
        graph = '<script type="text/javascript", src="%s/graph/graph.js"></script>' % request.cfg.url_prefix_static
        div.append(noscript)
        div.append(wrapper)
        div.append(graph)

        render_graph = """
<script>
<!-- hide script content

document.getElementById('noscript').style.display = 'none';

var data = %s
var graph = new Graph();
graph.scale(%s);

graph.edge = function(x0, y0, x1, y1, color) {

    this.setColor(color, 0.0, 0.65);
    this.ctx.beginPath();
    this.ctx.moveTo(x0, y0);
    this.ctx.lineTo(x1, y1);
    this.ctx.stroke();

}

var revlink = '<li style="_STYLE"><span class="desc_">';
revlink += '<a href="_URL" title="_URL">_NODE</a> _COMMENT';
revlink += '</span><span class="info_">_RADIO _DATE, by _USER</span><span class="size_"> _SIZE</span>_ACTIONS</li>';

graph.vertex = function(x, y, color, parity, cur) {

    this.ctx.beginPath();
    color = this.setColor(color, 0.25, 0.75);
    this.ctx.arc(x, y, radius, 0, Math.PI * 2, true);
    this.ctx.fill();

    var bg = '<li class="bg parity' + parity + '"></li>';
    var left = (this.columns + 1) * this.bg_height;
    var nstyle = 'padding-left: ' + left + 'px;';
    var item = revlink.replace(/_STYLE/, nstyle);
    item = item.replace(/_PARITY/, 'parity' + parity);
    item = item.replace(/_URL/, cur[0]);
    item = item.replace(/_URL/, cur[0]);
    item = item.replace(/_NODE/, cur[3]);
    item = item.replace(/_USER/, cur[4]);
    item = item.replace(/_DATE/, cur[5]);
    item = item.replace(/_COMMENT/, cur[6]);
    item = item.replace(/_SIZE/, cur[7]);
    item = item.replace(/_RADIO/, cur[8]);
    item = item.replace(/_ACTIONS/, cur[9]);

    return [bg, item];

}

graph.render(data);

// stop hiding script -->
</script>""" % (json(history), str(bg_height), )

        div.append(render_graph)
        form = html.FORM(method="GET", action="")
        form.append(div)
        request.write(unicode(form))

    _ = request.getText
    f = request.formatter
    request.cfg.stylesheets = [('all', request.cfg.url_prefix_static + '/graph/graph.css', )]
    request.emit_http_headers()
    request.setContentLanguage(request.lang)
    request.theme.send_title(_('Info for "%s"') % (page.split_title(), ), page=page)
    request.write(f.div(1, id="content"))
    history(page, pagename, request)
    request.write(f.div(0))
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()
