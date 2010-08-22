# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - user settings action

    @copyright: 2006 Radomir Dopieralski,
                2007, 2008 MoinMoin:JohannesBerg,
                2010 MoinMoin:DiogenesAugusto
    @license: GNU GPL, see COPYING for details.
"""
from flask import render_template, flash, flaskg

from flask import current_app as app

from MoinMoin import _, N_
from MoinMoin import Page, wikiutil
from MoinMoin.widget import html

def _handle_submission(request):
    """ Handle GET and POST requests of preferences forms.

    Return error msg_class, msg tuple or None, None.
    """
    sub = request.values.get('handler')

    if sub in app.cfg.userprefs_disabled:
        return None, None

    try:
        cls = wikiutil.importPlugin(app.cfg, 'userprefs', sub, 'Settings')
    except wikiutil.PluginMissingError:
        # we never show this plugin to click on so no need to
        # give a message here
        return None, None

    obj = cls(request)
    if not obj.allowed():
        return None, None
    res = obj.handle_form()
    if isinstance(res, tuple):
        return res
    # backward compatibility for userprefs plugins,
    # they just get 'dialog'-style messages.
    return None, res

def _create_prefs_page(request, sel=None):
    plugins = wikiutil.getPlugins('userprefs', app.cfg)
    ret = html.P()
    ret.append(html.Text(_("Please choose:")))
    ret.append(html.BR())
    items = html.UL()
    ret.append(items)
    for sub in plugins:
        if sub in app.cfg.userprefs_disabled:
            continue
        cls = wikiutil.importPlugin(app.cfg, 'userprefs', sub, 'Settings')
        obj = cls(request)
        if not obj.allowed():
            continue
        url = request.page.url(request, {'do': 'userprefs', 'sub': sub})
        lnk = html.LI().append(html.A(href=url).append(html.Text(obj.title)))
        items.append(lnk)
    return unicode(ret)


def _create_page(request, cancel=False):
    # returns text, title
    pagename = request.page.page_name

    sub = request.args.get('sub', '')
    cls = None
    if sub and sub not in app.cfg.userprefs_disabled:
        try:
            cls = wikiutil.importPlugin(app.cfg, 'userprefs', sub, 'Settings')
        except wikiutil.PluginMissingError:
            # cls is already None
            pass

    obj = cls and cls(request)

    if not obj or not obj.allowed():
        return _create_prefs_page(request), None

    return obj.create_form(), obj.title


def execute(pagename, request):
    if not flaskg.user.valid:
        actname = __name__.split('.')[-1]
        flash(_("You must login to use this action: %(action)s.") % {"action": actname}, "error")
        return Page.Page(request, pagename).send_page()

    text, title = _create_page(request)
    if title:
        # XXX: we would like to make "Settings" here a link back
        #      to the generic userprefs page but that is impossible
        #      due to the way the title is emitted and the theme is
        #      responsible for doing the linking....
        title = _("Settings") + ": " + title
    else:
        title = _("Settings")
    content = "%s%s%s" % (request.formatter.startContent("content"), text, request.formatter.endContent())
    return render_template('content.html', title=title, content=content)

