# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - misc. mimetype items

    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2009 MoinMoin:ReimarBauer,
                2009 MoinMoin:ChristopherDenter
                2009 MoinMoin:BastianBlank
    @license: GNU GPL, see COPYING for details.
"""

import os, re, tarfile, time, datetime, shutil
from StringIO import StringIO

from MoinMoin import caching, log
logging = log.getLogger(__name__)

from werkzeug import http_date, quote_etag, url_quote

from MoinMoin import wikiutil, config, user
from MoinMoin.util import timefuncs
from MoinMoin.support.python_compatibility import hash_new
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError, AccessDeniedError, \
                                   StorageError

from MoinMoin.items.sendcache import SendCache

NAME = "name"
NAME_OLD = "name_old"

# some metadata key constants:
ACL = "acl"

# This says: I am a system page
IS_SYSPAGE = "is_syspage"
# This says: original syspage as contained in release: <release>
SYSPAGE_VERSION = "syspage_version"

MIMETYPE = "mimetype"
SIZE = "size"

EDIT_LOG_ACTION = "edit_log_action"
EDIT_LOG_ADDR = "edit_log_addr"
EDIT_LOG_HOSTNAME = "edit_log_hostname"
EDIT_LOG_USERID = "edit_log_userid"
EDIT_LOG_EXTRA = "edit_log_extra"
EDIT_LOG_COMMENT = "edit_log_comment"

EDIT_LOG = [EDIT_LOG_ACTION, EDIT_LOG_ADDR, EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT]

# dummy getText function until we have a real one:
_ = lambda x: x

class Item(object):

    @classmethod
    def create(cls, request, name=u'', mimetype='application/x-unknown', rev_no=None,
               formatter=None, item=None):
        class DummyRev(dict):
            def __init__(self, mimetype):
                self[MIMETYPE] = mimetype
                self.item = None
            def read(self):
                return ''

        if rev_no is None:
            rev_no = -1

        try:
            if item is None:
                item = request.storage.get_item(name)
            else:
                name = item.name
        except NoSuchItemError:
            logging.debug("No such item: %r" % name)
            rev = DummyRev(mimetype)
            logging.debug("Item %r, created dummy revision with mimetype %r" % (name, mimetype))
        else:
            logging.debug("Got item: %r" % name)
            try:
                rev = item.get_revision(rev_no)
            except NoSuchRevisionError:
                try:
                    rev = item.get_revision(-1) # fall back to current revision
                    # XXX add some message about invalid revision
                except NoSuchRevisionError:
                    logging.debug("Item %r has no revisions." % name)
                    rev = DummyRev(mimetype)
                    logging.debug("Item %r, created dummy revision with mimetype %r" % (name, mimetype))
            logging.debug("Got item %r, revision: %r" % (name, rev_no))
        mimetype = rev.get(MIMETYPE) or 'application/x-unknown' # XXX why do we need ... or ..?
        logging.debug("Item %r, got mimetype %r from revision meta" % (name, mimetype))
        logging.debug("Item %r, rev meta dict: %r" % (name, dict(rev)))

        def _find_item_class(mimetype, BaseClass, best_match_len=-1):
            #logging.debug("_find_item_class(%r,%r,%r)" % (mimetype, BaseClass, best_match_len))
            Class = None
            for ItemClass in BaseClass.__subclasses__():
                for supported_mimetype in ItemClass.supported_mimetypes:
                    if mimetype.startswith(supported_mimetype):
                        match_len = len(supported_mimetype)
                        if match_len > best_match_len:
                            best_match_len = match_len
                            Class = ItemClass
                            #logging.debug("_find_item_class: new best match: %r by %r)" % (supported_mimetype, ItemClass))
                best_match_len, better_Class = _find_item_class(mimetype, ItemClass, best_match_len)
                if better_Class:
                    Class = better_Class
            return best_match_len, Class

        ItemClass = _find_item_class(mimetype, cls)[1]
        logging.debug("ItemClass %r handles %r" % (ItemClass, mimetype))
        return ItemClass(request, name=name, rev=rev, mimetype=mimetype, formatter=formatter)

    def __init__(self, request, name, rev=None, mimetype=None, formatter=None):
        self.request = request
        self.env = request.theme.env
        self.name = name
        self.rev = rev
        self.mimetype = mimetype
        if formatter is None:
            from MoinMoin.formatter.text_html import Formatter
            formatter = Formatter(request)
        self.formatter = formatter

    def get_meta(self):
        return self.rev or {}
    meta = property(fget=get_meta)

    def url(self, _absolute=False, **kw):
        """ return URL for this item, optionally as absolute URL """
        href = _absolute and self.request.abs_href or self.request.href
        return href(self.name, **kw)

    def rev_url(self, _absolute=False, **kw):
        """ return URL for this item and this revision, optionally as absolute URL """
        return self.url(rev=self.rev.revno, _absolute=_absolute, **kw)

    transclude_acceptable_attrs = []

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self.formatter.text('(Item %s (%s): transclusion not implemented)' % (self.name, self.mimetype))

    def meta_text_to_dict(self, text):
        """ convert meta data from a text fragment to a dict """
        meta = {}
        for line in text.splitlines():
            k, v = line.split(':', 1)
            k, v = k.strip(), v.strip()
            meta[k] = v
        return meta

    def meta_dict_to_text(self, meta):
        text = u'\n'.join([u"%s: %s" % (k, v) for k, v in meta.items()])
        return text

    def get_data(self):
        return '' # TODO create a better method for binary stuff
    data = property(fget=get_data)

    def do_modify(self, template_name):
        # XXX think about and add item template support
        template = self.env.get_template('modify_binary.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  rows_meta=3, cols=80,
                                  revno=0,
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  help=self.modify_help,
                                 )
        return content

    def _action_query(self, action, label=None, target=None, revno=None):
        template = self.env.get_template('action_query.html')
        content = template.render(gettext=self.request.getText,
                                  action=action,
                                  label=label or action,
                                  item_name=self.name,
                                  revno=revno,
                                  target=target,
                                 )
        return content

    def do_rename(self):
        return self._action_query('rename', target=self.name)

    def do_copy(self):
        return self._action_query('copy', target=self.name)

    def do_delete(self):
        return self._action_query('delete')

    def do_destroy(self):
        return self._action_query('destroy', revno=self.rev.revno)

    def do_revert(self):
        return self._action_query('revert', revno=self.rev.revno)

    def _write_stream(self, content, new_rev, bufsize=8192):
        hash_name = self.request.cfg.hash_algorithm
        hash = hash_new(hash_name)
        if hasattr(content, "read"):
            while True:
                buf = content.read(bufsize)
                hash.update(buf)
                if not buf:
                    break
                new_rev.write(buf)
        elif isinstance(content, str):
            new_rev.write(content)
            hash.update(content)
        else:
            raise StorageError("unsupported content object: %r" % content)
        return hash_name, unicode(hash.hexdigest())

    def copy(self, name, comment=u''):
        """
        copy this item to item <name>
        """
        old_item = self.rev.item
        backend = self.request.storage
        backend.copy_item(old_item, name=name)
        current_rev = old_item.get_revision(-1)
        # we just create a new revision with almost same meta/data to show up on RC
        self._save(current_rev, current_rev, name=name, action='SAVE/COPY', comment=comment)

    def _rename(self, name, comment, action):
        self.rev.item.rename(name)
        self._save(self.meta, self.data, name=name, action=action, comment=comment)

    def rename(self, name, comment=u''):
        """
        rename this item to item <name>
        """
        return self._rename(name, comment, action='SAVE/RENAME')

    def delete(self, comment=u''):
        """
        delete this item by moving it to the trashbin
        """
        trash_prefix = u'Trash/' # XXX move to config
        now = time.strftime(self.request.cfg.datetime_fmt, timefuncs.tmtuple(time.time()))
        # make trash name unique by including timestamp:
        trashname = u'%s%s (%s UTC)' % (trash_prefix, self.name, now)
        return self._rename(trashname, comment, action='SAVE/DELETE')

    def revert(self):
        # called from revert UI/POST
        comment = self.request.form.get('comment')
        self._save(self.meta, self.data, action='SAVE/REVERT', comment=comment)

    def destroy(self):
        # called from destroy UI/POST
        comment = self.request.form.get('comment')
        if comment == '0-0-0-Destruct-0': # TODO: improve this
            # destroy complete item with all revisions, metadata, etc.
            self.rev.item.destroy()
        else:
            # just destroy this revision
            self.rev.destroy()

    def modify(self):
        # called from modify UI/POST
        request = self.request
        data_file = request.files.get('data_file')
        mimetype = request.values.get('mimetype', 'text/plain')
        if data_file and data_file.filename:
            # user selected a file to upload
            data = data_file.stream
            mimetype = wikiutil.MimeType(filename=data_file.filename).mime_type()
        else:
            # take text from textarea
            data = request.form.get('data_text', '')
            if data:
                data = self.data_form_to_internal(data)
                data = self.data_internal_to_storage(data)
                mimetype = 'text/plain'
            else:
                data = '' # could've been u'' also!
                mimetype = None
        meta_text = request.form.get('meta_text', '')
        meta = self.meta_text_to_dict(meta_text)
        comment = self.request.form.get('comment')
        self._save(meta, data, mimetype=mimetype, comment=comment)

    def _save(self, meta, data, name=None, action=u'SAVE', mimetype=None, comment=u''):
        request = self.request
        if name is None:
            name = self.name
        backend = request.storage
        try:
            storage_item = backend.get_item(name)
        except NoSuchItemError:
            storage_item = backend.create_item(name)
        try:
            currentrev = storage_item.get_revision(-1)
            rev_no = currentrev.revno
            if mimetype is None:
                # if we didn't get mimetype info, thus reusing the one from current rev:
                mimetype = currentrev.get(MIMETYPE)
        except NoSuchRevisionError:
            rev_no = -1
        newrev = storage_item.create_revision(rev_no + 1)
        for k, v in meta.iteritems():
            # TODO Put metadata into newrev here for now. There should be a safer way
            #      of input for this.

            # Skip this metadata key. It should not be copied when editing an item.
            if not k == SYSPAGE_VERSION:
                newrev[k] = v

        # we store the previous (if different) and current item name into revision metadata
        # this is useful for rename history and backends that use item uids internally
        oldname = meta.get(NAME)
        if oldname and oldname != name:
            newrev[NAME_OLD] = oldname
        newrev[NAME] = name

        hash_name, hash_hexdigest = self._write_stream(data, newrev)
        newrev[hash_name] = hash_hexdigest
        timestamp = time.time()
        # XXX if meta is from old revision, and user did not give a non-empty
        # XXX comment, re-using the old rev's comment is wrong behaviour:
        comment = unicode(comment or meta.get(EDIT_LOG_COMMENT, ''))
        if comment:
            newrev[EDIT_LOG_COMMENT] = comment
        # allow override by form- / qs-given mimetype:
        mimetype = request.values.get('mimetype', mimetype)
        # allow override by give metadata:
        assert mimetype is not None
        newrev[MIMETYPE] = unicode(meta.get(MIMETYPE, mimetype))
        newrev[EDIT_LOG_ACTION] = unicode(action)
        newrev[EDIT_LOG_ADDR] = unicode(request.remote_addr)
        newrev[EDIT_LOG_HOSTNAME] = unicode(wikiutil.get_hostname(request, request.remote_addr))
        if request.user.valid:
            newrev[EDIT_LOG_USERID] = unicode(request.user.id)
        storage_item.commit()
        #event = FileAttachedEvent(request, pagename, target, new_rev.size)
        #send_event(event)

    def search_item(self, term=None):
        """ search items matching the term or,
            if term is None, return all items

            TODO: rename this method and backend method to search_items
        """
        if term:
            backend_items = self.request.storage.search_item(term)
        else:
            # special case: we just want all items
            backend_items = self.request.storage.iteritems()
        for item in backend_items:
            yield Item.create(self.request, item=item)

    list_items = search_item  # just for cosmetics

    def count_items(self, term=None):
        """
        Return item count for matching items. See search_item() for details.
        """
        count = 0
        # we intentionally use a loop to avoid creating a list with all item objects:
        for item in self.list_items(term):
            count += 1
        return count

    def get_index(self):
        """ create an index of sub items of this item """
        import re
        from MoinMoin.search.term import NameRE

        if self.name:
            prefix = self.name + u'/'
        else:
            # trick: an item of empty name can be considered as "virtual root item",
            # that has all wiki items as sub items
            prefix = u''
        sub_item_re = u"^%s.*" % re.escape(prefix)
        regex = re.compile(sub_item_re, re.UNICODE)

        item_iterator = self.search_item(NameRE(regex))

        # We only want the sub-item part of the item names, not the whole item objects.
        prefix_len = len(prefix)
        items = [(item.name, item.name[prefix_len:], item.meta.get(MIMETYPE))
                 for item in item_iterator]
        return sorted(items)

    def flat_index(self):
        index = self.get_index()
        index = [(fullname, relname, mimetype)
                 for fullname, relname, mimetype in index
                 if u'/' not in relname]
        return index

    def do_index(self):
        template = self.env.get_template('index.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  index=self.flat_index(),
                                 )
        return content


class NonExistent(Item):
    supported_mimetypes = ['application/x-unknown']
    mimetype_groups = [
        ('page markup text items', [
            ('text/x.moin.wiki', 'Wiki (MoinMoin)'),
            ('text/x.moin.creole', 'Wiki (Creole)'),
            ('text/html', 'unsafe html'),
            ('text/x-safe-html', 'safe html'),
        ]),
        ('highlighted text items', [
            ('text/x-diff', 'diff/patch'),
            ('text/x-python', 'python code'),
        ]),
        ('other text items', [
            ('text/plain', 'plain text'),
            ('text/csv', 'csv'),
            ('text/x-irclog', 'IRC log'),
        ]),
        ('image items', [
            ('image/jpeg', 'JPEG'),
            ('image/png', 'PNG'),
            ('image/svg+xml', 'SVG'),
        ]),
        ('audio items', [
            ('audio/midi', 'MIDI'),
            ('audio/mpeg', 'MP3'),
            ('audio/ogg', 'OGG'),
            ('audio/x-aiff', 'AIF'),
            ('audio/x-ms-wma', 'WMA'),
            ('audio/x-pn-realaudio', 'RA'),
            ('audio/x-wav', 'WAV'),
        ]),
        ('video items', [
            ('video/mpg', 'MPG'),
            ('video/fli', 'FLI'),
            ('video/mp4', 'MP4'),
            ('video/quicktime', 'QuickTime'),
            ('video/ogg', 'OGG'),
            ('video/x-flv', 'FLV'),
            ('video/x-ms-asf', 'ASF'),
            ('video/x-ms-wm', 'WM'),
            ('video/x-ms-wmv', 'WMV'),
            ('video/x-msvideo', 'AVI'),
        ]),
        ('drawing items', [
            ('application/x-twikidraw', 'TDRAW'),
            ('application/x-anywikidraw', 'ADRAW'),
        ]),

        ('other items', [
            ('application/pdf', 'PDF'),
            ('application/x-shockwave-flash', 'SWF'),
            ('application/zip', 'ZIP'),
            ('application/x-tar', 'TAR'),
            ('application/x-gtar', 'TGZ'),
            ('application/octet-stream', 'binary file'),
        ]),
    ]

    def do_show(self):
        self.request.status_code = 404
        template = self.env.get_template('show_type_selection.html')
        content = []
        content.append(template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  mimetype_groups=self.mimetype_groups, ))

        template = self.env.get_template('show_package_install.html')
        content.append(template.render(gettext=self.request.getText, ))
        return '<hr>'.join(content)

    def do_get(self):
        self.request.status_code = 404

    def do_highlight(self):
        self.request.status_code = 404

    transclude_acceptable_attrs = []
    def transclude(self, desc, tag_attrs=None, query_args=None):
        return (self.formatter.url(1, self.url(), css='nonexistent', title='click to create item') +
                self.formatter.text(self.name) + # maybe use some "broken image" icon instead?
                self.formatter.url(0))


class Binary(Item):
    """ An arbitrary binary item, fallback class for every item mimetype. """
    supported_mimetypes = [''] # fallback, because every mimetype starts with ''

    modify_help = """\
There is no help, you're doomed!
"""
    # XXX reads item rev data into memory!
    def get_data(self):
        if self.rev is not None:
            return self.rev.read()
        else:
            return ''
    data = property(fget=get_data)

    def _revlog(self, item, rev_nos):
        log = []
        for rev_no in reversed(rev_nos):
            r = item.get_revision(rev_no)
            log.append(dict(
                name=r[NAME],
                rev_no=rev_no,
                size=r.size,
                mtime=self.request.user.getFormattedDateTime(float(r.timestamp)),
                editor=user.get_printable_editor(self.request,
                       r.get(EDIT_LOG_USERID), r.get(EDIT_LOG_ADDR), r.get(EDIT_LOG_HOSTNAME)) or _("N/A"),
                comment=r.get(EDIT_LOG_COMMENT, ''),
                mimetype=r.get(MIMETYPE, ''),
            ))
        return log

    transclude_acceptable_attrs = []
    def transclude(self, desc, tag_attrs=None, query_args=None):
        """ we can't transclude (render) this, thus we just link to the item """
        if tag_attrs is None:
            tag_attrs = {}
        if query_args is None:
            query_args = {}
        url = self.rev_url(**query_args)
        return (self.formatter.url(1, url, **tag_attrs) +
                self.formatter.text(desc) +
                self.formatter.url(0))

    def _render_meta(self):
        return "<pre>%s</pre>" % self.meta_dict_to_text(self.meta)

    def _render_data(self):
        return '' # XXX we can't render the data, maybe show some "data icon" as a placeholder?

    def get_templates(self, mimetype=None):
        """ create a list of templates (for some specific mimetype) """
        from MoinMoin.search.term import NameRE, AND, LastRevisionMetaDataMatch
        regex = self.request.cfg.cache.page_template_regexact
        term = NameRE(regex)
        if mimetype:
            term = AND(term, LastRevisionMetaDataMatch(MIMETYPE, mimetype))
        item_iterator = self.search_item(term)
        items = [item.name for item in item_iterator]
        return sorted(items)

    def do_highlight(self):
        return '' # XXX we can't highlight the data, maybe show some "data icon" as a placeholder?

    def do_show(self):
        item = self.rev.item
        if item is None:
            # it is the dummy item -> this is a new and empty item
            show_templates = True
            rev_nos = log = []
        else:
            show_templates = False
            rev_nos = item.list_revisions()
            log = self._revlog(item, rev_nos)
        if show_templates:
            item_templates = self.get_templates(self.mimetype)
            html_template = 'show_template_selection.html'
            meta_rendered = data_rendered = ''
            index = []
        else:
            item_templates = []
            html_template = 'show.html'
            data_rendered=self._render_data()
            meta_rendered=self._render_meta()
            index = self.flat_index()

        template = self.env.get_template(html_template)
        content = template.render(gettext=self.request.getText,
                                  rev=self.rev,
                                  log=log,
                                  mimetype=self.mimetype,
                                  templates=item_templates,
                                  first_rev_no=rev_nos and rev_nos[0],
                                  last_rev_no=rev_nos and rev_nos[-1],
                                  data_rendered=data_rendered,
                                  meta_rendered=meta_rendered,
                                  index=index,
                                 )
        return content

    def _render_data_diff(self, oldrev, newrev):
        hash_name = self.request.cfg.hash_algorithm
        if oldrev[hash_name] == newrev[hash_name]:
            return "The items have the same data hash code (that means they very likely have the same data)."
        else:
            return "The items have different data."

    def do_diff(self, oldrev, newrev):
        item = self.rev.item
        rev_nos = item.list_revisions()
        log = self._revlog(item, rev_nos)

        template = self.env.get_template('diff.html')
        content = template.render(gettext=self.request.getText,
                                  rev=self.rev,
                                  log=log,
                                  first_rev_no=rev_nos[0],
                                  last_rev_no=rev_nos[-1],
                                  index=self.flat_index(),
                                  oldrev=oldrev,
                                  newrev=newrev,
                                  data_diff_rendered=self._render_data_diff(oldrev, newrev),
                                 )
        return content

    def do_get(self):
        request = self.request
        hash = self.rev.get(request.cfg.hash_algorithm)
        if_none_match = request.if_none_match
        if if_none_match and hash in if_none_match:
            request.status_code = 304
        else:
            self._do_get_modified(hash)

    def _do_get_modified(self, hash):
        request = self.request
        from_cache = request.values.get('from_cache')
        from_tar = request.values.get('from_tar')
        self._do_get(hash, from_cache, from_tar)

    def _do_get(self, hash, from_cache=None, from_tar=None):
        request = self.request
        if from_cache:
            content_disposition = None
            sendcache = SendCache(request, from_cache)
            headers = sendcache._get_headers()
            for key, value in headers:
                lkey = key.lower()
                if lkey == 'content-type':
                    content_type = value
                elif lkey == 'content-length':
                    content_length = value
                elif lkey == 'content-disposition':
                    content_disposition = value
                else:
                    request.headers.add(key, value)
            file_to_send = sendcache._get_datafile()
        elif from_tar: # content = file contained within a tar item revision
            filename = wikiutil.taintfilename(from_tar)
            mt = wikiutil.MimeType(filename=filename)
            content_disposition = mt.content_disposition(request.cfg)
            content_type = mt.content_type()
            content_length = None
            file_to_send = self.get_member(filename)
        else: # content = item revision
            rev = self.rev
            try:
                mimestr = rev[MIMETYPE]
            except KeyError:
                mimestr = mimetypes.guess_type(rev.item.name)[0]
            mt = wikiutil.MimeType(mimestr=mimestr)
            content_disposition = mt.content_disposition(request.cfg)
            content_type = mt.content_type()
            content_length = rev.size
            file_to_send = rev

        self._send(content_type, content_length, hash, file_to_send,
                   content_disposition=content_disposition)

    def _send(self, content_type, content_length, hash, file_to_send,
              filename=None, content_disposition=None):
        request = self.request
        if hash:
            # if item has no hash metadata, hash is None
            request.headers.add('Cache-Control', 'public')
            request.headers.add('Etag', quote_etag(hash))
        if content_disposition is not None:
            request.headers.add('Content-Disposition', content_disposition)

        request.status_code = 200
        request.content_type = content_type
        request.content_length = content_length
        request.send_file(file_to_send)



class RenderableBinary(Binary):
    """ This is a base class for some binary stuff that renders with a object tag. """
    supported_mimetypes = []

    width = "100%"
    height = "100%"
    transclude_params = []
    transclude_acceptable_attrs = ['class', 'title', 'width', 'height', # no style because of JS
                                   'type', 'standby', ] # we maybe need a hack for <PARAM> here
    def transclude(self, desc, tag_attrs=None, query_args=None, params=None):
        if tag_attrs is None:
            tag_attrs = {}
        if 'type' not in tag_attrs:
            tag_attrs['type'] = self.mimetype
        if self.width and 'width' not in tag_attrs:
            tag_attrs['width'] = self.width
        if self.height and 'height' not in tag_attrs:
            tag_attrs['height'] = self.height
        if query_args is None:
            query_args = {}
        if 'do' not in query_args:
            query_args['do'] = 'get'
        if params is None:
            params = self.transclude_params
        url = self.rev_url(**query_args)
        return (self.formatter.transclusion(1, data=url, **tag_attrs) +
                ''.join([self.formatter.transclusion_param(**p) for p in params]) +
                self.formatter.text(desc) +
                self.formatter.transclusion(0))

    def _render_data(self):
        return self.transclude('{{%s [%s]}}' % (self.name, self.mimetype))


class PlayableBinary(RenderableBinary):
    """ This is a base class for some binary stuff that plays with a object tag. """
    transclude_params = [
        dict(name='stop', value='1', valuetype='data'),
        dict(name='play', value='0', valuetype='data'),
        dict(name='autoplay', value='0', valuetype='data'),
    ]


class Application(Binary):
    supported_mimetypes = []


class ApplicationZip(Application):
    supported_mimetypes = ['application/zip']

    def _render_data(self):
        import zipfile
        try:
            content = []
            fmt = u"%12s  %-19s  %-60s"
            headline = fmt % (_("Size"), _("Modified"), _("File Name"))
            content.append(headline)
            content.append(u"-" * len(headline))
            zf = zipfile.ZipFile(self.rev, mode='r')
            for zinfo in zf.filelist:
                content.append(wikiutil.escape(fmt % (
                    str(zinfo.file_size),
                    u"%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time,
                    zinfo.filename,
                )))
        except (RuntimeError, zipfile.BadZipfile), err:
            # RuntimeError is raised by zipfile stdlib module in case of
            # problems (like inconsistent slash and backslash usage in the
            # archive or a defective zip file).
            logging.exception("An exception within zip file handling occurred:")
            content = [str(err)]
        return u"<pre>%s</pre>" % "\n".join(content)

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self._render_data()


class TarMixin(object):
    """
    TarMixin offers additional functionality for tar-like items to list and
    access member files and to create new revisions by multiple posts.
    """
    # Note: from_tar query string arg needs to be last because twikidraw looks
    # for "file extension" at the end - therefore we need special url methods.
    def rev_url(self, _absolute=False, member=None, **kw):
        url = super(TarMixin, self).rev_url(_absolute=_absolute, **kw)
        if member is not None:
            url += '&from_tar=%s' % url_quote(member)
        return url

    def url(self, _absolute=False, member=None, **kw):
        url = super(TarMixin, self).url(_absolute=_absolute, **kw)
        if member is not None:
            url += '&from_tar=%s' % url_quote(member)
            # note: from_tar needs to be last in qs because twikidraw looks for "file extension" at the end
        return url

    def list_members(self):
        """
        list tar file contents (member file names)
        """
        self.rev.seek(0)
        tf = tarfile.open(fileobj=self.rev, mode='r')
        return tf.getnames()

    def get_member(self, name):
        """
        return a file-like object with the member file data

        @param name: name of the data in the container file
        """
        self.rev.seek(0)
        tf = tarfile.open(fileobj=self.rev, mode='r')
        return tf.extractfile(name)

    def put_member(self, name, content, content_length, expected_members):
        """
        puts a new member file into a temporary tar container.
        If all expected members have been put, it saves the tar container
        to a new item revision.

        @param name: name of the data in the container file
        @param content: the data to store into the tar file (str or file-like)
        @param content_length: byte-length of content (for str, None can be given)
        @param expected_members: set of expected member file names
        """
        if not name in expected_members:
            raise StorageError("tried to add unexpected member %r to container item %r" % (name, self.name))
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        cache = caching.CacheEntry(self.request, "TarContainer", self.name, 'wiki')
        tmp_fname = cache._fname
        tf = tarfile.TarFile(tmp_fname, mode='a')
        ti = tarfile.TarInfo(name)
        if isinstance(content, str):
            if content_length is None:
                content_length = len(content)
            content = StringIO(content) # we need a file obj
        elif not hasattr(content, 'read'):
            logging.error("unsupported content object: %r" % content)
            raise StorageError("unsupported content object: %r" % content)
        assert content_length >= 0  # we don't want -1 interpreted as 4G-1
        ti.size = content_length
        tf.addfile(ti, content)
        tf_members = set(tf.getnames())
        tf.close()
        if tf_members - expected_members:
            msg = "found unexpected members in container item %r" % (self.name, )
            logging.error(msg)
            cache.remove()
            raise StorageError(msg)

        if tf_members == expected_members:
            # everything we expected has been added to the tar file, save the container as revision
            meta = {"mimetype": self.mimetype}
            cache.open(mode='rb')
            self._save(meta, cache, name=self.name, action='SAVE', mimetype=self.mimetype, comment='')
            cache.close()
            cache.remove()


class ApplicationXTar(TarMixin, Application):
    supported_mimetypes = ['application/x-tar', 'application/x-gtar']

    def _render_data(self):
        import tarfile
        try:
            content = []
            fmt = u"%12s  %-19s  %-60s"
            headline = fmt % (_("Size"), _("Modified"), _("File Name"))
            content.append(headline)
            content.append(u"-" * len(headline))
            tf = tarfile.open(fileobj=self.rev, mode='r')
            for tinfo in tf.getmembers():
                content.append(wikiutil.escape(fmt % (
                    str(tinfo.size),
                    time.strftime("%Y-%02m-%02d %02H:%02M:%02S", time.gmtime(tinfo.mtime)),
                    tinfo.name,
                )))
        except tarfile.TarError, err:
            logging.exception("An exception within tar file handling occurred:")
            content = [str(err)]
        return u"<pre>%s</pre>" % "\n".join(content)

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self._render_data()


class RenderableApplication(RenderableBinary):
    supported_mimetypes = []


class PlayableApplication(PlayableBinary):
    supported_mimetypes = []


class PDF(Application):
    supported_mimetypes = ['application/pdf', ]


class Flash(PlayableApplication):
    supported_mimetypes = ['application/x-shockwave-flash', ]


class Video(Binary):
    supported_mimetypes = ['video/', ]


class PlayableVideo(PlayableBinary):
    supported_mimetypes = ['video/mpg', 'video/fli', 'video/mp4', 'video/quicktime',
                           'video/ogg', 'video/x-flv', 'video/x-ms-asf', 'video/x-ms-wm',
                           'video/x-ms-wmv', 'video/x-msvideo',
                          ]
    width = "640px"
    height = "400px"


class Audio(Binary):
    supported_mimetypes = ['audio/', ]


class PlayableAudio(PlayableBinary):
    supported_mimetypes = ['audio/midi', 'audio/x-aiff', 'audio/x-ms-wma',
                           'audio/x-pn-realaudio',
                           'audio/x-wav',
                           'audio/mpeg',
                           'audio/ogg',
                          ]
    width = "200px"
    height = "100px"


class Image(Binary):
    """ Any Image mimetype """
    supported_mimetypes = ['image/', ]


class RenderableImage(RenderableBinary):
    """ Any Image mimetype """
    supported_mimetypes = []


class SvgImage(RenderableImage):
    """ SVG images use <object> tag mechanism from RenderableBinary base class """
    supported_mimetypes = ['image/svg+xml']


class RenderableBitmapImage(RenderableImage):
    """ PNG/JPEG/GIF images use <img> tag (better browser support than <object>) """
    supported_mimetypes = [] # if mimetype is also transformable, please list
                             # in TransformableImage ONLY!

    transclude_acceptable_attrs = ['class', 'title', 'longdesc', 'width', 'height', 'align', ] # no style because of JS
    def transclude(self, desc, tag_attrs=None, query_args=None):
        if tag_attrs is None:
            tag_attrs = {}
        if query_args is None:
            query_args = {}
        if 'class' not in tag_attrs:
            tag_attrs['class'] = 'image'
        if desc:
            for attr in ['alt', 'title', ]:
                if attr not in tag_attrs:
                    tag_attrs[attr] = desc
        if 'do' not in query_args:
            query_args['do'] = 'get'
        url = self.rev_url(**query_args)
        return self.formatter.image(src=url, **tag_attrs)

    def _render_data(self):
        return self.transclude(self.name)


class TransformableBitmapImage(RenderableBitmapImage):
    """ We can transform (resize, rotate, mirror) some image types """
    supported_mimetypes = ['image/png', 'image/jpeg', 'image/gif', ]

    def _transform(self, content_type, cache, size=None, transpose_op=None):
        """ resize to new size (optional), transpose according to exif infos,
            write data as content_type (default: same ct as original image)
            to the cache.
        """
        try:
            from PIL import Image as PILImage
        except ImportError:
            # no PIL, we can't do anything, we just output the revision data as is
            outfile = cache.data_cache
            outfile.open(mode='wb')
            shutil.copyfileobj(self.rev, outfile)
            outfile.close()
            cache.put(None, content_type=content_type)
            return

        if content_type == 'image/jpeg':
            output_type = 'JPEG'
        elif content_type == 'image/png':
            output_type = 'PNG'
        elif content_type == 'image/gif':
            output_type = 'GIF'
        else:
            raise ValueError("content_type %r not supported" % content_type)

        # revision obj has read() seek() tell(), thus this works:
        image = PILImage.open(self.rev)
        image.load()

        try:
            # if we have EXIF data, we can transpose (e.g. rotate left),
            # so the rendered image is correctly oriented:
            transpose_op = transpose_op or 1 # or self.exif['Orientation']
        except KeyError:
            transpose_op = 1 # no change

        if size is not None:
            image = image.copy() # create copy first as thumbnail works in-place
            image.thumbnail(size, PILImage.ANTIALIAS)

        transpose_func = {
            1: lambda image: image,
            2: lambda image: image.transpose(PILImage.FLIP_LEFT_RIGHT),
            3: lambda image: image.transpose(PILImage.ROTATE_180),
            4: lambda image: image.transpose(PILImage.FLIP_TOP_BOTTOM),
            5: lambda image: image.transpose(PILImage.ROTATE_90).transpose(PILImage.FLIP_TOP_BOTTOM),
            6: lambda image: image.transpose(PILImage.ROTATE_270),
            7: lambda image: image.transpose(PILImage.ROTATE_90).transpose(PILImage.FLIP_LEFT_RIGHT),
            8: lambda image: image.transpose(PILImage.ROTATE_90),
        }
        image = transpose_func[transpose_op](image)

        outfile = cache.data_cache
        outfile.open(mode='wb')
        image.save(outfile, output_type)
        outfile.close()
        cache.put(None, content_type=content_type)

    def _do_get_modified(self, hash):
        request = self.request
        try:
            width = int(request.values.get('w'))
        except (TypeError, ValueError):
            width = None
        try:
            height = int(request.values.get('h'))
        except (TypeError, ValueError):
            height = None
        try:
            transpose = int(request.values.get('t'))
            assert 1 <= transpose <= 8
        except (TypeError, ValueError, AssertionError):
            transpose = 1
        if width or height or transpose != 1:
            # resize requested, XXX check ACL behaviour! XXX
            hash_name = request.cfg.hash_algorithm
            hash_hexdigest = self.rev[hash_name]
            cache_meta = [ # we use a list to have order stability
                (hash_name, hash_hexdigest),
                ('width', width),
                ('height', height),
                ('transpose', transpose),
            ]
            cache = SendCache.from_meta(request, cache_meta)
            if not cache.exists():
                content_type = self.rev[MIMETYPE]
                size = (width or 99999, height or 99999)
                self._transform(content_type, cache=cache, size=size, transpose_op=transpose)
            from_cache = cache.key
        else:
            from_cache = request.values.get('from_cache')
        self._do_get(hash, from_cache=from_cache)

    def _render_data_diff(self, oldrev, newrev):
        try:
            from PIL import Image as PILImage
            from PIL.ImageChops import difference as PILdiff
        except ImportError:
            # no PIL, we can't do anything, we just call the base class method
            return super(TransformableBitmapImage, self)._render_data_diff(oldrev, newrev)

        content_type = newrev[MIMETYPE]
        if content_type == 'image/jpeg':
            output_type = 'JPEG'
        elif content_type == 'image/png':
            output_type = 'PNG'
        elif content_type == 'image/gif':
            output_type = 'GIF'
        else:
            raise ValueError("content_type %r not supported" % content_type)

        oldimage = PILImage.open(oldrev)
        newimage = PILImage.open(newrev)
        oldimage.load()
        newimage.load()

        diffimage = PILdiff(newimage, oldimage)

        request = self.request
        hash_name = request.cfg.hash_algorithm
        cache_meta = [ # we use a list to have order stability
            (hash_name, oldrev[hash_name], newrev[hash_name]),
        ]
        cache = SendCache.from_meta(request, cache_meta)
        if not cache.exists():
            outfile = cache.data_cache
            outfile.open(mode='wb')
            diffimage.save(outfile, output_type)
            outfile.close()
            cache.put(None, content_type=content_type)
        return self.transclude(desc='diff', query_args=dict(from_cache=cache.key))


class Text(Binary):
    """ Any kind of text """
    supported_mimetypes = ['text/']
    converter_mimetype = None

    # text/plain mandates crlf - but in memory, we want lf only
    def data_internal_to_form(self, text):
        """ convert data from memory format to form format """
        return text.replace(u'\n', u'\r\n')

    def data_form_to_internal(self, data):
        """ convert data from form format to memory format """
        return data.replace(u'\r\n', u'\n')

    def data_internal_to_storage(self, text):
        """ convert data from memory format to storage format """
        return text.replace(u'\n', u'\r\n').encode(config.charset)

    def data_storage_to_internal(self, data):
        """ convert data from storage format to memory format """
        return data.decode(config.charset).replace(u'\r\n', u'\n')

    def _render_data(self):
        from MoinMoin.converter2 import default_registry as reg
        from MoinMoin.util.iri import Iri
        from MoinMoin.util.mime import Type, type_moin_document
        from MoinMoin.util.tree import moin_page

        request = self.request
        input_conv = reg.get(Type(self.mimetype), type_moin_document,
                request=request)
        include_conv = reg.get(type_moin_document, type_moin_document,
                includes='expandall', request=request)
        link_conv = reg.get(type_moin_document, type_moin_document,
                links='extern', request=request)
        # TODO: Real output format
        html_conv = reg.get(type_moin_document,
                Type('application/x-xhtml-moin-page'), request=request)

        i = Iri(scheme='wiki', authority='', path='/' + self.name)

        doc = input_conv(self.data_storage_to_internal(self.data).split(u'\n'))
        doc.set(moin_page.page_href, unicode(i))
        doc = include_conv(doc)
        doc = link_conv(doc)
        doc = html_conv(doc)

        from array import array
        out = array('u')
        # TODO: Switch to xml
        doc.write(out.fromunicode, method='html')
        return out.tounicode()

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self._render_data()

    def _render_data_diff(self, oldrev, newrev):
        from MoinMoin.util import diff_html
        return diff_html.diff(self.request,
                              self.data_storage_to_internal(oldrev.read()),
                              self.data_storage_to_internal(newrev.read()))

    def do_modify(self, template_name):
        if template_name:
            item = Item.create(self.request, template_name)
            data_text = self.data_storage_to_internal(item.data)
        else:
            data_text = self.data_storage_to_internal(self.data)
        meta_text = self.meta_dict_to_text(self.meta)
        template = self.env.get_template('modify_text.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  rows_data=20, rows_meta=3, cols=80,
                                  revno=0,
                                  data_text=data_text,
                                  meta_text=meta_text,
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content

    def do_highlight(self):
        request = self.request
        template = self.env.get_template('highlight.html')
        data_text = self.data_storage_to_internal(self.data)
        Parser = wikiutil.searchAndImportPlugin(request.cfg, "parser", 'highlight')
        parser = Parser(data_text, request, format_args=self.mimetype)
        buffer = StringIO()
        request.redirect(buffer)
        parser.format(self.formatter)
        content = buffer.getvalue()
        request.redirect()
        del buffer

        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  data_text=content,
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content


class HTML(Text):
    """ HTML markup """
    supported_mimetypes = ['text/html']

    def _render_data(self):
        return self.data_storage_to_internal(self.data)

    def do_modify(self, template_name):
        if template_name:
            item = Item.create(self.request, template_name)
            data_text = self.data_storage_to_internal(item.data)
        else:
            data_text = self.data_storage_to_internal(self.data)
        meta_text = self.meta_dict_to_text(self.meta)
        template = self.env.get_template('modify_text_html.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  rows_data=20, rows_meta=3, cols=80,
                                  revno=0,
                                  data_text=data_text,
                                  meta_text=meta_text,
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content



class MoinWiki(Text):
    """ MoinMoin wiki markup """
    supported_mimetypes = ['text/x-unidentified-wiki-format',
                           'text/x.moin.wiki',
                          ]  # XXX Improve mimetype handling
    converter_mimetype = 'text/x.moin.wiki'


class CreoleWiki(Text):
    """ Creole wiki markup """
    supported_mimetypes = ['text/x.moin.creole']


class CSV(Text):
    """ Comma Separated Values format """
    supported_mimetypes = ['text/csv']
    format = 'csv'
    format_args = ''


class SafeHTML(Text):
    """ HTML markup """
    supported_mimetypes = ['text/x-safe-html']
    format = 'html'
    format_args = supported_mimetypes[0]

    # XXX duplicated from HTML class
    def do_modify(self, template_name):
        if template_name:
            item = Item.create(self.request, template_name)
            data_text = self.data_storage_to_internal(item.data)
        else:
            data_text = self.data_storage_to_internal(self.data)
        meta_text = self.meta_dict_to_text(self.meta)
        template = self.env.get_template('modify_text_html.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  rows_data=20, rows_meta=3, cols=80,
                                  revno=0,
                                  data_text=data_text,
                                  meta_text=meta_text,
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content


class DiffPatch(Text):
    """ diff output / patch input format """
    supported_mimetypes = ['text/x-diff']
    format = 'highlight'
    format_args = supported_mimetypes[0]


class IRCLog(Text):
    """ Internet Relay Chat Log """
    supported_mimetypes = ['text/x-irclog']
    format = 'highlight'
    format_args = supported_mimetypes[0]


class PythonSrc(Text):
    """ Python source code """
    supported_mimetypes = ['text/x-python']
    format = 'highlight'
    format_args = supported_mimetypes[0]


class TWikiDraw(TarMixin, Image):
    """
    drawings by TWikiDraw applet. It creates three files which are stored as tar file.
    """
    supported_mimetypes = ["application/x-twikidraw"]
    modify_help = ""

    def modify(self):
        # called from modify UI/POST
        request = self.request
        file_upload = request.files.get('filepath')
        filename = request.form['filename']
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)

        filecontent = file_upload.stream
        content_length = None
        if ext == '.draw': # TWikiDraw POSTs this first
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.replace("\r", "")
        elif ext == '.map':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.strip()
        elif ext == '.png':
            #content_length = file_upload.content_length
            # XXX gives -1 for wsgiref, gives 0 for werkzeug :(
            # If this is fixed, we could use the file obj, without reading it into memory completely:
            filecontent = filecontent.read()

        self.put_member('drawing' + ext, filecontent, content_length,
                        expected_members=set(['drawing.draw', 'drawing.map', 'drawing.png']))

    def do_modify(self, template_name):
        """
        Fills params into the template for initialzing of the the java applet.
        The applet is called for doing modifications.
        """
        request = self.request
        twd_params = {
            'pubpath': request.cfg.url_prefix_static + '/applets/TWikiDrawPlugin',
            'pngpath': self.url(do='get', member='drawing.png'),
            'drawpath': self.url(do='get', member='drawing.draw'),
            'savelink': self.url(do='modify', mimetype=self.supported_mimetypes[0]),
            'pagelink': self.url(),
            'helplink': self.modify_help,
            'basename': 'drawing',
        }
        template = self.env.get_template("modify_twikidraw.html")
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  revno=0,
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  help=self.modify_help,
                                  t=twd_params,
                                 )
        return content

    def _render_data(self):
        request = self.request
        item_name = self.name
        drawing_url = self.url(do='get', member='drawing.draw')
        png_url = self.url(do='get', member='drawing.png')
        title = _('Edit drawing %(filename)s (opens in new window)') % {'filename': item_name}

        mapfile = self.get_member('drawing.map')
        try:
            image_map = mapfile.read()
            mapfile.close()
        except (IOError, OSError):
            image_map = ''
        if image_map:
            # we have a image map. inline it and add a map ref to the img tag
            mapid = 'ImageMapOf' + item_name
            image_map = image_map.replace('%MAPNAME%', mapid)
            # add alt and title tags to areas
            image_map = re.sub(r'href\s*=\s*"((?!%TWIKIDRAW%).+?)"', r'href="\1" alt="\1" title="\1"', image_map)
            image_map = image_map.replace('%TWIKIDRAW%"', '%s" alt="%s" title="%s"' % (drawing_url, title, title))
            # unxml, because 4.01 concrete will not validate />
            image_map = image_map.replace('/>', '>')
            title = _('Clickable drawing: %(filename)s') % {'filename': item_name}

            return image_map + '<img src="%s" alt="%s" usemap="#%s">' % (png_url, title, mapid)
        else:
            return '<img src="%s" alt=%s>' % (png_url, title)


class AnyWikiDraw(TarMixin, Image):
    """
    drawings by AnyWikiDraw applet. It creates three files which are stored as tar file.
    """
    supported_mimetypes = ["application/x-anywikidraw"]
    modify_help = ""

    def modify(self):
        # called from modify UI/POST
        request = self.request
        file_upload = request.files.get('filepath')
        filename = request.form['filename']
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)
        filecontent = file_upload.stream
        content_length = None
        if ext == '.svg':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.replace("\r", "")
        elif ext == '.map':
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.strip()
        elif ext == '.png':
            #content_length = file_upload.content_length
            # XXX gives -1 for wsgiref, gives 0 for werkzeug :(
            # If this is fixed, we could use the file obj, without reading it into memory completely:
            filecontent = filecontent.read()
        self.put_member('drawing' + ext, filecontent, content_length,
                        expected_members=set(['drawing.svg', 'drawing.map', 'drawing.png']))

    def do_modify(self, template_name):
        """
        Fills params into the template for initialzing of the the java applet.
        The applet is called for doing modifications.
        """
        request = self.request
        if 'drawing.svg' in self.list_members():
            drawpath = self.url(do='get', member='drawing.svg')
        else:
            drawpath = ''

        awd_params = {
            'name': 'drawing.svg',
            'drawpath': drawpath,
            'pagelink': self.url(),
            'savelink': self.url(do='modify', mimetype=self.supported_mimetypes[0]),
            'pubpath': request.cfg.url_prefix_static + "/applets/anywikidraw/lib",
        }

        template = self.env.get_template("modify_anywikidraw.html")
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  revno=0,
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  help=self.modify_help,
                                  t=awd_params,
                                 )
        return content

    def _render_data(self):
        request = self.request
        drawing_url = self.url(do='get', member='drawing.svg')
        png_url = self.url(do='get', member='drawing.png')
        title = _('Edit drawing %(filename)s (opens in new window)') % {'filename': self.name}

        mapfile = self.get_member('drawing.map')
        try:
            image_map = mapfile.read()
            mapfile.close()
        except (IOError, OSError):
            image_map = ''
        if image_map:
            # ToDo mapid must become uniq
            # we have a image map. inline it and add a map ref to the img tag
            # we have also to set a unique ID
            mapid = 'ImageMapOf' + self.name
            image_map = image_map.replace(u'id="drawing.svg"', '')
            image_map = image_map.replace(u'name="drawing.svg"', u'name="%s"' % mapid)
            # unxml, because 4.01 concrete will not validate />
            image_map = image_map.replace(u'/>', u'>')
            title = _('Clickable drawing: %(filename)s') % {'filename': self.name}
            return image_map + '<img src="%s" alt="%s" usemap="#%s">' % (png_url, title, mapid)
        else:
            return '<img src="%s" alt=%s>' % (png_url, title)
