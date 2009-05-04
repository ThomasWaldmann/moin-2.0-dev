# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - misc. mimetype items
    
    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, time, datetime

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

    def save(self):
        request = self.request
        item_name = self.item_name
        data_file = request.files.get('data_file')
        data_text = request.form.get('data_text')
        meta_text = request.form.get('meta_text', '')
        if data_text is not None:
            data = self.data_form_to_internal(data_text)
            data = self.data_internal_to_storage(data)
        elif data_file:
            data = data_file.stream
        else:
            data = ''
        meta = self.meta_text_to_dict(meta_text)
        backend = request.cfg.data_backend
        try:
            storage_item = backend.get_item(item_name)
        except NoSuchItemError:
            storage_item = backend.create_item(item_name)
        try:
            rev_no = storage_item.get_revision(-1).revno
        except NoSuchRevisionError:
            rev_no = -1
        newrev = storage_item.create_revision(rev_no + 1)
        self._write_stream(data, newrev)
        timestamp = time.time()
        newrev[EDIT_LOG_COMMENT] = meta.get(EDIT_LOG_COMMENT, '')
        mimetype = wikiutil.MimeType(filename=data_file.filename).mime_type()
        # mimetype: 1. meta data, 2. url/post 3. filename
        mimetype = request.values.get('mimetype', mimetype)
        newrev["mimetype"] = meta.get('mimetype', mimetype)
        newrev[EDIT_LOG_ACTION] = 'SAVE'
        newrev[EDIT_LOG_ADDR] = request.remote_addr
        newrev[EDIT_LOG_HOSTNAME] = wikiutil.get_hostname(request, request.remote_addr)
        newrev[EDIT_LOG_USERID] = request.user.valid and request.user.id or ''
        newrev[EDIT_LOG_EXTRA] = ''
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
        ('text items', [
            ('text/plain', 'plain text'), 
        ]),
        ('image items', [
            ('image/jpeg', 'JPEG image'), 
            ('image/png', 'PNG image'),
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

class Text(Binary):
    supported_mimetypes = ['text/']
    is_text = True

    def get_data(self):
        if self.rev is not None:
            return self.rev.read_data()
        else:
            return ''
    data = property(fget=get_data)

    def data_internal_to_form(self, text):
        """ convert data from memory unicode text format to form format """
        data = text
        return data
    
    def data_form_to_internal(self, data):
        """ convert data from form format to memory unicode text format """
        text = data
        return text
    
    def data_internal_to_storage(self, text):
        """ convert data from memory unicode text format to storage format """
        text = text.replace(u'\n', u'\r\n') # text/plain mandates crlf
        data = text.encode(config.charset)
        return data
    
    def data_storage_to_internal(self, data):
        """ convert data from storage format to in memory unicode text """
        # text processing items can overwrite this with a text normalization
        text = data.decode(config.charset)
        text = text.replace(u'\r', u'')
        return text
    
    def _render_data(self):
        return "<pre>%s</pre>" % self.data_storage_to_internal(self.data) # XXX to_form()?

    def do_modify(self):
        template = self.env.get_template('modify_text.html')
        content = template.render(gettext=self.request.getText,
                                  rows_data=20, rows_meta=3, cols=80,
                                  revno=0,
                                  data_text=self.data_storage_to_internal(self.data),
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  lang='en', direction='ltr',
                                  help=self.modify_help,
                                 )
        return content


class MoinWiki(Text):
    supported_mimetypes = ['text/x-unidentified-wiki-format',
                           'text/moin',
                          ]  # XXX Improve mimetype handling
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
        Parser = wikiutil.searchAndImportPlugin(request.cfg, "parser", pi['format'])
        parser = Parser(body, request, format_args=pi['formatargs'])
        from StringIO import StringIO
        buffer = StringIO()
        request.redirect(buffer)
        parser.format(formatter)
        content = buffer.getvalue()
        request.redirect()
        del buffer
        return content


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

