# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - misc. mimetype items

    While MoinMoin.storage cares for backend storage of items,
    this module cares for more high-level, frontend items,
    e.g. showing, editing, etc. of wiki items.

    @copyright: 2009 MoinMoin:ThomasWaldmann,
                2009 MoinMoin:ReimarBauer,
                2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import os, time, datetime, shutil
from StringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

from werkzeug import http_date, quote_etag

from MoinMoin import wikiutil, config, user
from MoinMoin.util import timefuncs
from MoinMoin.support.python_compatibility import hash_new
from MoinMoin.Page import Page
from MoinMoin.Page import DELETED, EDIT_LOG_ADDR, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, \
                          EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_ACTION
from MoinMoin.storage.error import NoSuchItemError, NoSuchRevisionError

from MoinMoin.items.sendcache import SendCache


class Item(object):

    def __init__(self, request, item_name, rev=None, mimetype=None, formatter=None):
        self.request = request
        self.env = request.theme.env
        self.item_name = item_name
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
        return href(self.item_name, **kw)

    def rev_url(self, _absolute=False, **kw):
        """ return URL for this item and this revision, optionally as absolute URL """
        return self.url(rev=self.rev.revno, _absolute=_absolute, **kw)

    transclude_acceptable_attrs = []

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self.formatter.text('(Item %s (%s): transclusion not implemented)' % (self.item_name, self.mimetype))

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
            logging.error("unsupported content object: %r" % content)
            raise
        return hash_name, hash.hexdigest()

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
        oldname = self.item_name
        newname = self.request.form.get('target')
        self.rev.item.rename(newname)
        # we just create a new revision with almost same meta/data to show up on RC
        # XXX any better way to do this?
        self._save(self.meta, self.data, item_name=newname, action='SAVE/RENAME', extra=oldname, comment=comment)

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
        for k, v in meta.iteritems():
            # TODO Put metadata into newrev here for now. There should be a safer way
            #      of input for this.
            newrev[k] = v
        hash_name, hash_hexdigest = self._write_stream(data, newrev)
        newrev[hash_name] = hash_hexdigest
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
    supported_mimetypes = ['application/x-unknown']
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
        template = self.env.get_template('show_nonexistent.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.item_name,
                                  template_groups=self.template_groups,
                                  mimetype_groups=self.mimetype_groups, )
        return content

    def do_get(self):
        self.request.status_code = 404

    transclude_acceptable_attrs = []
    def transclude(self, desc, tag_attrs=None, query_args=None):
        return (self.formatter.url(1, self.url(), css='nonexistent', title='click to create item') +
                self.formatter.text(self.item_name) + # maybe use some "broken image" icon instead?
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
            return self.rev.read_data()
        else:
            return ''
    data = property(fget=get_data)

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

        self._send(content_type, content_length, hash, file_to_send,
                   content_disposition=content_disposition)

    def _send(self, content_type, content_length, hash, file_to_send,
              filename=None, content_disposition=None):
        request = self.request
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
        return self.transclude('{{%s [%s]}}' % (self.item_name, self.mimetype))


class PlayableBinary(RenderableBinary):
    """ This is a base class for some binary stuff that plays with a object tag. """
    transclude_params = [
        dict(name='stop', value='1', valuetype='data'),
        dict(name='play', value='0', valuetype='data'),
        dict(name='autoplay', value='0', valuetype='data'),
    ]


class Application(Binary):
    supported_mimetypes = []


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
        return self.transclude(self.item_name)


class TransformableBitmapImage(RenderableBitmapImage):
    """ We can transform (resize, rotate, mirror) some image types """
    supported_mimetypes = ['image/png', 'image/jpeg', 'image/gif', ]

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
                content_type = self.rev['mimetype']
                size = (width or 99999, height or 99999)
                transformed_image = self._transform(content_type, size=size, transpose_op=transpose)
                cache.put(transformed_image, content_type=content_type)
            from_cache = cache.key
        else:
            from_cache = request.values.get('from_cache')
        self._do_get(hash, from_cache=from_cache)


class Text(Binary):
    """ Any kind of text """
    supported_mimetypes = ['text/']

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

    def transclude(self, desc, tag_attrs=None, query_args=None):
        return self._render_data()

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
    """ Base class for text formats that are supported by some moin parser """
    supported_mimetypes = []
    format = 'wiki' # override this, if needed
    format_args = ''
    def _render_data(self):
        # TODO: switch from Page to Item subclass
        request = self.request
        page = Page(request, self.item_name)
        pi, body = page.pi, page.data
        self.formatter.setPage(page)
        #lang = pi.get('language', request.cfg.language_default)
        #request.setContentLanguage(lang)
        Parser = wikiutil.searchAndImportPlugin(request.cfg, "parser", self.format)
        parser = Parser(body, request, format_args=self.format_args)
        buffer = StringIO()
        request.redirect(buffer)
        parser.format(self.formatter)
        content = buffer.getvalue()
        request.redirect()
        del buffer
        return content


class MoinWiki(MoinParserSupported):
    """ MoinMoin wiki markup """
    supported_mimetypes = ['text/x-unidentified-wiki-format',
                           'text/moin-wiki',
                          ]  # XXX Improve mimetype handling
    format = 'wiki'
    format_args = ''


class CreoleWiki(MoinParserSupported):
    """ Creole wiki markup """
    supported_mimetypes = ['text/creole-wiki']
    format = 'creole'
    format_args = ''


class CSV(MoinParserSupported):
    """ Comma Separated Values format """
    supported_mimetypes = ['text/csv']
    format = 'csv'
    format_args = ''


class HTML(MoinParserSupported):
    """ HTML markup """
    supported_mimetypes = ['text/html']
    format = 'html'
    format_args = ''


class DiffPatch(MoinParserSupported):
    """ diff output / patch input format """
    supported_mimetypes = ['text/x-diff']
    format = 'highlight'
    format_args = 'diff'


class IRCLog(MoinParserSupported):
    """ Internet Relay Chat Log """
    supported_mimetypes = ['text/x-irclog']
    format = 'highlight'
    format_args = 'irc'


class PythonSrc(MoinParserSupported):
    """ Python source code """
    supported_mimetypes = ['text/x-python']
    format = 'highlight'
    format_args = 'python'


class Manager(object):

    def __init__(self, request, item_name, mimetype='application/x-unknown', rev_no=-1, formatter=None):
        self.request = request
        self.item_name = item_name
        self.item_mimetype = mimetype
        self.rev_no = rev_no
        self.formatter = formatter

    def _find_item_class(self, mimetype, BaseClass=Item, best_match_len=-1):
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
            best_match_len, better_Class = self._find_item_class(mimetype, ItemClass, best_match_len)
            if better_Class:
                Class = better_Class
        return best_match_len, Class

    def get_item(self):
        request = self.request
        try:
            item = request.cfg.data_backend.get_item(self.item_name)
        except NoSuchItemError:
            class DummyRev(dict):
                def __init__(self, mimetype):
                    self['mimetype'] = mimetype
                def read_data(self):
                    return ''
            rev = DummyRev(self.item_mimetype)
        else:
            try:
                rev = item.get_revision(self.rev_no)
            except NoSuchRevisionError:
                rev = item.get_revision(-1) # fall back to current revision
                # XXX add some message about invalid revision
        mimetype = rev.get("mimetype") or 'application/x-unknown' # XXX why do we need ... or ..?
        ItemClass = self._find_item_class(mimetype)[1]
        logging.debug("ItemClass %r handles %r" % (ItemClass, mimetype))
        return ItemClass(request, item_name=self.item_name, rev=rev, mimetype=mimetype, formatter=self.formatter)

