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
from MoinMoin.mail.sendmail import encodeSpamSafeEmail
from MoinMoin.support.python_compatibility import set
from MoinMoin.util import timefuncs, web
from MoinMoin.storage.error import BackendError
from MoinMoin.events import PageDeletedEvent, PageRenamedEvent, PageCopiedEvent, PageRevertedEvent
from MoinMoin.events import PagePreSaveEvent, Abort, send_event
from MoinMoin.wikiutil import EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID
from MoinMoin.storage.error import ItemAlreadyExistsError, RevisionAlreadyExistsError, NoSuchRevisionError
from MoinMoin.items import MIMETYPE, \
                           EDIT_LOG_ADDR, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
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
            'TIMESTAMP': now,
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
            if userDictPage in request.dicts:
                variables.update(request.dicts[userDictPage])

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

    def _write_file(self, text, old_revno=None, action='SAVE', comment=u'', extra=u''):
        """ Write the text to the page item (and make a backup of old page).

        @param text: text to save for this page
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

        metadata, data = wikiutil.split_body(text)
        newrev.write(data.encode(config.charset))

        for key, value in metadata.iteritems():
            newrev[key] = value

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
        newrev[MIMETYPE] = "text/x-unidentified-wiki-format"

        self._item.commit()
        self.reset()

    def saveText(self, newtext, rev, **kw):
        """ Save new text for a page.

        @param newtext: text to save for this page
        @param rev: revision of the page
        @keyword trivial: trivial edit (default: 0)
        @keyword extra: extra info field (e.g. for SAVE/REVERT with revno)
        @keyword comment: comment field (when preview is true)
        @keyword action: action for editlog (default: SAVE)
        @keyword index: needs indexing, not already handled (default: 1)
        @keyword notify: if False (default: True), don't send a PageChangedEvent
        @rtype: unicode
        @return: error msg
        """
        request = self.request
        _ = self._
        self._save_draft(newtext, rev, **kw)
        action = kw.get('action', 'SAVE')
        notify = kw.get('notify', True)

        #!!! need to check if we still retain the lock here
        #!!! rev check is not enough since internal operations use "0"

        # expand variables, unless it's a template or form page
        if not wikiutil.isTemplatePage(request, self.page_name):
            newtext = self._expand_variables(newtext)

        msg = ""
        if not request.user.may.write(self.page_name):
            msg = _('You are not allowed to edit this page!')
            raise self.AccessDenied, msg
        elif not newtext:
            msg = _('You cannot save empty pages.')
            raise self.EmptyPage, msg
        elif newtext == self.get_raw_body():
            msg = _('You did not change the page content, not saved!')
            self.lock.release()
            raise self.Unchanged, msg

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

            comment = kw.get('comment', u'')
            extra = kw.get('extra', u'')
            trivial = kw.get('trivial', 0)
            # write the page file
            self._write_file(newtext, rev, action, comment, extra)
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
