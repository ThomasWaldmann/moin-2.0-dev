# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - RecentChanges Macro

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import time

from MoinMoin import util, wikiutil
from MoinMoin.Page import Page
from MoinMoin.logfile import editlog

_DAYS_SELECTION = [1, 2, 3, 7, 14, 30, 60, 90]
_MAX_DAYS = 7
_MAX_PAGENAME_LENGTH = 15 # 35
_MAX_COMMENT_LENGTH = 20

#############################################################################
### RecentChanges Macro
#############################################################################

Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]

def format_comment(request, line):
    comment = line.comment
    action = line.action
    _ = request.getText
    if '/REVERT' in action:
        rev = int(line.extra)
        comment = (_("Revert to revision %(rev)d.") % {'rev': rev}) + " " + comment
    elif '/RENAME' in action:
        comment = (_("Renamed from '%(oldpagename)s'.") % {'oldpagename': line.extra}) + " " + comment

    return wikiutil.make_breakable(comment, _MAX_COMMENT_LENGTH)

def format_page_edits(macro, lines, bookmark_mtime):
    request = macro.request
    _ = request.getText
    d = {} # dict for passing stuff to theme
    line = lines[0]
    pagename = line.pagename
    rev = line.rev
    tnow = time.time()
    is_new = lines[-1].action == 'SAVENEW'
    is_renamed = lines[-1].action == 'SAVE/RENAME'
    # check whether this page is newer than the user's bookmark
    hilite = line.mtime > (bookmark_mtime or line.mtime)
    page = Page(request, pagename)

    html_link = ''
    if not page.exists():
        img = request.theme.make_icon('deleted')
        revbefore = rev - 1
        if revbefore and page.exists(rev=revbefore, domain='standard'):
            # indicate page was deleted and show diff to last existing revision of it
            html_link = page.link_to_raw(request, img, querystr={'action': 'diff'}, rel='nofollow')
        else:
            # just indicate page was deleted
            html_link = img
    elif page.isConflict():
        img = request.theme.make_icon('conflict')
        html_link = page.link_to_raw(request, img, querystr={'action': 'edit'}, rel='nofollow')
    elif hilite:
        # show special icons if change was after the user's bookmark
        if is_new:
            img = 'new'
        elif is_renamed:
            img = 'renamed'
        else:
            img = 'updated'
        img = request.theme.make_icon(img)
        html_link = page.link_to_raw(request, img, querystr={'action': 'diff', 'date': '%d' % wikiutil.timestamp2version(bookmark_mtime)}, rel='nofollow')
    else:
        # show "DIFF" icon else
        img = request.theme.make_icon('diffrc')
        html_link = page.link_to_raw(request, img, querystr={'action': 'diff'}, rel='nofollow')

    # print name of page, with a link to it
    force_split = len(page.page_name) > _MAX_PAGENAME_LENGTH

    d['icon_html'] = html_link
    d['pagelink_html'] = page.link_to(request, text=page.split_title(force=force_split))

    # print time of change
    d['time_html'] = None
    if request.cfg.changed_time_fmt:
        tdiff = (tnow - line.mtime) / 60
        if tdiff < 100:
            d['time_html'] = _("%(mins)dm ago") % {
                'mins': tdiff}
        else:
            d['time_html'] = time.strftime(request.cfg.changed_time_fmt, line.time_tuple)

    # print editor name or IP
    d['editors'] = None
    if request.cfg.show_names:
        if len(lines) > 1:
            counters = {}
            for idx in range(len(lines)):
                name = lines[idx].getEditor(request)
                if not name in counters:
                    counters[name] = []
                counters[name].append(idx+1)
            poslist = [(v, k) for k, v in counters.items()]
            poslist.sort()
            d['editors'] = []
            for positions, name in poslist:
                d['editors'].append("%s&nbsp;[%s]" % (
                    name, util.rangelist(positions)))
        else:
            d['editors'] = [line.getEditor(request)]

    comments = []
    for idx in range(len(lines)):
        comment = format_comment(request, lines[idx])
        if comment:
            comments.append((idx+1, wikiutil.escape(comment)))

    d['changecount'] = len(lines)
    d['comments'] = comments

    img = request.theme.make_icon('info')
    d['info_html'] = page.link_to_raw(request, img, querystr={'action': 'info'}, rel='nofollow')

    return request.theme.recentchanges_entry(d)

def cmp_lines(first, second):
    return cmp(first[0], second[0])

def print_abandoned(macro):
    request = macro.request
    _ = request.getText
    output = []
    d = {}
    page = macro.formatter.page
    pagename = page.page_name
    d['page'] = page
    d['q_page_name'] = wikiutil.quoteWikinameURL(pagename)
    msg = None

    # set max size in days
    max_days = min(int(request.values.get('max_days', 0)), _DAYS_SELECTION[-1])
    # default to _MAX_DAYS for users without bookmark
    if not max_days:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days

    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = None

    d['rc_update_bookmark'] = None
    output.append(request.theme.recentchanges_header(d))

    pages = set()
    last = int(time.time()) - (max_days * 24 * 60 * 60)
    glog = editlog.GlobalEditLog(request)
    for line in glog:
        if line.mtime > last:
            pages.add(line.pagename)
        else:
            break

    pages = set(request.rootpage.getPageList(include_underlay=False)) - pages

    last_edits = []
    for pagename in pages:
        llog = editlog.LocalEditLog(request, rootpagename=pagename)
        for line in llog:
            last_edits.append(line)
            break
    last_edits.sort()

    this_day = 0
    for line in last_edits:
        line.time_tuple = request.user.getTime(line.mtime)
        day = line.time_tuple[0:3]
        if day != this_day:
            d['bookmark_link_html'] = None
            d['date'] = request.user.getFormattedDate(line.mtime)
            output.append(request.theme.recentchanges_daybreak(d))
            this_day = day
        output.append(format_page_edits(macro, [line], None))

    d['rc_msg'] = msg
    output.append(request.theme.recentchanges_footer(d))
    return ''.join(output)


def macro_RecentChanges(macro, abandoned=False):
    # handle abandoned keyword
    if abandoned:
        return print_abandoned(macro)

    request = macro.request
    _ = request.getText
    output = []
    user = request.user
    page = macro.formatter.page
    pagename = page.page_name

    d = {}
    d['page'] = page
    d['q_page_name'] = wikiutil.quoteWikinameURL(pagename)

    glog = editlog.GlobalEditLog(request)

    tnow = time.time()
    msg = ""

    # get bookmark from valid user
    bookmark_usecs = request.user.getBookmark() or 0
    bookmark_mtime = wikiutil.version2timestamp(bookmark_usecs)

    # add bookmark link if valid user
    d['rc_curr_bookmark'] = None
    d['rc_update_bookmark'] = None
    if request.user.valid:
        d['rc_curr_bookmark'] = _('(no bookmark set)')
        if bookmark_usecs:
            currentBookmark = user.getFormattedDateTime(bookmark_mtime)
            currentBookmark = _('(currently set to %s)') % currentBookmark
            deleteBookmark = page.link_to(request, _("Delete bookmark"), querystr={'action': 'bookmark', 'time': 'del'}, rel='nofollow')
            d['rc_curr_bookmark'] = currentBookmark + ' ' + deleteBookmark

        version = wikiutil.timestamp2version(tnow)
        d['rc_update_bookmark'] = page.link_to(request, _("Set bookmark"), querystr={'action': 'bookmark', 'time': '%d' % version}, rel='nofollow')

    # set max size in days
    max_days = min(int(request.values.get('max_days', 0)), _DAYS_SELECTION[-1])
    # default to _MAX_DAYS for useres without bookmark
    if not max_days and not bookmark_usecs:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days

    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = []

    output.append(request.theme.recentchanges_header(d))

    pages = {}
    ignore_pages = {}

    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0

    for line in glog:

        if not request.user.may.read(line.pagename):
            continue

        line.time_tuple = request.user.getTime(line.mtime)
        day = line.time_tuple[0:3]
        hilite = line.mtime > (bookmark_mtime or line.mtime)

        if ((this_day != day or (not hilite and not max_days))) and len(pages) > 0:
            # new day or bookmark reached: print out stuff
            this_day = day
            for p in pages:
                ignore_pages[p] = None
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()

            if request.user.valid:
                bmtime = pages[0][0].mtime
                d['bookmark_link_html'] = page.link_to(request, _("Set bookmark"), querystr={'action': 'bookmark', 'time': '%d' % bmtime}, rel='nofollow')
            else:
                d['bookmark_link_html'] = None
            d['date'] = request.user.getFormattedDate(pages[0][0].mtime)
            output.append(request.theme.recentchanges_daybreak(d))

            for p in pages:
                output.append(format_page_edits(macro, p, bookmark_mtime))
            pages = {}
            day_count += 1
            if max_days and (day_count >= max_days):
                break

        elif this_day != day:
            # new day but no changes
            this_day = day

        if line.pagename in ignore_pages:
            continue

        # end listing by default if user has a bookmark and we reached it
        if not max_days and not hilite:
            msg = _('[Bookmark reached]')
            break

        if line.pagename in pages:
            pages[line.pagename].append(line)
        else:
            pages[line.pagename] = [line]
    else:
        if len(pages) > 0:
            # end of loop reached: print out stuff
            # XXX duplicated code from above
            # but above does not trigger if we have the first day in wiki history
            for p in pages:
                ignore_pages[p] = None
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()

            if request.user.valid:
                bmtime = pages[0][0].mtime
                d['bookmark_link_html'] = page.link_to(request, _("Set bookmark"), querystr={'action': 'bookmark', 'time': '%d' % bmtime}, rel='nofollow')
            else:
                d['bookmark_link_html'] = None
            d['date'] = request.user.getFormattedDate(pages[0][0].mtime)
            output.append(request.theme.recentchanges_daybreak(d))

            for p in pages:
                output.append(format_page_edits(macro, p, bookmark_mtime))

    d['rc_msg'] = msg
    output.append(request.theme.recentchanges_footer(d))

    return ''.join(output)


