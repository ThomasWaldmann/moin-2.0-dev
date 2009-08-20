# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - twikidraw related stuff

    UNFINISHED, does not work, see some related code in __init__.py

    @copyright: 2009 MoinMoin:ThomasWaldmann,
    @license: GNU GPL, see COPYING for details.
"""

import os, time, datetime
from StringIO import StringIO

from MoinMoin import log
logging = log.getLogger(__name__)

# keep both imports below as they are, order is important:
from MoinMoin import wikiutil
import mimetypes

from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.search.term import AND, NOT, NameRE, LastRevisionMetaDataMatch
from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.items import MIMETYPE, \
                           EDIT_LOG_ACTION, EDIT_LOG_HOSTNAME, \
                           EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT
from MoinMoin.support import tarfile

action_name = __name__.split('.')[-1]

from MoinMoin.items import Image

class TwikiDraw(Image):
    twd_mimetype = 'application/x-twikidraw'
    supported_mimetypes = [twd_mimetype]
    modify_help = ""

    def do_modify(self):
        request = self.request
        item_name = self.name
        ci = ContainerItem(request, item_name)
        base_name = item_name.replace('.tdraw', '')
        twd_params = {
            'pubpath': request.cfg.url_prefix_static + "/applets/TWikiDrawPlugin",
            'pngpath': ci.member_url(base_name + '.png'),
            'drawpath': ci.member_url(base_name + '.draw'),
            'savelink': request.href(item_name, action='modify', mimetype=self.twd_mimetype),
            'pagelink': request.href(item_name, action=action_name),
            'helplink': '',
            'basename': wikiutil.escape(basename, 1),
        }

        template = self.env.get_template('modify_twikidraw.html')
        content = template.render(gettext=self.request.getText,
                                  item_name=self.name,
                                  revno=0,
                                  meta_text=self.meta_dict_to_text(self.meta),
                                  help=self.modify_help,
                                  t=twd_params,
                                 )
        return content

    def save(self):
        request = self.request
        item_name = self.name

        file_upload = request.files.get('filepath')
        filename = request.form['filename']
        basepath, basename = os.path.split(filename)
        basename, ext = os.path.splitext(basename)

        ci = ContainerItem(request, item_name)
        filecontent = file_upload.stream
        content_length = None
        if ext == '.draw': # TWikiDraw POSTs this first
            ci.truncate()
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.replace("\r", "")
        elif ext == '.map':
            # touch attachment directory to invalidate cache if new map is saved
            filecontent = filecontent.read() # read file completely into memory
            filecontent = filecontent.strip()
        else:
            #content_length = file_upload.content_length
            # XXX gives -1 for wsgiref :( If this is fixed, we could use the file obj,
            # without reading it into memory completely:
            filecontent = filecontent.read()

        ci.put(basename + ext, filecontent, content_length)

        request.write("OK")

        if last_POST: # after all 3 POSTs were done ...
            meta = {} # TODO how to handle metadata edits?
            data = '' # TODO get data from container item
            backend = request.storage
            try:
                storage_item = backend.get_item(item_name)
                rev_no = storage_item.list_revisions()[-1]
            except NoSuchItemError:
                storage_item = backend.create_item(item_name)
                rev_no = -1
            newrev = storage_item.create_revision(rev_no + 1)
            newrev.write(data)
            timestamp = time.time()
            newrev[EDIT_LOG_COMMENT] = ''
            newrev[MIMETYPE] = self.twd_mimetype
            newrev[EDIT_LOG_ACTION] = 'SAVE'
            newrev[EDIT_LOG_ADDR] = request.remote_addr
            newrev[EDIT_LOG_HOSTNAME] = wikiutil.get_hostname(request, request.remote_addr)
            newrev[EDIT_LOG_USERID] = request.user.valid and request.user.id or ''
            newrev[EDIT_LOG_EXTRA] = ''
            storage_item.commit()

    def _render_data(self):
        request = self.request
        item_name = self.name
        ci = ContainerItem(request, item_name)
        return '<img src="%s">' % ci.member_url(item_name.replace('.tdraw', '.png'))


class ContainerItem:
    """ A storage container (multiple objects in 1 tarfile) """
    # TODO: modify for storage backend / mimetype items
    # currently uses old pagename/filename combo as in AttachFile
    def __init__(self, request, item_name):
        self.request = request
        self.name = item_name
        self.container_filename = '' # TODO how to handle?

    def member_url(self, member):
        """ return URL for accessing container member
            (we use same URL for get (GET) and put (POST))
        """
        url = Item(self.request, self.name).url({
            'action': 'box', #'from_tar': member,
        })
        return url + '&from_tar=%s' % member
        # member needs to be last in qs because twikidraw looks for "file extension" at the end

    def get(self, member):
        """ return a file-like object with the member file data
        """
        tf = tarfile.TarFile(self.container_filename)
        return tf.extractfile(member)

    def put(self, member, content, content_length=None):
        """ save data into a container's member """
        tf = tarfile.TarFile(self.container_filename, mode='a')
        if isinstance(member, unicode):
            member = member.encode('utf-8')
        ti = tarfile.TarInfo(member)
        if isinstance(content, str):
            if content_length is None:
                content_length = len(content)
            content = StringIO(content) # we need a file obj
        elif not hasattr(content, 'read'):
            logging.error("unsupported content object: %r" % content)
            raise
        assert content_length >= 0  # we don't want -1 interpreted as 4G-1
        ti.size = content_length
        tf.addfile(ti, content)
        tf.close()

    def truncate(self):
        f = open(self.container_filename, 'w')
        f.close()

    def exists(self):
        return os.path.exists(self.container_filename)

############ some old code from formatter #################
    def attachment_drawing(self, url, text, **kw):
        # XXX text arg is unused!
        _ = self.request.getText
        pagename, drawing = AttachFile.absoluteName(url, self.page.page_name)
        containername = wikiutil.taintfilename(drawing) + ".tdraw"

        drawing_url = AttachFile.getAttachUrl(pagename, containername, self.request, drawing=drawing, upload=True)
        ci = AttachFile.ContainerItem(self.request, pagename, containername)
        if not ci.exists():
            title = _('Create new drawing "%(filename)s (opens in new window)"') % {'filename': drawing}
            img = self.icon('attachimg')  # TODO: we need a new "drawimg" in similar grey style and size
            css = 'nonexistent'
            return self.url(1, drawing_url, css=css, title=title) + img + self.url(0)

        title = _('Edit drawing %(filename)s (opens in new window)') % {'filename': self.text(drawing)}
        kw['src'] = src = ci.member_url(drawing + u'.png')
        kw['css'] = 'drawing'

        mapfile = ci.get(drawing + u'.map')
        try:
            map = mapfile.read()
            mapfile.close()
        except (IOError, OSError):
            map = ''
        if map:
            # we have a image map. inline it and add a map ref to the img tag
            mapid = 'ImageMapOf' + drawing
            map = map.replace('%MAPNAME%', mapid)
            # add alt and title tags to areas
            map = re.sub(r'href\s*=\s*"((?!%TWIKIDRAW%).+?)"', r'href="\1" alt="\1" title="\1"', map)
            map = map.replace('%TWIKIDRAW%"', '%s" alt="%s" title="%s"' % (drawing_url, title, title))
            # unxml, because 4.01 concrete will not validate />
            map = map.replace('/>', '>')
            title = _('Clickable drawing: %(filename)s') % {'filename': self.text(drawing)}
            if 'title' not in kw:
                kw['title'] = title
            if 'alt' not in kw:
                kw['alt'] = kw['title']
            kw['usemap'] = '#'+mapid
            return map + self.image(**kw)
        else:
            if 'title' not in kw:
                kw['title'] = title
            if 'alt' not in kw:
                kw['alt'] = kw['title']
            return self.url(1, drawing_url) + self.image(**kw) + self.url(0)

