# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - misc. mimetype items
    
    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, time, datetime, shutil

from MoinMoin import log
logging = log.getLogger(__name__)

from jinja2 import Environment, PackageLoader, Template, FileSystemBytecodeCache, Markup

from werkzeug import http_date

from MoinMoin import wikiutil, config, user
from MoinMoin.util import timefuncs
from MoinMoin.Page import Page
from MoinMoin.Page import DELETED, EDIT_LOG_ADDR, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
                          EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_ACTION
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError


class Item(object):
    is_text = False
    def __init__(self, request, env, item_name, rev=None):
        self.request = request
        self.env = env
        self.item_name = item_name
        self.rev = rev

    def get_meta(self):
        return self.rev or {}
    meta = property(fget=get_meta)
    
    def meta_text_to_dict(self, text):
        """ convert meta data from a text fragment to a dict """
        meta = {}
        for line in text.splitlines():
            k, v = line.split(':')
            k, v = k.strip(), v.strip()
            meta[k] = v
        return meta

    def meta_dict_to_text(self, meta):
        text = u'\n'.join([u"%s: %s" % (k, v) for k, v in meta.items()])
        return text

    def get_data(self):
        return '' # TODO create a better method for binary stuff
    data = property(fget=get_data)

    def do_modify(self):
        template = self.env.get_template('modify_binary.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.item_name,
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
                                  item_name=self.item_name,
                                  revno=revno,
                                  target=target,
                                 )
        return content

    def do_rename(self):
        return self._action_query('rename', target=self.item_name)

    def do_copy(self):
        return self._action_query('copy', target=self.item_name)

    def do_revert(self):
        return self._action_query('revert', revno=self.rev.revno)

    def _write_stream(self, content, new_rev, bufsize=8192):
        if hasattr(content, "read"):
            while True:
                buf = content.read(bufsize)
                if not buf:
                    break
                new_rev.write(buf)
        elif isinstance(content, str):
            new_rev.write(content)
        else:
            logging.error("unsupported content object: %r" % content)
            raise

    def copy(self):
        # called from copy UI/POST
        request = self.request
        comment = request.form.get('comment')
        target = request.form.get('target')
        old_item = self.rev.item
        backend = request.cfg.data_backend
        new_item = backend.create_item(target)
        # Transfer all revisions with their data and metadata
        # Make sure the list begins with the lowest value, that is, 0.
        revs = old_item.list_revisions()
        for revno in revs:
            old_rev = old_item.get_revision(revno)
            new_rev = new_item.create_revision(revno)
            shutil.copyfileobj(old_rev, new_rev, 8192)
            for key in old_rev:
                new_rev[key] = old_rev[key]
            new_item.commit()
        current_rev = old_item.get_revision(revno)
        # transfer item metadata
        new_item.change_metadata()
        for key in old_item:
            new_item[key] = old_item[key]
        new_item.publish_metadata()
        # we just create a new revision with almost same meta/data to show up on RC
        self._save(current_rev, current_rev, item_name=target, action='SAVE/COPY', extra=self.item_name, comment=comment)

    def rename(self):
        # called from rename UI/POST
        comment = self.request.form.get('comment')
        # we just create a new revision with almost same meta/data to show up on RC
        self._save(self.meta, self.data, action='SAVE/RENAME', extra=self.item_name, comment=comment)
        target = self.request.form.get('target')
        self.rev.item.rename(target)

    def revert(self):
        # called from revert UI/POST
        comment = self.request.form.get('comment')
        self._save(self.meta, self.data, comment=comment)

    def modify(self):
        # called from modify UI/POST
        request = self.request
        delete = request.form.get('delete')
        if delete:
            data = ''
            mimetype = None
        else:
            data_file = request.files.get('data_file')
            if data_file.filename:
                # user selected a file to upload
                data = data_file.stream
                mimetype = wikiutil.MimeType(filename=data_file.filename).mime_type()
            else:
                # take text from textarea
                data_text = request.form.get('data_text', '')
                data = self.data_form_to_internal(data_text)
                data = self.data_internal_to_storage(data)
                mimetype = 'text/plain'
        meta_text = request.form.get('meta_text', '')
        meta = self.meta_text_to_dict(meta_text)
        comment = self.request.form.get('comment')
        self._save(meta, data, mimetype=mimetype, comment=comment)

    def _save(self, meta, data, item_name=None, action='SAVE', mimetype=None, comment='', extra=''):
        request = self.request
        if item_name is None:
            item_name = self.item_name
        backend = request.cfg.data_backend
        try:
            storage_item = backend.get_item(item_name)
        except NoSuchItemError:
            storage_item = backend.create_item(item_name)
        try:
            currentrev = storage_item.get_revision(-1)
            rev_no = currentrev.revno
            if mimetype is None:
                # if we didn't get mimetype info, thus reusing the one from current rev:
                mimetype = currentrev.get("mimetype")
        except NoSuchRevisionError:
            rev_no = -1
        newrev = storage_item.create_revision(rev_no + 1)
        if not data:
            # saving empty data is same as deleting
            # XXX unclear: do we have meta-only items that shall not be "deleted" state?
            newrev[DELETED] = True
            comment = comment or 'deleted'
        self._write_stream(data, newrev)
        timestamp = time.time()
        newrev[EDIT_LOG_COMMENT] = comment or meta.get(EDIT_LOG_COMMENT, '')
        # allow override by form- / qs-given mimetype:
        mimetype = request.values.get('mimetype', mimetype)
        # allow override by give metadata:
        newrev["mimetype"] = meta.get('mimetype', mimetype)
        newrev[EDIT_LOG_ACTION] = action
        newrev[EDIT_LOG_ADDR] = request.remote_addr
        newrev[EDIT_LOG_HOSTNAME] = wikiutil.get_hostname(request, request.remote_addr)
        newrev[EDIT_LOG_USERID] = request.user.valid and request.user.id or ''
        newrev[EDIT_LOG_EXTRA] = extra
        storage_item.commit()
        #event = FileAttachedEvent(request, pagename, target, new_rev.size)
        #send_event(event)


class NonExistent(Item):
    supported_mimetypes = [] # only explicitely used
    template_groups = [
        ('moin wiki text items', [
            ('HomePageTemplate', 'home page (moin)'), 
            ('GroupPageTemplate', 'group page (moin)'), 
        ]),
        ('creole wiki text items', [
            ('CreoleHomePageTemplate', 'home page (creole)'), 
            ('CreoleGroupPageTemplate', 'group page (creole)'), 
        ]),
    ]
    mimetype_groups = [
        ('page markup text items', [
            ('text/moin-wiki', 'wiki (moin)'), 
            ('text/creole-wiki', 'wiki (creole)'), 
            ('text/html', 'html'),
        ]),
        ('highlighted text items', [
            ('text/x-diff', 'diff/patch'),
            ('text/x-python', 'python code'),
        ]),
        ('other text items', [
            ('text/plain', 'plain text'), 
            ('text/csv', 'csv'),
        ]),
        ('image items', [
            ('image/jpeg', 'JPEG'), 
            ('image/png', 'PNG'),
            ('image/svg+xml', 'SVG'),
        ]),
        ('other items', [
            ('application/pdf', 'PDF'), 
            ('application/zip', 'ZIP'),
            ('application/x-tar', 'TAR'),
            ('application/x-gtar', 'TGZ'),
            ('application/octet-stream', 'binary file'),
        ]),
    ]

    def do_show(self):
        template = self.env.get_template('show_nonexistent.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.item_name,
                                  template_groups=self.template_groups,
                                  mimetype_groups=self.mimetype_groups, )
        return content

    def do_get(self):
        self.request.status_code = 404


class Binary(Item):
    supported_mimetypes = [''] # fallback, because every mimetype starts with ''
    modify_help = """\
There is no help, you're doomed!
"""
    def _revlog(self, item, rev_nos):
        log = []
        for rev_no in reversed(rev_nos):
            r = item.get_revision(rev_no)
            log.append(dict(
                rev_no=rev_no,
                size=r.size,
                mtime=self.request.user.getFormattedDateTime(float(r.timestamp)),
                editor=user.get_printable_editor(self.request,
                       r[EDIT_LOG_USERID], r[EDIT_LOG_ADDR], r[EDIT_LOG_HOSTNAME]) or _("N/A"),
                comment=r.get(EDIT_LOG_COMMENT, ''),
                mimetype=r.get('mimetype', ''),
            ))
        return log

    def _render_meta(self):
        return "<pre>%s</pre>" % self.meta_dict_to_text(self.meta)

    def _render_data(self):
        return ""

    def do_show(self):
        item = self.rev.item
        rev_nos = item.list_revisions()
        log = self._revlog(item, rev_nos)

        template = self.env.get_template('show.html')
        content = template.render(gettext=self.request.getText,
                                  rev=self.rev,
                                  log=log,
                                  first_rev_no=rev_nos[0],
                                  last_rev_no=rev_nos[-1],
                                  data_rendered=self._render_data(),
                                  meta_rendered=self._render_meta(),
                                 )
        return content

    def do_get(self, content_disposition=None):
        request = self.request
        from_tar = request.values.get('from_tar')
        if from_tar:
            self.do_get_from_tar(from_tar)
        else:
            rev = self.rev
            # TODO: fix 304 behaviour, does not work yet! header problem?
            timestamp = datetime.datetime.fromtimestamp(rev.timestamp)
            if_modified = request.if_modified_since
            if if_modified and if_modified >= timestamp:
                request.status_code = 304
            else:
                request.status_code = 200
                request.content_length = rev.size
                timeout = 24 * 3600
                request.headers.add('Cache-Control', 'max-age=%d, public' % timeout)
                request.headers.add('Expires', http_date(time.time() + timeout))
                request.headers.add('Last-Modified', http_date(timestamp))
                try:
                    mimestr = rev["mimetype"]
                except KeyError:
                    mimestr = mimetypes.guess_type(rev.item.name)[0]
                mt = wikiutil.MimeType(mimestr=mimestr)
                content_type = mt.content_type()
                mime_type = mt.mime_type()
                request.content_type = content_type # request.mimetype = ... ?
                # for dangerous files (like .html), when we are in danger of cross-site-scripting attacks,
                # we just let the user store them to disk ('attachment').
                # For safe files, we directly show them inline (this also works better for IE).
                dangerous = mime_type in request.cfg.mimetypes_xss_protect
                if content_disposition is None:
                    content_disposition = dangerous and 'attachment' or 'inline'
                # TODO: fix the encoding here, plain 8 bit is not allowed according to the RFCs
                # There is no solution that is compatible to IE except stripping non-ascii chars
                #filename_enc = filename.encode(config.charset)
                #content_disposition += '; filename="%s"' % filename_enc
                request.headers.add('Content-Disposition', content_disposition)
                # send data
                request.send_file(rev)

    def do_get_from_tar(self, member):
        # TODO: make it work, file access to storage items?
        timestamp = datetime.datetime.fromtimestamp(self.timestamp)
        if_modified = request.if_modified_since
        if if_modified and if_modified >= timestamp:
            request.status_code = 304
        else:
            ci = ContainerItem(request, item_name)
            filename = wikiutil.taintfilename(member)
            mt = wikiutil.MimeType(filename=filename)
            content_type = mt.content_type()
            mime_type = mt.mime_type()

            # TODO: fix the encoding here, plain 8 bit is not allowed according to the RFCs
            # There is no solution that is compatible to IE except stripping non-ascii chars
            filename_enc = filename.encode(config.charset)

            # for dangerous files (like .html), when we are in danger of cross-site-scripting attacks,
            # we just let the user store them to disk ('attachment').
            # For safe files, we directly show them inline (this also works better for IE).
            dangerous = mime_type in request.cfg.mimetypes_xss_protect
            content_dispo = dangerous and 'attachment' or 'inline'

            request.content_type = content_type
            request.last_modified = timestamp
            #request.content_length = os.path.getsize(fpath)
            content_dispo_string = '%s; filename="%s"' % (content_dispo, filename_enc)
            request.headers.add('Content-Disposition', content_dispo_string)

            # send data
            request.send_file(ci.get(filename))


class Image(Binary):
    supported_mimetypes = ['image/']

    def _render_data(self):
        return '<img src="?action=get&rev=%d">' % self.rev.revno

class SvgImage(Binary):
    supported_mimetypes = ['image/svg+xml']

    def _render_data(self):
        return """
            <object data="?action=get&rev=%d" type="image/svg+xml">
            image needs SVG rendering capability
            </object>
        """ % self.rev.revno

class Text(Binary):
    supported_mimetypes = ['text/']
    is_text = True

    def get_data(self):
        if self.rev is not None:
            return self.rev.read_data()
        else:
            return ''
    data = property(fget=get_data)

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
        return u"<pre>%s</pre>" % self.data_storage_to_internal(self.data) # XXX to_form()?

    def do_modify(self):
        template = self.env.get_template('modify_text.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.item_name,
                                  rows_data=20, rows_meta=3, cols=80,
                                  revno=0,
                                  data_text=self.data_storage_to_internal(self.data),
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content


class MoinParserSupported(Text):
    supported_mimetypes = []
    format = 'wiki' # override this, if needed
    format_args = ''
    def _render_data(self):
        # TODO: switch from Page to Item subclass
        request = self.request
        page = Page(request, self.item_name)
        pi, body = page.pi, page.data
        from MoinMoin.formatter.text_html import Formatter
        formatter = Formatter(request)
        formatter.setPage(page)
        #lang = pi.get('language', request.cfg.language_default)
        #request.setContentLanguage(lang)
        Parser = wikiutil.searchAndImportPlugin(request.cfg, "parser", self.format)
        parser = Parser(body, request, format_args=self.format_args)
        from StringIO import StringIO
        buffer = StringIO()
        request.redirect(buffer)
        parser.format(formatter)
        content = buffer.getvalue()
        request.redirect()
        del buffer
        return content

class MoinWiki(MoinParserSupported):
    supported_mimetypes = ['text/x-unidentified-wiki-format',
                           'text/moin-wiki',
                          ]  # XXX Improve mimetype handling
    format = 'wiki'
    format_args = ''


class CreoleWiki(MoinParserSupported):
    supported_mimetypes = ['text/creole-wiki']
    format = 'creole'
    format_args = ''

class CSV(MoinParserSupported):
    supported_mimetypes = ['text/csv']
    format = 'csv'
    format_args = ''

class DiffPatch(MoinParserSupported):
    supported_mimetypes = ['text/x-diff']
    format = 'highlight'
    format_args = 'diff'

class HTML(MoinParserSupported):
    supported_mimetypes = ['text/html']
    format = 'html'
    format_args = ''

class PythonSrc(MoinParserSupported):
    supported_mimetypes = ['text/x-python']
    format = 'highlight'
    format_args = 'python'


class Manager(object):
    def __init__(self, request, item_name, mimetype=None, rev_no=-1):
        self.request = request
        self.item_name = item_name
        self.item_mimetype = mimetype
        self.rev_no = rev_no
        jinja_cachedir = os.path.join(request.cfg.cache_dir, 'jinja')
        try:
            os.mkdir(jinja_cachedir)
        except:
            pass
        self.env = Environment(loader=PackageLoader('MoinMoin', 'templates'),
                               bytecode_cache=FileSystemBytecodeCache(jinja_cachedir, '%s'), 
                               extensions=['jinja2.ext.i18n'])
        from werkzeug import url_quote, url_encode
        self.env.filters['urlencode'] = lambda x: url_encode(x)
        self.env.filters['urlquote'] = lambda x: url_quote(x)

    def _find_item_class(self, mimetype, BaseClass=Item, best_match_len=-1):
        Class = None
        for ItemClass in BaseClass.__subclasses__():
            for supported_mimetype in ItemClass.supported_mimetypes:
                if mimetype.startswith(supported_mimetype):
                    match_len = len(supported_mimetype)
                    if match_len > best_match_len:
                        best_match_len = match_len
                        Class = ItemClass
            better_Class = self._find_item_class(mimetype, ItemClass, best_match_len)
            if better_Class:
                Class = better_Class
        return Class

    def get_item(self):
        request = self.request
        try:
            item = request.cfg.data_backend.get_item(self.item_name)
        except NoSuchItemError:
            rev = None
            ItemClass = NonExistent
            mimetype = self.item_mimetype
        else:
            try:
                rev = item.get_revision(self.rev_no)
            except NoSuchRevisionError:
                rev = item.get_revision(-1) # fall back to current revision
                # XXX add some message about invalid revision
            mimetype = rev.get("mimetype")
        if mimetype:
            ItemClass = self._find_item_class(mimetype)
        return ItemClass(request, env=self.env, item_name=self.item_name, rev=rev) 

