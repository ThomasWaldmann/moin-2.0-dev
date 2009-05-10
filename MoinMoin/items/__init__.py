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
from StringIO import StringIO

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

from MoinMoin.items.sendcache import SendCache

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

    def get_index(self):
        """ create an index of sub items of this item """
        import re
        from MoinMoin.search.term import AND, NOT, NameRE, LastRevisionMetaDataMatch

        if self.item_name:
            prefix = self.item_name + u'/'
        else:
            # trick: an item of empty name can be considered as "virtual root item",
            # that has all wiki items as sub items
            prefix = u''
        sub_item_re = u"^%s.*" % re.escape(prefix)
        regex = re.compile(sub_item_re, re.UNICODE)

        item_iterator = self.request.cfg.data_backend.search_item(
                            AND(NameRE(regex),
                                NOT(LastRevisionMetaDataMatch('deleted', True))))

        # We only want the sub-item part of the item names, not the whole item objects.
        prefix_len = len(prefix)
        items = [(item.name, item.name[prefix_len:], item.get_revision(-1).get("mimetype"))
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
                                  item_name=self.item_name,
                                  index=self.flat_index(),
                                 )
        return content


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
            ('text/x-irclog', 'IRC log'),
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
                                  index=self.flat_index(),
                                 )
        return content

    def _render_data_diff(self, oldrev, newrev):
        return "Can not compare binary items."

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
        # XXX is it ok to use rev.timestamp for tar/cache/normal?
        timestamp = datetime.datetime.fromtimestamp(self.rev.timestamp)
        if_modified = request.if_modified_since
        # TODO: fix 304 behaviour, does not work yet! header problem?
        if if_modified and if_modified >= timestamp:
            request.status_code = 304
        else:
            self._do_get_modified(timestamp)

    def _do_get_modified(self, timestamp):
        request = self.request
        from_cache = request.values.get('from_cache')
        from_tar = request.values.get('from_tar')
        self._do_get(timestamp, from_cache, from_tar)

    def _do_get(self, timestamp, from_cache=None, from_tar=None):
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
            # TODO: make it work, file access to storage items?
            filename = wikiutil.taintfilename(from_tar)
            mt = wikiutil.MimeType(filename=filename)
            content_disposition = mt.content_disposition(request.cfg)
            content_type = mt.content_type()
            content_length = os.path.getsize(fpath) # XXX
            ci = ContainerItem(request, self.item_name)
            file_to_send = ci.get(filename)
        else: # content = item revision
            rev = self.rev
            try:
                mimestr = rev["mimetype"]
            except KeyError:
                mimestr = mimetypes.guess_type(rev.item.name)[0]
            mt = wikiutil.MimeType(mimestr=mimestr)
            content_disposition = mt.content_disposition(request.cfg)
            content_type = mt.content_type()
            content_length = rev.size
            file_to_send = rev

        self._send(content_type, content_length, timestamp, file_to_send,
                   content_disposition=content_disposition)

    def _send(self, content_type, content_length, timestamp, file_to_send,
              filename=None, content_disposition=None, timeout=24*3600):
        request = self.request
        request.headers.add('Cache-Control', 'max-age=%d, public' % timeout)
        now = time.time()
        request.headers.add('Expires', http_date(now + timeout))

        # XXX choose:
        request.last_modified = timestamp
        request.headers.add('Last-Modified', http_date(timestamp))

        if content_disposition is not None:
            request.headers.add('Content-Disposition', content_disposition)
        
        request.status_code = 200
        request.content_type = content_type
        request.content_length = content_length
        request.send_file(file_to_send)


class Image(Binary):
    supported_mimetypes = ['image/']

    def _render_data(self):
        return '<img src="?do=get&rev=%d">' % self.rev.revno


class TransformableImage(Image):
    supported_mimetypes = ['image/png', 'image/jpeg', 'image/gif', ]

    def _render_data(self):
        return '<img src="?do=get&rev=%d">' % self.rev.revno

    def _transform(self, content_type, size=None, transpose_op=None):
        """ resize to new size (optional), transpose according to exif infos,
            return data as content_type (default: same ct as original image)
        """
        try:
            from PIL import Image as PILImage
        except ImportError:
            # no PIL, we can't do anything
            return self.rev.read()

        if content_type == 'image/jpeg':
            output_type = 'JPEG'
        elif content_type == 'image/png':
            output_type = 'PNG'
        elif content_type == 'image/gif':
            output_type = 'GIF'
        else:
            raise ValueError("content_type %r not supported" % content_type)

        #image = PILImage.open(self.rev) # XXX needs: read() seek() tell()
        buf = StringIO(self.rev.read())
        image = PILImage.open(buf)
        image.load()
        buf.close()

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

        buf = StringIO()
        image.save(buf, output_type)
        buf.flush() # XXX needed?
        data = buf.getvalue()
        buf.close()
        return data

    def _do_get_modified(self, timestamp):
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
            cache_meta = [ # we use a list to have order stability
                ('wikiname', request.cfg.interwikiname or request.cfg.siteid),
                ('itemname', self.item_name),
                ('revision', self.rev.revno),
                # XXX even better than wikiname/itemname/revision would be a content hash!
                ('width', width),
                ('height', height),
                ('transpose', transpose),
            ]
            cache = SendCache.from_meta(request, cache_meta)
            if not cache.exists():
                content_type = self.rev['mimetype']
                size = (width or 99999, height or 99999)
                transformed_image = self._transform(content_type, size=size, transpose_op=transpose)
                cache.put(transformed_image, content_type=content_type)
            from_cache = cache.key
        else:
            from_cache = request.values.get('from_cache')
        self._do_get(timestamp, from_cache=from_cache)


class SvgImage(Binary):
    supported_mimetypes = ['image/svg+xml']

    def _render_data(self):
        return """
            <object data="?do=get&rev=%d" type="image/svg+xml">
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

    def _render_data_diff(self, oldrev, newrev):
        from MoinMoin.util import diff_html
        return diff_html.diff(self.request, oldrev.read(), newrev.read())

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

class HTML(MoinParserSupported):
    supported_mimetypes = ['text/html']
    format = 'html'
    format_args = ''

class DiffPatch(MoinParserSupported):
    supported_mimetypes = ['text/x-diff']
    format = 'highlight'
    format_args = 'diff'

class IRCLog(MoinParserSupported):
    supported_mimetypes = ['text/x-irclog']
    format = 'highlight'
    format_args = 'irc'

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

