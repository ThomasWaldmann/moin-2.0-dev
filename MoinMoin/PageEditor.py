# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PageEditor class

    PageEditor is used for r/w access to a wiki page (edit, rename, delete operations).

    DEPRECATED - move stuff you need to MoinMoin.items!
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
from MoinMoin.storage.error import ItemAlreadyExistsError, RevisionAlreadyExistsError, NoSuchRevisionError
from MoinMoin.Page import DELETED, EDIT_LOG_ADDR, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
                          EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_ACTION

import MoinMoin.events.notification as notification

# used for merging
conflict_markers = ("\n---- /!\\ '''Edit conflict - other version:''' ----\n",
                    "\n---- /!\\ '''Edit conflict - your version:''' ----\n",
                    "\n---- /!\\ '''End of edit conflict''' ----\n")


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
            try:
                last_rev = new_item.get_revision(-1)
                last_revno = last_rev.revno + 1
            except NoSuchRevisionError:
                last_revno = 0

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
            key = self.request.form.get('key', 'text_html') # XXX see cleanup code in deletePage
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
            self.lock.release()
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
