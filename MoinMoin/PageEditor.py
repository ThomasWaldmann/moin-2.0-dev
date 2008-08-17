# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PageEditor class

    PageEditor is used for r/w access to a wiki page (edit, rename, delete operations).

    TODO:
    * See comments in Page.py, most apply here, too.
    * The editor code should be modularized so we will be able to use it for any
      text/* mimetype data with some special features enabled depending on the
      mimetype (e.g. enable wiki markup help when editing wiki mimetype).

    @copyright: 2000-2004 by Juergen Hermann <jh@web.de>,
                2005-2007 by MoinMoin:ThomasWaldmann,
                2007 by MoinMoin:ReimarBauer,
                2008 by MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import errno
import time
import shutil

from MoinMoin import config, caching, wikiutil, error, user
from MoinMoin.Page import Page
from MoinMoin.widget import html
from MoinMoin.widget.dialog import Status
from MoinMoin.logfile import eventlog
from MoinMoin.mail.sendmail import encodeSpamSafeEmail
from MoinMoin.support.python_compatibility import set
from MoinMoin.util import timefuncs, web
from MoinMoin.storage.error import BackendError
from MoinMoin.events import PageDeletedEvent, PageRenamedEvent, PageCopiedEvent, PageRevertedEvent
from MoinMoin.events import PagePreSaveEvent, Abort, send_event
from MoinMoin.wikiutil import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID
from MoinMoin.storage.error import ItemAlreadyExistsError, RevisionAlreadyExistsError
from MoinMoin.storage import DELETED, EDIT_LOG_ADDR, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
                             EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_ACTION

import MoinMoin.events.notification as notification

# used for merging
conflict_markers = ("\n---- /!\\ '''Edit conflict - other version:''' ----\n",
                    "\n---- /!\\ '''Edit conflict - your version:''' ----\n",
                    "\n---- /!\\ '''End of edit conflict''' ----\n")


#############################################################################
### Javascript code for editor page
#############################################################################

# we avoid the "--" operator to make this XHTML happy!
_countdown_js = """
%(countdown_script)s
<script type="text/javascript">
var countdown_timeout_min = %(lock_timeout)s
var countdown_lock_expire = "%(lock_expire)s"
var countdown_lock_mins = "%(lock_mins)s"
var countdown_lock_secs = "%(lock_secs)s"
addLoadEvent(countdown)
</script>
"""


#############################################################################
### PageEditor - Edit pages
#############################################################################
class PageEditor(Page):
    """ Editor for a wiki page. """

    # exceptions for .saveText()
    class SaveError(error.Error):
        pass
    class RevertError(SaveError):
        pass
    class AccessDenied(SaveError):
        pass
    class Immutable(AccessDenied):
        pass
    class NoAdmin(AccessDenied):
        pass
    class EmptyPage(SaveError):
        pass
    class Unchanged(SaveError):
        pass
    class EditConflict(SaveError):
        pass
    class CouldNotLock(SaveError):
        pass

    def __init__(self, request, page_name, **keywords):
        """ Create page editor object.

        @param page_name: name of the page
        @param request: the request object
        @keyword do_revision_backup: if 0, suppress making a page backup per revision
        @keyword do_editor_backup: if 0, suppress saving of draft copies
        @keyword uid_override: override user id and name (default None)
        """
        Page.__init__(self, request, page_name, **keywords)
        self._ = request.getText

        self.do_revision_backup = keywords.get('do_revision_backup', 1)
        self.do_editor_backup = keywords.get('do_editor_backup', 1)
        self.uid_override = keywords.get('uid_override', None)

        if self._item is None:
            self._item = self._backend.create_item(self.page_name)

        self.lock = PageLock(self)

    def mergeEditConflict(self, origrev):
        """ Try to merge current page version with new version the user tried to save

        @param origrev: the original revision the user was editing
        @rtype: bool
        @return: merge success status
        """
        from MoinMoin.util import diff3
        allow_conflicts = 1

        # Get current editor text
        savetext = self.get_raw_body()

        # The original text from the revision the user was editing
        original_text = Page(self.request, self.page_name, rev=origrev).get_raw_body()

        # The current revision someone else saved
        saved_text = Page(self.request, self.page_name).get_raw_body()

        # And try to merge all into one with edit conflict separators
        verynewtext = diff3.text_merge(original_text, saved_text, savetext,
                                       allow_conflicts, *conflict_markers)
        if verynewtext:
            self.set_raw_body(verynewtext)
            return True

        # this should never happen, except for empty pages
        return False

    def sendconfirmleaving(self):
        """ Prevents moving away from the page without saving it. """
        _ = self._
        self.request.write(u'''\
<script type="text/javascript">
    var flgChange = false;
    function confirmleaving() {
        if ( flgChange )
            return "%s";
    }
</script>
''' % _("Your changes are not saved!"))

    def sendEditor(self, **kw):
        """ Send the editor form page.

        @keyword preview: if given, show this text in preview mode
        @keyword staytop: don't go to #preview
        @keyword comment: comment field (when preview is true)
        """
        from MoinMoin import i18n
        from MoinMoin.action import SpellCheck
        request = self.request
        form = request.form
        _ = self._

        raw_body = ''
        msg = None
        conflict_msg = None
        edit_lock_message = None
        preview = kw.get('preview', None)
        staytop = kw.get('staytop', 0)

        from MoinMoin.formatter.text_html import Formatter
        request.formatter = Formatter(request, store_pagelinks=1)

        # check edit permissions
        if not request.user.may.write(self.page_name):
            msg = _('You are not allowed to edit this page.')
        elif self.rev >= 0:
            # Trying to edit an old version, this is not possible via
            # the web interface, but catch it just in case...
            msg = _('Cannot edit old revisions!')
        else:
            try:
                # try to acquire edit lock
                ok, edit_lock_message = self.lock.acquire()
                if not ok:
                    # failed to get the lock
                    if preview is not None:
                        edit_lock_message = _('The lock you held timed out. Be prepared for editing conflicts!'
                            ) + "<br>" + edit_lock_message
                    else:
                        msg = edit_lock_message
            except OSError, err:
                if err.errno == errno.ENAMETOOLONG:
                    msg = _("Page name is too long, try shorter name.")
                else:
                    raise

        # Did one of the prechecks fail?
        if msg:
            request.theme.add_msg(msg, "error")
            self.send_page()
            return

        # Emmit http_headers after checks (send_page)
        request.disableHttpCaching(level=2)
        request.emit_http_headers()

        # check if we want to load a draft
        use_draft = None
        if 'button_load_draft' in form:
            wanted_draft_timestamp = int(form.get('draft_ts', ['0'])[0])
            if wanted_draft_timestamp:
                draft = self._load_draft()
                if draft is not None:
                    draft_timestamp, draft_rev, draft_text = draft
                    if draft_timestamp == wanted_draft_timestamp:
                        use_draft = draft_text

        # Check for draft / normal / preview submit
        if use_draft is not None:
            title = _('Draft of "%(pagename)s"')
            # Propagate original revision
            rev = int(form['draft_rev'][0])
            self.set_raw_body(use_draft, modified=1)
            preview = use_draft
        elif preview is None:
            title = _('Edit "%(pagename)s"')
        else:
            title = _('Preview of "%(pagename)s"')
            # Propagate original revision
            rev = request.rev
            self.set_raw_body(preview, modified=1)

        # send header stuff
        lock_timeout = self.lock.timeout / 60
        lock_page = wikiutil.escape(self.page_name, quote=1)
        lock_expire = _("Your edit lock on %(lock_page)s has expired!") % {'lock_page': lock_page}
        lock_mins = _("Your edit lock on %(lock_page)s will expire in # minutes.") % {'lock_page': lock_page}
        lock_secs = _("Your edit lock on %(lock_page)s will expire in # seconds.") % {'lock_page': lock_page}

        # get request parameters
        try:
            text_rows = int(form['rows'][0])
        except StandardError:
            text_rows = self.cfg.edit_rows
            if request.user.valid:
                text_rows = int(request.user.edit_rows)

        if preview is not None:
            # Check for editing conflicts
            if not self.exists():
                # page does not exist, are we creating it?
                if rev:
                    conflict_msg = _('Someone else deleted this page while you were editing!')
            elif rev != self.current_rev():
                conflict_msg = _('Someone else changed this page while you were editing!')
                if self.mergeEditConflict(rev):
                    conflict_msg = _("""Someone else saved this page while you were editing!
Please review the page and save then. Do not save this page as it is!""")
                    rev = self.current_rev()
            if conflict_msg:
                # We don't show preview when in conflict
                preview = None

        elif self.exists(includeDeleted=True):
            # revision of existing page
            rev = self.current_rev()
        else:
            # page creation
            rev = -1

        # Page editing is done using user language
        request.setContentLanguage(request.lang)

        # Get the text body for the editor field.
        # TODO: what about deleted pages? show the text of the last revision or use the template?
        if preview is not None:
            raw_body = self.get_raw_body()
            if use_draft:
                request.theme.add_msg(_("[Content loaded from draft]"), 'info')
        elif self.exists():
            # If the page exists, we get the text from the page.
            # TODO: maybe warn if template argument was ignored because the page exists?
            raw_body = self.get_raw_body()
        elif 'template' in form:
            # If the page does not exist, we try to get the content from the template parameter.
            template_page = form['template'][0]
            if request.user.may.read(template_page):
                raw_body = Page(request, template_page).get_raw_body()
                if raw_body:
                    request.theme.add_msg(_("[Content of new page loaded from %s]") % (template_page, ), 'info')
                else:
                    request.theme.add_msg(_("[Template %s not found]") % (template_page, ), 'warning')
            else:
                request.theme.add_msg(_("[You may not read %s]") % (template_page, ), 'error')

        # Make backup on previews - but not for new empty pages
        if not use_draft and preview and raw_body:
            self._save_draft(raw_body, rev)

        draft_message = None
        loadable_draft = False
        if preview is None:
            draft = self._load_draft()
            if draft is not None:
                draft_timestamp, draft_rev, draft_text = draft
                if draft_text != raw_body:
                    loadable_draft = True
                    page_rev = rev
                    draft_timestamp_str = request.user.getFormattedDateTime(draft_timestamp)
                    draft_message = _(u"'''<<BR>>Your draft based on revision %(draft_rev)d (saved %(draft_timestamp_str)s) can be loaded instead of the current revision %(page_rev)d by using the load draft button - in case you lost your last edit somehow without saving it.''' A draft gets saved for you when you do a preview, cancel an edit or unsuccessfully save.", wiki=True) % locals()

        # Setup status message
        status = [kw.get('msg', ''), conflict_msg, edit_lock_message, draft_message]
        status = [msg for msg in status if msg]
        status = ' '.join(status)
        status = Status(request, content=status)
        request.theme.add_msg(status, "dialog")

        request.theme.send_title(
            title % {'pagename': self.split_title(), },
            page=self,
            html_head=self.lock.locktype and (
                _countdown_js % {
                     'countdown_script': request.theme.externalScript('countdown'),
                     'lock_timeout': lock_timeout,
                     'lock_expire': lock_expire,
                     'lock_mins': lock_mins,
                     'lock_secs': lock_secs,
                    }) or '',
            editor_mode=1,
        )

        request.write(request.formatter.startContent("content"))

        # Generate default content for new pages
        if not raw_body:
            raw_body = _('Describe %s here.') % (self.page_name, )

        # send form
        request.write('<form id="editor" method="post" action="%s/%s#preview" onSubmit="flgChange = false;">' % (
            request.getScriptname(),
            wikiutil.quoteWikinameURL(self.page_name),
            ))

        # yet another weird workaround for broken IE6 (it expands the text
        # editor area to the right after you begin to type...). IE sucks...
        # http://fplanque.net/2003/Articles/iecsstextarea/
        request.write('<fieldset style="border:none;padding:0;">')

        request.write(unicode(html.INPUT(type="hidden", name="action", value="edit")))

        # Send revision of the page our edit is based on
        request.write('<input type="hidden" name="rev" value="%d">' % (rev, ))

        # Create and send a ticket, so we can check the POST
        request.write('<input type="hidden" name="ticket" value="%s">' % wikiutil.createTicket(request))

        # Save backto in a hidden input
        backto = form.get('backto', [None])[0]
        if backto:
            request.write(unicode(html.INPUT(type="hidden", name="backto", value=backto)))

        # button bar
        button_spellcheck = '<input class="button" type="submit" name="button_spellcheck" value="%s" onClick="flgChange = false;">' % _('Check Spelling')

        save_button_text = _('Save Changes')
        cancel_button_text = _('Cancel')

        if self.cfg.page_license_enabled:
            request.write('<p><em>', _(
"""By hitting '''%(save_button_text)s''' you put your changes under the %(license_link)s.
If you don't want that, hit '''%(cancel_button_text)s''' to cancel your changes.""", wiki=True) % {
                'save_button_text': save_button_text,
                'cancel_button_text': cancel_button_text,
                'license_link': wikiutil.getLocalizedPage(request, self.cfg.page_license_page).link_to(request),
            }, '</em></p>')


        request.write('''
<input class="button" type="submit" name="button_save" value="%s" onClick="flgChange = false;">
<input class="button" type="submit" name="button_preview" value="%s" onClick="flgChange = false;">
''' % (save_button_text, _('Preview'), ))

        if not (request.cfg.editor_force and request.cfg.editor_default == 'text'):
            request.write('''
<input id="switch2gui" style="display: none;" class="button" type="submit" name="button_switch" value="%s">
''' % (_('GUI Mode'), ))

        if loadable_draft:
            request.write('''
<input class="button" type="submit" name="button_load_draft" value="%s" onClick="flgChange = false;">
<input type="hidden" name="draft_ts" value="%d">
<input type="hidden" name="draft_rev" value="%d">
''' % (_('Load Draft'), draft_timestamp, draft_rev))

        request.write('''
%s
<input class="button" type="submit" name="button_cancel" value="%s">
<input type="hidden" name="editor" value="text">
''' % (button_spellcheck, cancel_button_text, ))

        # Trivial Change-checkbox to the top of the page, shows up only if user has JavaScript enabled. It's "linked" with the bottom's box (checking one checks both)
        if self.cfg.mail_enabled:
            request.write('''
<script type="text/javascript">
    <!--
    function toggle_trivial(CheckedBox)
    {
        TrivialBoxes = document.getElementsByName("trivial");
        for (var i = 0; i < TrivialBoxes.length; i++)
            TrivialBoxes[i].checked = CheckedBox.checked;
    }

    document.write('<input type="checkbox" name="trivial" id="chktrivialtop" value="1" %(checked)s onclick="toggle_trivial(this)">');
    document.write('<label for="chktrivialtop">%(label)s</label>');
    //-->
</script> ''' % {
                'checked': ('', 'checked')[form.get('trivial', ['0'])[0] == '1'],
                'label': _("Trivial change"),
            })

        from MoinMoin.security.textcha import TextCha
        request.write(TextCha(request).render())

        # Add textarea with page text
        self.sendconfirmleaving()

        lang = self.pi.get('language', request.cfg.language_default)

        request.write(
            u'''\
<textarea id="editor-textarea" name="savetext" lang="%(lang)s" dir="%(dir)s" rows="%(rows)d" cols="80"
          onChange="flgChange = true;" onKeyPress="flgChange = true;">\
%(text)s\
</textarea>''' % {
            'lang': lang,
            'dir': i18n.getDirection(lang),
            'rows': text_rows,
            'text': wikiutil.escape(raw_body)
        })

        request.write("<p>")
        request.write(_("Comment:"),
            ' <input id="editor-comment" type="text" name="comment" value="%s" size="80" maxlength="200"'
            ' onChange="flgChange = true;" onKeyPress="flgChange = true;">' % (
                wikiutil.escape(kw.get('comment', ''), 1), ))
        request.write("</p>")

        # Category selection
        filterfn = self.cfg.cache.page_category_regexact.search
        cat_pages = request.rootpage.getPageList(filter=filterfn)
        cat_pages = list(cat_pages)
        cat_pages.sort()
        cat_pages = [wikiutil.pagelinkmarkup(p) for p in cat_pages]
        cat_pages.insert(0, ('', _('<No addition>')))
        request.write("<p>")
        request.write(_('Add to: %(category)s') % {
            'category': unicode(web.makeSelection('category', cat_pages)),
        })

        if self.cfg.mail_enabled:
            request.write('''
&nbsp;

<input type="checkbox" name="trivial" id="chktrivial" value="1" %(checked)s onclick="toggle_trivial(this)">
<label for="chktrivial">%(label)s</label>

''' % {
                'checked': ('', 'checked')[form.get('trivial', ['0'])[0] == '1'],
                'label': _("Trivial change"),
                })

        request.write('''
&nbsp;
<input type="checkbox" name="rstrip" id="chkrstrip" value="1" %(checked)s>
<label for="chkrstrip">%(label)s</label>
''' % {
            'checked': ('', 'checked')[form.get('rstrip', ['0'])[0] == '1'],
            'label': _('Remove trailing whitespace from each line')
            })
        request.write("</p>")

        badwords_re = None
        if preview is not None:
            if 'button_spellcheck' in form or 'button_newwords' in form:
                badwords, badwords_re, msg = SpellCheck.checkSpelling(self, request, own_form=0)
                request.write("<p>%s</p>" % msg)
        request.write('</fieldset>')
        request.write("</form>")

        # QuickHelp originally by Georg Mischler <schorsch@lightingwiki.com>
        markup = self.pi['format'] or request.cfg.default_markup
        parser = wikiutil.searchAndImportPlugin(self.request.cfg, "parser", markup)
        quickhelp = getattr(parser, 'quickhelp', None)
        if quickhelp:
            request.write(request.formatter.div(1, id="editor-help"))
            request.write(_(quickhelp, wiki=True))
            request.write(request.formatter.div(0))

        if preview is not None:
            if staytop:
                content_id = 'previewbelow'
            else:
                content_id = 'preview'
            self.send_page(content_id=content_id, content_only=1, hilite_re=badwords_re)

        request.write(request.formatter.endContent())
        request.theme.send_footer(self.page_name)
        request.theme.send_closing_html()

    def sendCancel(self, newtext, rev):
        """ User clicked on Cancel button.
            If edit locking is active, delete the current lock file.

        @param newtext: the edited text (which has been cancelled)
        @param rev: not used!?
        """
        request = self.request
        _ = self._
        self._save_draft(newtext, rev) # shall we really save a draft on CANCEL?
        self.lock.release()

        backto = request.form.get('backto', [None])[0]
        if backto:
            pg = Page(request, backto)
            request.http_redirect(pg.url(request, relative=False))
        else:
            request.theme.add_msg(_('Edit was cancelled.'), "error")
            self.send_page()

    def copyPage(self, newpagename, comment=u''):
        """ Copy the current version of the page (keeping the backups, logs and attachments).

        @param comment: Comment given by user
        @rtype: unicode
        @return: success flag, error message
        """
        request = self.request
        _ = self._

        if not self.request.user.may.write(newpagename):
            return False, _('You are not allowed to copy this page!')
        if newpagename == self.page_name:
            return False, _("Copy failed because name and newname are the same.")
        if not newpagename:
            return False, _("You cannot copy to an empty item name.")

        old_item = self._backend.get_item(self.page_name)
        try:
            new_item = self._backend.create_item(newpagename)
            last_revno = 0
        except ItemAlreadyExistsError:
            # In this case, we just add all revisions of the old item to the
            # revisions of the new item. Note that the new item may already have
            # some revisions. Thus, we start at the new items last_revno + 1
            new_item = self._backend.get_item(self.page_name)
            last_rev = new_item.get_revision(-1)  # TODO May fail, but shouldn't
            last_revno = last_rev.revno + 1

        # Transfer all revisions with their data and metadata
        # Make sure the list begins with the lowest value, that is, 0.
        revs = old_item.list_revisions()
        for revno in revs:
            new_rev = new_item.create_revision(revno + last_revno)
            old_rev = old_item.get_revision(revno)

            shutil.copyfileobj(old_rev, new_rev, 8192)

            for key in old_rev:
                new_rev[key] = old_rev[key]

            new_item.commit()

        # transfer item metadata
        new_item.change_metadata()
        for key in old_item:
            new_item[key] = old_item[key]
        new_item.publish_metadata()

        newpage = PageEditor(request, newpagename)
        # Get old page text
        savetext = newpage.get_raw_body()

        if not comment:
            comment = u"## page was copied from %s" % self.page_name

        # Save page text with a comment about the old name and log entry
        savetext = u"## page was copied from %s\n%s" % (self.page_name, savetext)
        newpage.saveText(savetext, None, comment=comment, index=0, extra=self.page_name, action='SAVE', notify=False)

        if request.cfg.xapian_search:
            from MoinMoin.search.Xapian import Index
            index = Index(request)
            if index.exists():
                index.update_page(newpagename)

        event = PageCopiedEvent(request, newpage, self, comment)
        send_event(event)

        return True, None

    def renamePage(self, newpagename, comment=u''):
        """ Rename the current version of the page (making a backup before deletion
            and keeping the backups, logs and attachments).

        @param comment: Comment given by user
        @rtype: unicode
        @return: success flag, error message
        """
        request = self.request
        _ = self._
        old_name = self.page_name

        if not (request.user.may.delete(old_name)
                and request.user.may.write(newpagename)):
            msg = _('You are not allowed to rename this page!')
            raise self.AccessDenied, msg

        try:
            item = self._backend.get_item(old_name)
            item.rename(newpagename)
        except BackendError, err:
            return False, _(err.message)

        newpage = PageEditor(request, newpagename)
        savetext = newpage.get_raw_body()
        savetext = u"## page was renamed from %s\n%s" % (old_name, savetext)
        newpage.saveText(savetext, None, comment=comment, index=0, extra=old_name, action='SAVE/RENAME', notify=False)

        # delete pagelinks
        arena = newpage
        key = 'pagelinks'
        cache = caching.CacheEntry(request, arena, key, scope='item')
        cache.remove()

        # clean the cache
        for formatter_name in self.cfg.caching_formats:
            arena = newpage
            key = formatter_name
            cache = caching.CacheEntry(request, arena, key, scope='item')
            cache.remove()

        if request.cfg.xapian_search:
            from MoinMoin.search.Xapian import Index
            index = Index(request)
            if index.exists():
                index.remove_item(old_name, now=0)
                index.update_page(newpagename)

        event = PageRenamedEvent(request, newpage, self, comment)
        send_event(event)

        return True, None

    def revertPage(self, revision, comment=u''):
        """ Reverts page to the given revision

        @param revision: revision to revert to
        @type revision: int

        """
        _ = self.request.getText

        if not self.request.user.may.revert(self.page_name):
            # no real message necessary, cannot happen if
            # user doesn't try to exploit us
            raise self.RevertError('not allowed')
        elif revision is None:
            # see above
            raise self.RevertError('cannot revert to current rev')
        else:
            revstr = '%08d' % revision
            pg = Page(self.request, self.page_name, rev=revision)
            msg = self.saveText(pg.get_raw_body(), None, extra=revstr, action="SAVE/REVERT", notify=False, comment=comment)

            # Remove cache entry (if exists)
            pg = Page(self.request, self.page_name)
            key = self.request.form.get('key', ['text_html'])[0]
            caching.CacheEntry(self.request, pg, key, scope='item').remove()
            caching.CacheEntry(self.request, pg, "pagelinks", scope='item').remove()

            # Notify observers
            e = PageRevertedEvent(self.request, self.page_name, revision, revstr)
            send_event(e)

            return msg

    def deletePage(self, comment=""):
        """ Delete the current version of the page (making a backup before deletion
            and keeping the backups, logs and attachments).

        @param comment: Comment given by user
        @rtype: unicode
        @return: success flag, error message
        """
        request = self.request
        _ = self._
        success = True
        if not (request.user.may.write(self.page_name)
                and request.user.may.delete(self.page_name)):
            msg = _('You are not allowed to delete this page!')
            raise self.AccessDenied, msg

        try:
            msg = self.saveText(u"deleted\n", None, comment=comment or u'', deleted=True, notify=False)
            msg = msg.replace(
                _("Thank you for your changes. Your attention to detail is appreciated."),
                _('Page "%s" was successfully deleted!') % (wikiutil.escape(self.page_name), ))

            event = PageDeletedEvent(request, self, comment)
            send_event(event)
        except self.SaveError, message:
            # XXX do not only catch base class SaveError here, but
            # also the derived classes, so we can give better err msgs
            success = False
            msg = "SaveError has occured in PageEditor.deletePage. We need locking there."

        # delete pagelinks
        arena = self
        key = 'pagelinks'
        cache = caching.CacheEntry(request, arena, key, scope='item')
        cache.remove()

        # clean the cache
        for formatter_name in self.cfg.caching_formats:
            arena = self
            key = formatter_name
            cache = caching.CacheEntry(request, arena, key, scope='item')
            cache.remove()
        return success, msg

    def _get_local_timestamp(self):
        """ Returns the string that can be used by the TIME substitution.

        @return: str with a timestamp in it
        """

        now = time.time()
        # default: UTC
        zone = "Z"
        u = self.request.user

        # setup the timezone
        if u.valid and u.tz_offset:
            tz = u.tz_offset
            # round to minutes
            tz -= tz % 60
            minutes = tz / 60
            hours = minutes / 60
            minutes -= hours * 60

            # construct the offset
            zone = "%+0.2d%02d" % (hours, minutes)
            # correct the time by the offset we've found
            now += tz

        return time.strftime("%Y-%m-%dT%H:%M:%S", timefuncs.tmtuple(now)) + zone

    def _expand_variables(self, text):
        """ Expand @VARIABLE@ in `text`and return the expanded text.

        @param text: current text of wikipage
        @rtype: string
        @return: new text of wikipage, variables replaced
        """
        # TODO: Allow addition of variables via wikiconfig or a global wiki dict.
        request = self.request
        now = self._get_local_timestamp()
        u = request.user
        obfuscated_email_address = encodeSpamSafeEmail(u.email)
        signature = u.signature()
        variables = {
            'PAGE': self.page_name,
            'TIME': "<<DateTime(%s)>>" % now,
            'DATE': "<<Date(%s)>>" % now,
            'ME': u.name,
            'USERNAME': signature,
            'USER': "-- %s" % signature,
            'SIG': "-- %s <<DateTime(%s)>>" % (signature, now),
            'EMAIL': "<<MailTo(%s)>>" % (obfuscated_email_address)
        }

        if u.valid and u.name:
            if u.email:
                variables['MAILTO'] = "<<MailTo(%s)>>" % u.email
            # Users can define their own variables via
            # UserHomepage/MyDict, which override the default variables.
            userDictPage = u.name + "/MyDict"
            if request.dicts.has_dict(userDictPage):
                variables.update(request.dicts.dict(userDictPage))

        for name in variables:
            text = text.replace('@%s@' % name, variables[name])
        return text

    def normalizeText(self, text, **kw):
        """ Normalize text

        Make sure text uses '\n' line endings, and has a trailing
        newline. Strip whitespace on end of lines if needed.

        You should normalize any text you enter into a page, for
        example, when getting new text from the editor, or when setting
        new text manually.

        @param text: text to normalize (unicode)
        @keyword stripspaces: if 1, strip spaces from text
        @rtype: unicode
        @return: normalized text
        """
        if text:
            lines = text.splitlines()
            # Strip trailing spaces if needed
            if kw.get('stripspaces', 0):
                lines = [line.rstrip() for line in lines]
            # Add final newline if not present, better for diffs (does
            # not include former last line when just adding text to
            # bottom; idea by CliffordAdams)
            if not lines[-1] == u'':
                # '' will make newline after join
                lines.append(u'')

            text = u'\n'.join(lines)
        return text

    def _save_draft(self, text, rev, **kw):
        """ Save an editor backup to the drafts cache arena.

        @param text: draft text of the page
                     (if None, the draft gets removed from the cache)
        @param rev: the revision of the page this draft is based on
        @param kw: no keyword args used currently
        """
        request = self.request
        if not request.user.valid or not self.do_editor_backup:
            return None

        arena = 'drafts'
        key = request.user.id
        cache = caching.CacheEntry(request, arena, key, scope='wiki', use_pickle=True)
        if cache.exists():
            cache_data = cache.content()
        else:
            cache_data = {}
        pagename = self.page_name
        if text is None:
            try:
                del cache_data[pagename]
            except:
                pass
        else:
            timestamp = int(time.time())
            cache_data[pagename] = (timestamp, rev, text)
        cache.update(cache_data)

    def _load_draft(self):
        """ Get a draft from the drafts cache arena.

        @rtype: unicode
        @return: draft text or None
        """
        request = self.request
        if not request.user.valid:
            return None

        arena = 'drafts'
        key = request.user.id
        cache = caching.CacheEntry(request, arena, key, scope='wiki', use_pickle=True)
        pagename = self.page_name
        try:
            cache_data = cache.content()
            return cache_data.get(pagename)
        except caching.CacheError:
            return None

    def _write_file(self, text, old_revno=None, action='SAVE', comment=u'', extra=u'', deleted=False):
        """ Write the text to the page item (and make a backup of old page).

        @param text: text to save for this page
        @param deleted: if True, then don't write page content (used by deletePage)
        @rtype: int
        @return: mtime_usec of new page
        """
        _ = self._
        request = self.request
        was_deprecated = self.pi.get('deprecated', False)

        if old_revno is None:
            try:
                old_revno = max(self._item.list_revisions())
            except ValueError:
                old_revno = -1

        # remember conflict state
        self.setConflict(wikiutil.containsConflictMarker(text))

        if was_deprecated:
            newrev = self._item.get_revision(-1)
        else:
            try:
                newrev = self._item.create_revision(old_revno + 1)
            except RevisionAlreadyExistsError:
                raise PageEditor.EditConflict(_("Someone else saved this page while you were editing!"))

        if not deleted:
            metadata, data = wikiutil.split_body(text)
            newrev.write(data.encode(config.charset))

            for key, value in metadata.iteritems():
                newrev[key] = value
        else:
            newrev.write("")
            newrev[DELETED] = True

        if self.uid_override is not None:
            addr, userid = "", ""
            hostname = self.uid_override
        else:
            addr = request.remote_addr

            if hasattr(request, "user"):
                userid = request.user.valid and request.user.id or ''
            else:
                userid = ""

            hostname = wikiutil.get_hostname(request, addr)

        timestamp = time.time()
        newrev[EDIT_LOG_ACTION] = action
        newrev[EDIT_LOG_ADDR] = addr
        newrev[EDIT_LOG_HOSTNAME] = hostname
        newrev[EDIT_LOG_USERID] = userid
        newrev[EDIT_LOG_EXTRA] = extra
        newrev[EDIT_LOG_COMMENT] = wikiutil.clean_input(comment)
        newrev["mimetype"] = "text/x-unidentified-wiki-format"

        self._item.commit()
        self.reset()

        # add event log entry
        elog = eventlog.EventLog(request)
        elog.add(request, 'SAVEPAGE', {'pagename': self.page_name}, 1, time.time())

    def saveText(self, newtext, rev, **kw):
        """ Save new text for a page.

        @param newtext: text to save for this page
        @param rev: revision of the page
        @keyword trivial: trivial edit (default: 0)
        @keyword extra: extra info field (e.g. for SAVE/REVERT with revno)
        @keyword comment: comment field (when preview is true)
        @keyword action: action for editlog (default: SAVE)
        @keyword index: needs indexing, not already handled (default: 1)
        @keyword deleted: if True, then don't save page content (used by DeletePage, default: False)
        @keyword notify: if False (default: True), don't send a PageChangedEvent
        @rtype: unicode
        @return: error msg
        """
        request = self.request
        _ = self._
        self._save_draft(newtext, rev, **kw)
        action = kw.get('action', 'SAVE')
        deleted = kw.get('deleted', False)
        notify = kw.get('notify', True)

        #!!! need to check if we still retain the lock here
        #!!! rev check is not enough since internal operations use "0"

        # expand variables, unless it's a template or form page
        if not wikiutil.isTemplatePage(request, self.page_name):
            newtext = self._expand_variables(newtext)

        msg = ""
        if not request.user.may.save(self, newtext, rev, **kw):
            msg = _('You are not allowed to edit this page!')
            raise self.AccessDenied, msg
        elif not newtext:
            msg = _('You cannot save empty pages.')
            raise self.EmptyPage, msg
        elif newtext == self.get_raw_body():
            msg = _('You did not change the page content, not saved!')
            raise self.Unchanged, msg
        else:
            from MoinMoin.security import parseACL
            # Get current ACL and compare to new ACL from newtext. If
            # they are not the sames, the user must have admin
            # rights. This is a good place to update acl cache - instead
            # of wating for next request.
            acl = self.getACL()
            if (not request.user.may.admin(self.page_name) and
                parseACL(request, newtext).acl != acl.acl and
                action != "SAVE/REVERT"):
                msg = _("You can't change ACLs on this page since you have no admin rights on it!")
                raise self.NoAdmin, msg

        presave = PagePreSaveEvent(request, self, newtext)
        results = send_event(presave)

        for result in results:
            if isinstance(result, Abort):
                # XXX: this should return a list of messages to the sorrounding context
                # XXX: rather than dumbly concatenate them. Fix in the future.
                msg = msg + result.reason

        # save only if no error occurred (msg is empty) and no abort has been requested
        if not msg:
            # set success msg
            msg = _("Thank you for your changes. Your attention to detail is appreciated.")

            # determine action for edit log
            if action == 'SAVE' and not self.exists():
                action = 'SAVENEW'
            comment = kw.get('comment', u'')
            extra = kw.get('extra', u'')
            trivial = kw.get('trivial', 0)
            # write the page file
            self._write_file(newtext, rev, action, comment, extra, deleted=deleted)

            self._save_draft(None, None) # everything fine, kill the draft for this page
            if notify:
                # send notifications
                from MoinMoin import events

                if trivial:
                    e = events.TrivialPageChangedEvent(self.request, self, comment)
                else:
                    e = events.PageChangedEvent(self.request, self, comment)
                results = events.send_event(e)

                recipients = set()
                for result in results:
                    if isinstance(result, notification.Success):
                        recipients.update(result.recipients)

                        if recipients:
                            info = _("Notifications sent to:")
                            msg = msg + "<p>%s %s</p>" % (info, ", ".join(recipients))

            # Update page trail with the page we just saved.
            # This is needed for NewPage macro with backto because it does not
            # send the page we just saved.
            request.user.addTrail(self)

        # remove lock (forcibly if we were allowed to break it by the UI)
        # !!! this is a little fishy, since the lock owner might not notice
        # we broke his lock ==> but revision checking during preview will
        self.lock.release(force=not msg) # XXX does "not msg" make any sense?

        return msg


class PageLock:
    """ PageLock - Lock pages """
    # TODO: race conditions throughout, need to lock file during queries & update
    def __init__(self, pageobj):
        """
        """
        self.pageobj = pageobj
        self.page_name = pageobj.page_name
        request = pageobj.request
        self.request = request
        self._ = self.request.getText
        self.cfg = self.request.cfg

        # current time and user for later checks
        self.now = int(time.time())
        self.uid = request.user.valid and request.user.id or request.remote_addr

        # get details of the locking preference, i.e. warning or lock, and timeout
        self.locktype = None
        self.timeout = 10 * 60 # default timeout in minutes

        if self.cfg.edit_locking:
            lockinfo = self.cfg.edit_locking.split()
            if 1 <= len(lockinfo) <= 2:
                self.locktype = lockinfo[0].lower()
                if len(lockinfo) > 1:
                    try:
                        self.timeout = int(lockinfo[1]) * 60
                    except ValueError:
                        pass


    def acquire(self):
        """ Begin an edit lock depending on the mode chosen in the config.

        @rtype: tuple
        @return: tuple is returned containing 2 values:
              * a bool indicating successful acquiry
              * a string giving a reason for failure or an informational msg
        """
        if not self.locktype:
            # we are not using edit locking, so always succeed
            return 1, ''

        _ = self._
        #!!! race conditions, need to lock file during queries & update
        self._readLockFile()
        bumptime = self.request.user.getFormattedDateTime(self.now + self.timeout)
        timestamp = self.request.user.getFormattedDateTime(self.timestamp)
        owner = self.owner_html
        secs_valid = self.timestamp + self.timeout - self.now

        # do we own the lock, or is it stale?
        if self.owner is None or self.uid == self.owner or secs_valid < 0:
            # create or bump the lock
            self._writeLockFile()

            msg = []
            if self.owner is not None and -10800 < secs_valid < 0:
                mins_ago = secs_valid / -60
                msg.append(_(
                    "The lock of %(owner)s timed out %(mins_ago)d minute(s) ago,"
                    " and you were granted the lock for this page."
                    ) % {'owner': owner, 'mins_ago': mins_ago})

            if self.locktype == 'lock':
                msg.append(_(
                    "Other users will be ''blocked'' from editing this page until %(bumptime)s.",
                    wiki=True) % {'bumptime': bumptime})
            else:
                msg.append(_(
                    "Other users will be ''warned'' until %(bumptime)s that you are editing this page.",
                    wiki=True) % {'bumptime': bumptime})
            msg.append(_(
                "Use the Preview button to extend the locking period."
                ))
            result = 1, '\n'.join(msg)
        else:
            mins_valid = (secs_valid+59) / 60
            if self.locktype == 'lock':
                # lout out user
                result = 0, _(
                    "This page is currently ''locked'' for editing by %(owner)s until %(timestamp)s,"
                    " i.e. for %(mins_valid)d minute(s).",
                    wiki=True) % {'owner': owner, 'timestamp': timestamp, 'mins_valid': mins_valid}
            else:
                # warn user about existing lock

                result = 1, _(
"""This page was opened for editing or last previewed at %(timestamp)s by %(owner)s.<<BR>>
'''You should ''refrain from editing'' this page for at least another %(mins_valid)d minute(s),
to avoid editing conflicts.'''<<BR>>
To leave the editor, press the Cancel button.""", wiki=True) % {
                    'timestamp': timestamp, 'owner': owner, 'mins_valid': mins_valid}

        return result


    def release(self, force=0):
        """ Release lock, if we own it.

        @param force: if 1, unconditionally release the lock.
        """
        if self.locktype:
            # check that we own the lock in order to delete it
            #!!! race conditions, need to lock file during queries & update
            self._readLockFile()
            if force or self.uid == self.owner:
                self._deleteLockFile()

    def _readLockFile(self):
        _ = self._
        self.owner = None
        self.owner_html = wikiutil.escape(_("<unknown>"))
        self.timestamp = 0
        if self.locktype:
            (lock, self.timestamp, addr, hostname, userid) = wikiutil.get_edit_lock(self.pageobj._item)
            if lock:
                self.owner = userid or addr
                self.owner_html = user.get_printable_editor(self.request, userid, addr, hostname)


    def _writeLockFile(self):
        """ Write new lock file. """
        self.pageobj._item.edit_lock = True

    def _deleteLockFile(self):
        """ Delete the lock file unconditionally. """
        self.pageobj._item.edit_lock = False
