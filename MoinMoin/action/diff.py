# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show diff between 2 page revisions

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2006-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil
from MoinMoin.Page import Page

def execute(pagename, request):
    """ Handle "action=diff"
        checking for either a "rev=formerrevision" parameter
        or rev1 and rev2 parameters
    """
    data_backend = request.cfg.data_backend

    if not request.user.may.read(pagename):
        Page(request, pagename).send_page()  # TODO: Get rid of Page-usage here
        return

    try:
        date = request.form['date'][0]
        try:
            date = date
        except StandardError:
            date = 0
    except KeyError:
        date = 0

    try:
        rev1 = int(request.form.get('rev1', [-1])[0])
    except StandardError:
        rev1 = 0
    try:
        rev2 = int(request.form.get('rev2', [0])[0])
    except StandardError:
        rev2 = 0

    if rev1 == -1 and rev2 == 0:
        rev1 = request.rev
        if rev1 is None:
            rev1 = -1

    # spacing flag?
    ignorews = int(request.form.get('ignorews', [0])[0])

    _ = request.getText

    # get a list of old revisions, and back out if none are available
    currentpage = data_backend.get_item(pagename)
    currentrev = currentpage.get_revision(-1)
    currentrev = currentrev.revno

    if currentrev < 1:  # Revision enumeration starts with 0 in the backend
        request.theme.add_msg(_("No older revisions available!"), "error")
        Page.from_item(request, currentpage).send_page()
        return

    if date: # this is how we get called from RecentChanges
        rev1 = 0
        item = data_backend.get_item(pagename)
        revs = item.list_revisions()
        for revno in revs:
            revision = item.get_revision(revno)
            if date >= revision[EDIT_LOG_MTIME]:
                rev1 = revision.revno
                break
        else:
            rev1 = 1
        rev2 = 0

    # Start output
    # This action generates content in the user language
    request.setContentLanguage(request.lang)

    request.emit_http_headers()
    request.theme.send_title(_('Diff for "%s"') % (pagename, ), pagename=pagename, allow_doubleclick=1)

    if rev1 > 0 and rev2 > 0 and rev1 > rev2 or rev1 == 0 and rev2 > 0:
        rev1, rev2 = rev2, rev1

    if rev1 == -1:
        oldrev = currentrev - 1
        ###oldpage = Page(request, pagename, rev=oldrev)
        item = data_backend.get_item(pagename)
        oldpage = item.get_revision(oldrev)

    elif rev1 == 0:
        oldrev = currentrev
        oldpage = currentpage

    else:
        oldrev = rev1
        ###oldpage = Page(request, pagename, rev=oldrev)
        item = data_backend.get_item(pagename)
        oldpage = item.get_revision(oldrev)

    if rev2 == 0:
        newrev = currentrev
        newpage = currentpage.get_revision(newrev)

    else:
        newrev = rev2
        ###newpage = Page(request, pagename, rev=newrev)
        item = data_backend.get_item(pagename)
        newpage = item.get_revision(newrev)

    edit_count = abs(newrev - oldrev)

    f = request.formatter
    request.write(f.div(1, id="content"))

    oldrev = oldpage.revno
    newrev = newpage.revno

    revlist = currentpage.list_revisions()

    # code below assumes that the page exists and has at least
    # one revision in the revlist, just bail out if not. Users
    # shouldn't really run into this anyway.
    if not revlist:
        request.write(f.div(0)) # end content div
        request.theme.send_footer(pagename)
        request.theme.send_closing_html()
        return

    title = _('Differences between revisions %d and %d') % (oldrev, newrev)
    if edit_count > 1:
        title += ' ' + _('(spanning %d versions)') % (edit_count, )
    title = f.text(title)

    # Revision list starts from 2...
    if oldrev == min(revlist):
        disable_prev = u' disabled="true"'
    else:
        disable_prev = u''

    if newrev == max(revlist):
        disable_next = u' disabled="true"'
    else:
        disable_next = u''

    ###page_url = wikiutil.escape(currentpage.url(request), True)
    page_url = wikiutil.escape(Page.from_item(request, currentpage).url(request), True)

    revert_html = ""
    if request.user.may.revert(pagename):
        revert_html = """
 <td style="border:0">
  <span style="text-align:center">
   <form action="%s" method="get">
    <input name="action" value="revert" type="hidden">
    <input name="rev" value="%d" type="hidden">
    <input value="%s" type="submit"%s>
   </form>
  </span>
 </td>
 """ % (page_url, rev2, _("Revert to this revision"), disable_next)

    navigation_html = """
<span class="diff-header">%s</span>
<table class="diff">
<tr>
 <td style="border:0">
  <span style="text-align:left">
   <form action="%s" method="get">
    <input name="action" value="diff" type="hidden">
    <input name="rev1" value="%d" type="hidden">
    <input name="rev2" value="%d" type="hidden">
    <input value="%s" type="submit"%s>
   </form>
  </span>
 </td>
 %s
 <td style="border:0">
  <span style="text-align:right">
   <form action="%s" method="get">
    <input name="action" value="diff" type="hidden">
    <input name="rev1" value="%d" type="hidden">
    <input name="rev2" value="%d" type="hidden">
    <input value="%s" type="submit"%s>
   </form>
  </span>
 </td>
</tr>
</table>
""" % (title,
       page_url, oldrev - 1, oldrev, _("Previous change"), disable_prev,
       revert_html,
       page_url, newrev, newrev + 1, _("Next change"), disable_next, )

    request.write(f.rawHTML(navigation_html))

    if request.user.show_fancy_diff:
        from MoinMoin.util import diff_html
        request.write(f.rawHTML(diff_html.diff(request, oldpage.read(), newpage.read())))
        ###newpage.send_page(count_hit=0, content_only=1, content_id="content-below-diff")
        # XXX: Navigating stupidly from the revision to its item. Use a better approach here...
        Page.from_item(request, newpage._item).send_page(count_hit=0, content_only=1, content_id="content-below-diff")
    else:
        from MoinMoin.util import diff_text
        # XXX and here...
        oldlines = Page.from_item(request, oldpage._item).getlines()
        newlines = Page.from_item(request, newpage._item).getlines()
        lines = diff_text.diff(oldlines, newlines)
        if not lines:
            msg = f.text(" - " + _("No differences found!"))
            if edit_count > 1:
                msg = msg + f.paragraph(1) + f.text(_('The page was saved %(count)d times, though!') % {
                    'count': edit_count}) + f.paragraph(0)
            request.write(msg)
        else:
            if ignorews:
                request.write(f.text(_('(ignoring whitespace)')), f.linebreak())
            else:
                qstr = {'action': 'diff', 'ignorews': '1', }
                if rev1:
                    qstr['rev1'] = str(rev1)
                if rev2:
                    qstr['rev2'] = str(rev2)
                request.write(f.paragraph(1), Page(request, pagename).link_to(request,
                    text=_('Ignore changes in the amount of whitespace'),
                    querystr=qstr, rel='nofollow'), f.paragraph(0))

            request.write(f.preformatted(1))
            for line in lines:
                if line[0] == "@":
                    request.write(f.rule(1))
                request.write(f.text(line + '\n'))
            request.write(f.preformatted(0))

    request.write(f.div(0)) # end content div
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()

