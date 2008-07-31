# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - show diff between 2 page revisions

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2006-2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.storage import EDIT_LOG_MTIME
from MoinMoin.storage.error import NoSuchRevisionError

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
        date = int(request.form.get('date', [None])[0])
    except StandardError:
        date = None
    try:
        rev1 = int(request.form.get('rev1', [None])[0])
    except StandardError:
        rev1 = None
    try:
        rev2 = int(request.form.get('rev2', [None])[0])
    except StandardError:
        rev2 = None

    # a value being None means that it was not (or not validly) given,
    # thus we make up some defaults (no default for date, if it is not
    # given or not valid, we just don't use it):
    if rev2 is None:
        rev2 = -1  # -1 means latest rev (implemented by backend)
    if rev1 is None:
        rev1 = -2  # -2 means second latest rev (not implemented by backend)

    # spacing flag?
    ignorews = int(request.form.get('ignorews', [0])[0])

    _ = request.getText

    # get a list of old revisions, and back out if none are available
    try:
        currentpage = data_backend.get_item(pagename)
        currentrev = currentpage.get_revision(-1)

    except (NoSuchRevisionError, NoSuchItemError, ):
        # TODO: Handle Exception sanely
        pass

    currentrev = currentrev.revno


    if currentrev == 0:  # Revision enumeration starts with 0 in the backend
        request.theme.add_msg(_("No older revisions available!"), "error")
        Page.from_item(request, currentpage).send_page()
        return

    # now we have made sure that we have at least 2 revisions (revno 0 and 1)

    if date: # this is how we get called from RecentChanges
             # try to find the latest rev1 before bookmark <date>
        revs = currentpage.list_revisions()
        revs.reverse()  # begin with latest rev
        for revno in revs:
            try:
                revision = currentpage.get_revision(revno)
            except NoSuchRevisionError:
                # TODO: Handle Exception sanely
                pass

            if revision[EDIT_LOG_MTIME] <= date:
                rev1 = revision.revno
                break
        else:
            rev1 = revno  # if we didn't find a rev, we just take oldest rev we have
        rev2 = -1  # and compare it with latest we have

    # Start output
    # This action generates content in the user language
    request.setContentLanguage(request.lang)

    request.emit_http_headers()
    request.theme.send_title(_('Diff for "%s"') % (pagename, ), pagename=pagename, allow_doubleclick=1)

    if rev1 >= 0 and rev2 >= 0 and rev1 > rev2 or rev1 == -1 and rev2 >= 0:
        rev1, rev2 = rev2, rev1

    oldrev, newrev = rev1, rev2

    try:
        oldrevision = currentpage.get_revision(oldrev)
        newrevision = currentpage.get_revision(newrev)

    except NoSuchRevisionError:
        ##request.makeForbidden(404, "The revision you tried to access does not exist.")  #XXX Localize this?
        # TODO: Handle Exception sanely
        pass

    edit_count = abs(newrev - oldrev)

    f = request.formatter
    request.write(f.div(1, id="content"))

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
        request.write(f.rawHTML(diff_html.diff(request, oldrevision.read(), newrevision.read())))
        Page.from_item(request, currentpage).send_page(count_hit=0, content_only=1, content_id="content-below-diff")

    else:
        from MoinMoin.util import diff_text
        oldlines = oldrevision.read().split('\n')
        newlines = newrevision.read().split('\n')
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

