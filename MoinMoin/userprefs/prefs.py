# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Preferences Form

    @copyright: 2001-2004 Juergen Hermann <jh@web.de>,
                2003-2007 MoinMoin:ThomasWaldmann,
                2010 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import time

from flask import flaskg

from MoinMoin import _, N_
from MoinMoin import user, util, wikiutil, events
from MoinMoin.theme import load_theme_fallback
from MoinMoin.userprefs import UserPrefBase

from flask import current_app as app

from flask import render_template

#################################################################
# This is still a mess.
#
# The plan for refactoring would be:
# split the plugin into multiple preferences pages:
#    - account details (name, email, timezone, ...)
#    - wiki settings (editor, fancy diffs, theme, ...)
#    - quick links (or leave in wiki settings?)
####

_date_formats = {# datetime_fmt & date_fmt
        'iso': '%Y-%m-%d %H:%M:%S & %Y-%m-%d',
        'us': '%m/%d/%Y %I:%M:%S %p & %m/%d/%Y',
        'euro': '%d.%m.%Y %H:%M:%S & %d.%m.%Y',
        'rfc': '%a %b %d %H:%M:%S %Y & %a %b %d %Y',
    }

def _user(request):
    """ Create elementary user attributes """
    u = flaskg.user
    user_params = dict(name=dict(param=u.name, title=_("Name"), comment=_("(Use FirstnameLastname)")),
                       aliasname=dict(param=u.aliasname, title=_("Alias-Name"), comment=""),
                       email=dict(param=u.email, title=_("Email"), comment=""),
                       css_url=dict(param=u.css_url, title=_("User CSS URL"), comment=_("(Leave it empty for disabling user CSS)")))
    return user_params

def _dtfmt_select(request):
    """ Create date format selection. """
    date_formats = [dict(value="", text=_('Default'))]
    dt_d_combined = '%s & %s' % (flaskg.user.datetime_fmt, flaskg.user.date_fmt)

    for key in _date_formats.keys():
        selected = ""
        if _date_formats[key] == dt_d_combined[0]:
            selected = "selected"
        date_formats.append(dict(value=key, text=_date_formats[key], selected=selected))
    return date_formats

def _theme_select(request):
    """ Create theme selection. """
    cur_theme = flaskg.user.valid and flaskg.user.theme_name or app.cfg.theme_default

    theme_selection = [dict(value="<default>", text="&lt;%s&gt;" % _("Default"), selected="")]
    for theme in wikiutil.getPlugins('theme', app.cfg):
        selected = ""
        if theme == cur_theme:
            selected = "selected"
        theme_selection.append(dict(value=theme,
                                    text=theme,
                                    selected=selected))
    return theme_selection

def _editor_default_select(request):
    """ Create editor selection. """
    editor_default = flaskg.user.valid and flaskg.user.editor_default or app.cfg.editor_default
    options = [("<default>", "&lt;%s&gt;" % _("Default"))]
    editor_default_selection = []
    for editor in ['text', 'gui', ]:
        selected = ""
        if editor == editor_default:
            selected = "selected"
        editor_default_selection.append(dict(value=editor,
                                             text=editor,
                                             selected=selected))
    return editor_default_selection

def _prefered_editor(request):
    """ Create editor selection. """
    editor_ui = flaskg.user.valid and flaskg.user.editor_ui or app.cfg.editor_ui
    prefered_editor = [dict(value="<default>", text="&lt;%s&gt;" % _("Default"), selected="selected"),
                       dict(value="theonepreferred", text=_("the one preferred"), selected=""),
                       dict(value="freechoice", text=_("free choice"), selected="")]
    return prefered_editor

def _tz_select(request, enabled=True):
    """ Create time zone selection. """
    tz = 0
    if flaskg.user.valid:
        tz_offset = int(flaskg.user.tz_offset)

    time_zone = []
    now = time.time()
    for halfhour in range(-47, 48):
        offset = halfhour * 1800
        t = now + offset
        selected = ""
        if offset == tz_offset:
            selected = "selected"
        time_zone.append(dict(value=str(offset),
                              selected=selected,
                              text='%s [%s%s:%s]' % (
                time.strftime(app.cfg.datetime_fmt, time.gmtime(t)),
                "+-"[offset < 0],
                "%02d" % (abs(offset) / 3600),
                "%02d" % (abs(offset) % 3600 / 60),
            ),
        ))
    return time_zone

def _lang_select(request, enabled=True):
    """ Create language selection. """
    from MoinMoin import i18n
    cur_lang = flaskg.user.language

    langs = i18n.wikiLanguages().items()
    langs.sort(lambda x, y: cmp(x[1]['x-language'], y[1]['x-language']))
    languages = [dict(value="", text="&lt;%s&gt;" % _('Browser setting'), selected="")]
    for lang in langs:
        selected = ""
        name = lang[1]['x-language']
        if name == cur_lang:
            selected = "selected"
        languages.append(dict(value=lang[0],
                         text=name,
                         selected=selected))
    return languages

def get_userprefs_info(request):
    u = flaskg.user
    # boolean user options
    general_options = []
    checkbox_fields = app.cfg.user_checkbox_fields
    checkbox_fields.sort(lambda a, b: cmp(a[1](_), b[1](_)))
    for key, label in checkbox_fields:
        if not key in app.cfg.user_checkbox_remove:
            disabled = ""
            if key in app.cfg.user_checkbox_disable:
                disabled = "disabled"
            checked = ""
            if getattr(u, key, False):
                checked = "checked"
            general_options.append(dict(name=key,
                                        checked=checked,
                                        disabled=disabled,
                                        text=label(_)))

    server_time = "%s %s (UTC)" % (_('Server time is'), time.strftime(app.cfg.datetime_fmt, time.gmtime()))
    your_time = "%s %s" % (_('Your time is'), time.strftime(app.cfg.datetime_fmt, time.gmtime(time.time())))

    return dict(user=_user(request),
                date_formats=dict(title=_("Date format"), param=_dtfmt_select(request)),
                editor_default_selection=dict(title=_("Editor Preference"), param=_editor_default_select(request)),
                edit_rows=dict(title=_("Editor size"), param=u.edit_rows),
                general_options=dict(title=_("General options"), param=general_options),
                prefered_language=dict(title=_("Preferred language"), param=_lang_select(request)),
                prefered_editor=dict(title=_("Editor shown on UI"), param=_prefered_editor(request)),
                quick_links=dict(title="Quick links", param='\n'.join(u.getQuickLinks())),
                server_time=server_time,
                theme_selection=dict(title=_("Preferred theme"), param=_theme_select(request)),
                time_zone=dict(title=_("Time zone"), param=_tz_select(request)),
                your_time=your_time)

class Settings(UserPrefBase):
    def __init__(self, request):
        """ Initialize user settings form. """
        UserPrefBase.__init__(self, request)
        self.request = request
        self.cfg = app.cfg
        _ = self._
        self.title = _("Preferences")
        self.name = 'prefs'

    def _decode_pagelist(self, key):
        """ Decode list of pages from form input

        Each line is a page name, empty lines ignored.

        @param key: the form key to get
        @rtype: list of unicode strings
        @return: list of normalized names
        """
        text = self.request.form.get(key, '')
        text = text.replace('\r', '')
        items = []
        for item in text.split('\n'):
            item = item.strip()
            if not item:
                continue
            items.append(item)
        return items

    def _save_user_prefs(self):
        _ = self._
        request = self.request
        form = request.form
        u = flaskg.user

        if not 'name' in u.auth_attribs:
            # Require non-empty name
            new_name = wikiutil.clean_input(form.get('name', u.name)).strip()

            # Don't allow changing the name to an invalid one
            if not user.isValidName(request, new_name):
                return 'error', _("""Invalid user name '%s'.
Name may contain any Unicode alpha numeric character, with optional one
space between words. Group page name is not allowed.""") % wikiutil.escape(new_name)

            # Is this an existing user trying to change information or a new user?
            # Name required to be unique. Check if name belong to another user.
            existing_id = user.getUserId(request, new_name)
            if existing_id is not None and existing_id != u.id:
                return 'error', _("This user name already belongs to somebody else.")

            if not new_name:
                return 'error', _("Empty user name. Please enter a user name.")

            # done sanity checking the name, set it
            u.name = new_name


        if not 'email' in u.auth_attribs:
            # try to get the email
            new_email = wikiutil.clean_input(form.get('email', u.email)).strip()

            # Require email
            if not new_email and 'email' not in app.cfg.user_form_remove:
                return 'error', _("Please provide your email address. If you lose your"
                                  " login information, you can get it by email.")

            # Email should be unique - see also MoinMoin/script/accounts/moin_usercheck.py
            if new_email and app.cfg.user_email_unique:
                other = user.get_by_email_address(request, new_email)
                if other is not None and other.id != u.id:
                    return 'error', _("This email already belongs to somebody else.")

            # done checking the email, set it
            u.email = new_email


        if not 'aliasname' in u.auth_attribs:
            # aliasname
            u.aliasname = wikiutil.clean_input(form.get('aliasname', '')).strip()

        # editor size
        u.edit_rows = util.web.getIntegerInput(request, 'edit_rows', u.edit_rows, 0, 999)

        # try to get the editor
        u.editor_default = wikiutil.clean_input(form.get('editor_default', self.cfg.editor_default))
        u.editor_ui = wikiutil.clean_input(form.get('editor_ui', self.cfg.editor_ui))

        # time zone
        u.tz_offset = util.web.getIntegerInput(request, 'tz_offset', u.tz_offset, -84600, 84600)

        # datetime format
        try:
            dt_d_combined = _date_formats.get(form['datetime_fmt'], '')
            u.datetime_fmt, u.date_fmt = dt_d_combined.split(' & ')
        except (KeyError, ValueError):
            pass # keep the default

        # try to get the (optional) theme
        theme_name = wikiutil.clean_input(form.get('theme_name', self.cfg.theme_default))
        if theme_name != u.theme_name:
            # if the theme has changed, load the new theme
            # so the user has a direct feedback
            # WARNING: this should be refactored (i.e. theme load
            # after userform handling), cause currently the
            # already loaded theme is just replaced (works cause
            # nothing has been emitted yet)
            u.theme_name = theme_name
            if load_theme_fallback(request, theme_name) > 0:
                theme_name = wikiutil.escape(theme_name)
                return 'error', _("The theme '%(theme_name)s' could not be loaded!") % locals()

        # try to get the (optional) preferred language
        u.language = wikiutil.clean_input(form.get('language', ''))

        # I want to handle all inputs from user_form_fields, but
        # don't want to handle the cases that have already been coded
        # above.
        # This is a horribly fragile kludge that's begging to break.
        # Something that might work better would be to define a
        # handler for each form field, instead of stuffing them all in
        # one long and inextensible method.  That would allow for
        # plugins to provide methods to validate their fields as well.
        already_handled = ['name', 'email',
                           'aliasname', 'edit_rows', 'editor_default',
                           'editor_ui', 'tz_offset', 'datetime_fmt',
                           'theme_name', 'language', 'real_language']
        for field in self.cfg.user_form_fields:
            key = field[0]
            if ((key in self.cfg.user_form_disable)
                or (key in already_handled)):
                continue
            default = self.cfg.user_form_defaults[key]
            value = form.get(key, default)
            value = wikiutil.clean_input(value)
            setattr(u, key, value)

        # checkbox options
        for key, label in self.cfg.user_checkbox_fields:
            if key not in self.cfg.user_checkbox_disable and key not in self.cfg.user_checkbox_remove:
                value = form.get(key, 'False')
                try:
                    value = value == 'True'
                except ValueError:
                    # value we got is crap, do not setattr this value, just pass
                    pass
                else:
                    setattr(u, key, value)

        # quicklinks for navibar
        u.quicklinks = self._decode_pagelist('quicklinks')

        # save data
        u.save()
        if u.disabled:
            # set valid to false so the current request won't
            # show the user as logged-in any more
            u.valid = False

        result = _("User preferences saved!")
        return result


    def handle_form(self):
        request = self.request
        form = request.form
        _ = self._

        if 'cancel' in form:
            return

        if request.method != 'POST':
            return

        if not wikiutil.checkTicket(request, form.get('ticket', '')):
            return _('Please use the interactive user interface to use action %(actionname)s!') % {'actionname': 'userprefs.prefs'}

        if 'save' in form: # Save user profile
            return self._save_user_prefs()

    def _dtfmt_select(self):
        """ Create date format selection. """
        _ = self._
        try:
            dt_d_combined = '%s & %s' % (flaskg.user.datetime_fmt, flaskg.user.date_fmt)
            selected = [
                k for k, v in _date_formats.items()
                    if v == dt_d_combined][0]
        except IndexError:
            selected = ''
        options = [('', _('Default'))] + _date_formats.items()

        return util.web.makeSelection('datetime_fmt', options, selected)

    def create_form(self):
        return render_template('userprefs.html',
                                             userprefs=get_userprefs_info(self.request),
                                             ticket=wikiutil.createTicket(self.request))

