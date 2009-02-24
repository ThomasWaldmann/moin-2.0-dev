# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - AttachFile action

    This action lets a page have multiple attachment files.
    It creates a folder <data>/pages/<pagename>/attachments
    and keeps everything in there.

    Form values: action=Attachment
    1. with no 'do' key: returns file upload form
    2. do=attach: accept file upload and saves the file in
       ../attachment/pagename/
    3. /pagename/fname?action=Attachment&do=get[&mimetype=type]:
       return contents of the attachment file with the name fname.
    4. /pathname/fname, do=view[&mimetype=type]:create a page
       to view the content of the file

    To link to an attachment, use [[attachment:file.txt]],
    to embed an attachment, use {{attachment:file.png}}.

    @copyright: 2001 by Ken Sugino (sugino@mediaone.net),
                2001-2004 by Juergen Hermann <jh@web.de>,
                2005 MoinMoin:AlexanderSchremmer,
                2005 DiegoOngaro at ETSZONE (diego@etszone.com),
                2005-2007 MoinMoin:ReimarBauer,
                2007-2008 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import os, time, zipfile, mimetypes, errno

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import config, wikiutil, packages
from MoinMoin.Page import Page
from MoinMoin.util import filesys, timefuncs
from MoinMoin.security.textcha import TextCha
from MoinMoin.events import FileAttachedEvent, send_event
from MoinMoin.search.term import AND, NOT, NameRE, LastRevisionMetaDataMatch
from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError, NoSuchRevisionError
from MoinMoin.Page import EDIT_LOG_ACTION, EDIT_LOG_HOSTNAME, \
                          EDIT_LOG_USERID, EDIT_LOG_EXTRA, EDIT_LOG_COMMENT, DELETED

action_name = __name__.split('.')[-1]

#############################################################################
### External interface - these are called from the core code
#############################################################################

class AttachmentAlreadyExists(Exception):
    pass


def getAttachDir(request, pagename, create=0):
    """ Get directory where attachments for page `pagename` are stored. """
    if request.page and pagename == request.page.page_name:
        page = request.page # reusing existing page obj is faster
    else:
        page = Page(request, pagename)
    return page.getPagePath("attachments", check_create=create)


def absoluteName(url, pagename):
    """ Get (pagename, filename) of an attachment: link
        @param url: PageName/filename.ext or filename.ext (unicode)
        @param pagename: name of the currently processed page (unicode)
        @rtype: tuple of unicode
        @return: PageName, filename.ext
    """
    url = wikiutil.AbsPageName(pagename, url)
    pieces = url.split(u'/')
    if len(pieces) == 1:
        return pagename, pieces[0]
    else:
        return u"/".join(pieces[:-1]), pieces[-1]


def attachUrl(request, pagename, filename=None, **kw):
    # filename is not used yet, but should be used later to make a sub-item url
    if kw:
        qs = '?%s' % wikiutil.makeQueryString(kw, want_unicode=False)
    else:
        qs = ''
    return "%s/%s%s" % (request.getScriptname(), wikiutil.quoteWikinameURL(pagename), qs)


def getAttachUrl(pagename, filename, request, addts=0, escaped=0, do='get', drawing='', upload=False):
    """ Get URL that points to attachment `filename` of page `pagename`. """
    if upload:
        if not drawing:
            url = attachUrl(request, pagename, filename,
                            rename=wikiutil.taintfilename(filename), action=action_name)
        else:
            url = attachUrl(request, pagename, filename,
                            rename=wikiutil.taintfilename(filename), drawing=drawing, action=action_name)
    else:
        if not drawing:
            url = attachUrl(request, pagename, filename,
                            target=filename, action=action_name, do=do)
        else:
            url = attachUrl(request, pagename, filename,
                            drawing=drawing, action=action_name)
    if escaped:
        url = wikiutil.escape(url)
    return url


def getFilename(request, pagename, filename):
    """ make complete pathfilename of file "name" attached to some page "pagename"
        @param request: request object
        @param pagename: name of page where the file is attached to (unicode)
        @param filename: filename of attached file (unicode)
        @rtype: string (in config.charset encoding)
        @return: complete path/filename of attached file
    """
    if isinstance(filename, unicode):
        filename = filename.encode(config.charset)
    return os.path.join(getAttachDir(request, pagename, create=1), filename)


def exists(request, pagename, filename):
    """ check if page <pagename> has a file <filename> attached """
    try:
        item = request.cfg.data_backend.get_item(pagename + "/" + filename)
        rev = item.get_revision(-1)
        return True
    except (NoSuchItemError, NoSuchRevisionError):
        return False


def size(request, pagename, filename):
    """ return file size of file attachment """
    try:
        item = request.cfg.data_backend.get_item(pagename + "/" + filename)
        rev = item.get_revision(-1)
        return rev.size
    except (NoSuchItemError, NoSuchRevisionError):
        return None


def info(pagename, request):
    """ Generate snippet with info on the attachment for page `pagename`. """
    _ = request.getText

    attach_dir = getAttachDir(request, pagename)
    files = []
    if os.path.isdir(attach_dir):
        files = os.listdir(attach_dir)
    page = Page(request, pagename)
    link = page.url(request, {'action': action_name})
    attach_info = _('There are <a href="%(link)s">%(count)s attachment(s)</a> stored for this page.') % {
        'count': len(files),
        'link': wikiutil.escape(link)
        }
    return "\n<p>\n%s\n</p>\n" % attach_info

def _write_stream(content, new_rev, bufsize=8192):
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

def add_attachment(request, pagename, target, filecontent, overwrite=0):
    """ save <filecontent> to an attachment <target> of page <pagename>

        filecontent can be either a str (in memory file content),
        or an open file object (file content in e.g. a tempfile).
    """
    _ = request.getText

    # replace illegal chars
    assert isinstance(pagename, basestring)
    target = wikiutil.taintfilename(target)
    item_name = pagename + "/" + target  # pagenames are guaranteed to be unique in the backend,
                                         # but we want to allow equally named attachments to be
                                         # stored for different pages.
    backend = request.cfg.data_backend
    try:
        item = backend.create_item(item_name)
    except ItemAlreadyExistsError:
        try:
            item = backend.get_item(item_name)
            rev = item.get_revision(-1)
            deleted = DELETED in rev
        except NoSuchRevisionError:
            deleted = True

        if overwrite or deleted:
            item = backend.get_item(item_name)
        else:
            raise AttachmentAlreadyExists

    try:
        current_revno = item.get_revision(-1).revno
        new_rev = item.create_revision(current_revno + 1)
    except NoSuchRevisionError:
        new_rev = item.create_revision(0)

    _write_stream(filecontent, new_rev)

    # XXX Intentionally leaving out some of the information the old _addLogEntry saved. Maybe add them later.
    new_rev[EDIT_LOG_ACTION] = 'ATTNEW'
    new_rev[EDIT_LOG_HOSTNAME] = wikiutil.get_hostname(request, request.remote_addr)
    new_rev[EDIT_LOG_USERID] = request.user.valid and request.user.id or ''
    new_rev[EDIT_LOG_EXTRA] = wikiutil.url_quote(target, want_unicode=True)
    new_rev[EDIT_LOG_COMMENT] = u''  # XXX At some point one may consider enabling attachment-comments

    mimetype = mimetypes.guess_type(target)[0]
    if mimetype is None:
        mimetype = "application/octet-stream"
    new_rev["mimetype"] = mimetype

    try:
        item.commit()
    except ItemAlreadyExistsError:
        raise AttachmentAlreadyExists

    event = FileAttachedEvent(request, pagename, target, new_rev.size)
    send_event(event)

    return target, new_rev.size


#############################################################################
### Internal helpers
#############################################################################

def _addLogEntry(request, action, pagename, filename, uid_override=None):
    """ Add an entry to the edit log on uploads and deletes.

        `action` should be "ATTNEW" or "ATTDEL"
    """
    logging.debug("DEPRECATION WARNING: Some code is still using _addLogEntry in action/AttachFile.py!")


def _access_file(pagename, request):
    """ Check form parameter `target` and return a tuple of
        `(pagename, filename, filepath)` for an existing attachment.

        Return `(pagename, None, None)` if an error occurs.
    """
    _ = request.getText

    error = None
    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form['target'][0])
        fpath = getFilename(request, pagename, filename)

        if os.path.isfile(fpath):
            return (pagename, filename, fpath)
        error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}

    error_msg(pagename, request, error)
    return (pagename, None, None)


def _build_filelist(request, pagename, showheader, readonly, mime_type='*'):
    _ = request.getText
    fmt = request.html_formatter

    files = _get_files(request, pagename)

    if mime_type != '*':
        files = [fname for fname in files if mime_type == mimetypes.guess_type(fname)[0]]

    html = []
    if files:
        if showheader:
            html.append(fmt.rawHTML(_(
                "To refer to attachments on a page, use '''{{{attachment:filename}}}''', \n"
                "as shown below in the list of files. \n"
                "Do '''NOT''' use the URL of the {{{[get]}}} link, \n"
                "since this is subject to change and can break easily.",
                wiki=True
            )))

        label_del = _("del")
        label_move = _("move")
        label_get = _("get")
        label_edit = _("edit")
        label_view = _("view")
        label_unzip = _("unzip")
        label_install = _("install")

        html.append(fmt.bullet_list(1))
        for file in files:
            mt = wikiutil.MimeType(filename=file)
            backend = request.cfg.data_backend
            try:
                item = backend.get_item(pagename + "/" + file)
                rev = item.get_revision(-1)
            except (NoSuchItemError, NoSuchRevisionError):
                # The file may have been renamed in the interim. Just don't show it then.
                continue

            try:
                fmtime = request.user.getFormattedDateTime(float(rev.timestamp))
            except KeyError:
                fmtime = "unknown"

            base, ext = os.path.splitext(file)
            parmdict = {'file': wikiutil.escape(file),
                        'fsize': "%.1f" % (float(rev.size) / 1024),
                        'fmtime': fmtime,
                       }

            links = []
            may_delete = request.user.may.delete(pagename)
            if may_delete and not readonly:
                links.append(fmt.url(1, getAttachUrl(pagename, file, request, do='del')) +
                             fmt.text(label_del) +
                             fmt.url(0))

                links.append(fmt.url(1, getAttachUrl(pagename, file, request, do='move')) +
                             fmt.text(label_move) +
                             fmt.url(0))

            links.append(fmt.url(1, getAttachUrl(pagename, file, request)) +
                         fmt.text(label_get) +
                         fmt.url(0))

            if ext == '.draw':
                links.append(fmt.url(1, getAttachUrl(pagename, file, request, drawing=base)) +
                             fmt.text(label_edit) +
                             fmt.url(0))
            else:
                links.append(fmt.url(1, getAttachUrl(pagename, file, request, do='view')) +
                             fmt.text(label_view) +
                             fmt.url(0))

           ## TODO: Adjust this zipfile-related stuff
           # try:
           #     is_zipfile = zipfile.is_zipfile(fullpath)
           #     if is_zipfile:
           #         is_package = packages.ZipPackage(request, fullpath).isPackage()
           #         if is_package and request.user.isSuperUser():
           #             links.append(fmt.url(1, getAttachUrl(pagename, file, request, do='install')) +
           #                          fmt.text(label_install) +
           #                          fmt.url(0))
           #         elif (not is_package and mt.minor == 'zip' and
           #               may_delete and
           #               request.user.may.read(pagename) and
           #               request.user.may.write(pagename)):
           #             links.append(fmt.url(1, getAttachUrl(pagename, file, request, do='unzip')) +
           #                          fmt.text(label_unzip) +
           #                          fmt.url(0))
           # except RuntimeError:
           #     # We don't want to crash with a traceback here (an exception
           #     # here could be caused by an uploaded defective zip file - and
           #     # if we crash here, the user does not get a UI to remove the
           #     # defective zip file again).
           #     # RuntimeError is raised by zipfile stdlib module in case of
           #     # problems (like inconsistent slash and backslash usage in the
           #     # archive).
           #     logging.exception("An exception within zip file attachment handling occurred:")

            html.append(fmt.listitem(1))
            html.append("[%s]" % "&nbsp;| ".join(links))
            html.append(" (%(fmtime)s, %(fsize)s KB) [[attachment:%(file)s]]" % parmdict)
            html.append(fmt.listitem(0))
        html.append(fmt.bullet_list(0))

    else:
        if showheader:
            html.append(fmt.paragraph(1))
            html.append(fmt.text(_("No attachments stored for %(pagename)s") % {
                                   'pagename': pagename}))
            html.append(fmt.paragraph(0))

    return ''.join(html)


def _get_files(request, pagename):
    # MoinMoin.search.NameRE expects a Regular Expression Object.
    # Find all items that are attached to $pagename. (Indicated by their
    # Item-Name (in storage-backend) being constructed like: pagename + "/" + filename
    import re
    regex = re.compile('^%s/.*' % (pagename, ))
    backend = request.cfg.data_backend

    # Get a list of all items (of the page matching the regex) whose latest revision
    # has a metadata-key 'mimetype' indicating that it is NOT a regular moin-page
    items = list(backend.search_item(AND(NameRE(regex),
                                     NOT(LastRevisionMetaDataMatch('mimetype', 'text/x-unidentified-wiki-format')),
                                     NOT(LastRevisionMetaDataMatch('deleted', True)))))

    # We only want the names of the items, not the whole item.
    item_names = [item.name for item in items]

    # We only want the filename, not the whole item_name.
    return [f.split("/")[1] for f in item_names]


def _get_filelist(request, pagename):
    return _build_filelist(request, pagename, 1, 0)


def error_msg(pagename, request, msg):
    request.theme.add_msg(msg, "error")
    Page(request, pagename).send_page()


#############################################################################
### Create parts of the Web interface
#############################################################################

def send_link_rel(request, pagename):
    # XXX the need for this stuff is questionable
    # and soon we won't have attachments any more, so we don't need it anyway
    files = _get_files(request, pagename)
    for fname in files:
        url = getAttachUrl(pagename, fname, request, do='view', escaped=1)
        request.write(u'<link rel="Appendix" title="%s" href="%s">\n' % (
                      wikiutil.escape(fname, 1), url))


def send_hotdraw(pagename, request):
    _ = request.getText

    now = time.time()
    pubpath = request.cfg.url_prefix_static + "/applets/TWikiDrawPlugin"
    basename = request.form['drawing'][0]
    drawpath = getAttachUrl(pagename, basename + '.draw', request, escaped=1)
    pngpath = getAttachUrl(pagename, basename + '.png', request, escaped=1)
    pagelink = attachUrl(request, pagename, '', action=action_name, ts=now)
    helplink = Page(request, "HelpOnActions/AttachFile").url(request)
    savelink = attachUrl(request, pagename, '', action=action_name, do='savedrawing')
    #savelink = Page(request, pagename).url(request) # XXX include target filename param here for twisted
                                           # request, {'savename': request.form['drawing'][0]+'.draw'}
    #savelink = '/cgi-bin/dumpform.bat'

    timestamp = '&amp;ts=%s' % now

    request.write('<h2>' + _("Edit drawing") + '</h2>')
    request.write("""
<p>
<img src="%(pngpath)s%(timestamp)s">
<applet code="CH.ifa.draw.twiki.TWikiDraw.class"
        archive="%(pubpath)s/twikidraw.jar" width="640" height="480">
<param name="drawpath" value="%(drawpath)s">
<param name="pngpath"  value="%(pngpath)s">
<param name="savepath" value="%(savelink)s">
<param name="basename" value="%(basename)s">
<param name="viewpath" value="%(pagelink)s">
<param name="helppath" value="%(helplink)s">
<strong>NOTE:</strong> You need a Java enabled browser to edit the drawing example.
</applet>
</p>""" % {
    'pngpath': pngpath, 'timestamp': timestamp,
    'pubpath': pubpath, 'drawpath': drawpath,
    'savelink': savelink, 'pagelink': pagelink, 'helplink': helplink,
    'basename': wikiutil.escape(basename, 1),
})


def send_uploadform(pagename, request):
    """ Send the HTML code for the list of already stored attachments and
        the file upload form.
    """
    _ = request.getText

    if not request.user.may.read(pagename):
        request.write('<p>%s</p>' % _('You are not allowed to view this page.'))
        return

    writeable = request.user.may.write(pagename)

    # First send out the upload new attachment form on top of everything else.
    # This avoids usability issues if you have to scroll down a lot to upload
    # a new file when the page already has lots of attachments:
    if writeable:
        request.write('<h2>' + _("New Attachment") + '</h2>')
        request.write("""
<form action="%(baseurl)s/%(pagename)s" method="POST" enctype="multipart/form-data">
<dl>
<dt>%(upload_label_file)s</dt>
<dd><input type="file" name="file" size="50"></dd>
<dt>%(upload_label_rename)s</dt>
<dd><input type="text" name="rename" size="50" value="%(rename)s"></dd>
<dt>%(upload_label_overwrite)s</dt>
<dd><input type="checkbox" name="overwrite" value="1" %(overwrite_checked)s></dd>
</dl>
%(textcha)s
<p>
<input type="hidden" name="action" value="%(action_name)s">
<input type="hidden" name="do" value="upload">
<input type="submit" value="%(upload_button)s">
</p>
</form>
""" % {
    'baseurl': request.getScriptname(),
    'pagename': wikiutil.quoteWikinameURL(pagename),
    'action_name': action_name,
    'upload_label_file': _('File to upload'),
    'upload_label_rename': _('Rename to'),
    'rename': wikiutil.escape(request.form.get('rename', [''])[0], 1),
    'upload_label_overwrite': _('Overwrite existing attachment of same name'),
    'overwrite_checked': ('', 'checked')[request.form.get('overwrite', ['0'])[0] == '1'],
    'upload_button': _('Upload'),
    'textcha': TextCha(request).render(),
})

    request.write('<h2>' + _("Attached Files") + '</h2>')
    request.write(_get_filelist(request, pagename))

    if not writeable:
        request.write('<p>%s</p>' % _('You are not allowed to attach a file to this page.'))

    if writeable and request.form.get('drawing', [None])[0]:
        send_hotdraw(pagename, request)


#############################################################################
### Web interface for file upload, viewing and deletion
#############################################################################

def execute(pagename, request):
    """ Main dispatcher for the 'AttachFile' action. """
    _ = request.getText

    do = request.form.get('do', ['upload_form'])
    handler = globals().get('_do_%s' % do[0])
    if handler:
        filename = request.form.get('target', None)
        if filename:
            filename = wikiutil.taintfilename(filename[0])
        msg = handler(pagename, request, filename=filename)
    else:
        msg = _('Unsupported AttachFile sub-action: %s') % (wikiutil.escape(do[0]), )
    if msg:
        error_msg(pagename, request, msg)


def _do_upload_form(pagename, request, filename):
    upload_form(pagename, request)


def upload_form(pagename, request, msg=''):
    _ = request.getText

    request.emit_http_headers()
    # Use user interface language for this generated page
    request.setContentLanguage(request.lang)
    request.theme.add_msg(msg, "dialog")
    request.theme.send_title(_('Attachments for "%(pagename)s"') % {'pagename': pagename}, pagename=pagename)
    request.write('<div id="content">\n') # start content div
    send_uploadform(pagename, request)
    request.write('</div>\n') # end content div
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()


def preprocess_filename(filename):
    """ preprocess the filename we got from upload form,
        strip leading drive and path (IE misbehaviour)
    """
    if filename and len(filename) > 1 and (filename[1] == ':' or filename[0] == '\\'): # C:.... or \path... or \\server\...
        bsindex = filename.rfind('\\')
        if bsindex >= 0:
            filename = filename[bsindex+1:]
    return filename


def _do_upload(pagename, request, filename):
    _ = request.getText
    # Currently we only check TextCha for upload (this is what spammers ususally do),
    # but it could be extended to more/all attachment write access
    if not TextCha(request).check_answer_from_form():
        return _('TextCha: Wrong answer! Go back and try again...')

    form = request.form
    overwrite = form.get('overwrite', [u'0'])[0]
    try:
        overwrite = int(overwrite)
    except:
        overwrite = 0

    if not request.user.may.write(pagename):
        return _('You are not allowed to attach a file to this page.')
    if overwrite and not request.user.may.delete(pagename):
        return _('You are not allowed to overwrite a file attachment of this page.')

    filename = form.get('file__filename__')
    if not filename:
        return _("Filename of attachment not specified!")
    rename = form.get('rename', [u''])[0].strip()
    if rename:
        target = rename
    else:
        target = filename

    target = preprocess_filename(target)
    target = wikiutil.clean_input(target)

    # get file content
    filecontent = request.form.get('file', [None])[0]
    if filecontent is None:
        # This might happen when trying to upload file names
        # with non-ascii characters on Safari.
        return _("No file content. Delete non ASCII characters from the file name and try again.")

    # add the attachment
    try:
        target, bytes = add_attachment(request, pagename, target, filecontent, overwrite=overwrite)
        msg = _("Attachment '%(target)s' (remote name '%(filename)s')"
                " with %(bytes)d bytes saved.") % {
                'target': target, 'filename': filename, 'bytes': bytes}
    except AttachmentAlreadyExists:
        msg = _("Attachment '%(target)s' (remote name '%(filename)s') already exists.") % {
            'target': target, 'filename': filename}

    # return attachment list
    upload_form(pagename, request, msg)


def _do_savedrawing(pagename, request, filename):
    _ = request.getText

    if not request.user.may.write(pagename):
        return _('You are not allowed to save a drawing on this page.')

    filename = request.form['filename'][0]
    filecontent = request.form['filepath'][0]

    basepath, basename = os.path.split(filename)
    basename, ext = os.path.splitext(basename)

    # get directory, and possibly create it
    attach_dir = getAttachDir(request, pagename, create=1)
    savepath = os.path.join(attach_dir, basename + ext)

    if ext == '.draw':
        _addLogEntry(request, 'ATTDRW', pagename, basename + ext)
        filecontent = filecontent.read() # read file completely into memory
        filecontent = filecontent.replace("\r", "")
    elif ext == '.map':
        filecontent = filecontent.read() # read file completely into memory
        filecontent = filecontent.strip()

    if filecontent:
        # filecontent is either a file or a non-empty string
        stream = open(savepath, 'wb')
        try:
            _write_stream(filecontent, stream)
        finally:
            stream.close()
    else:
        # filecontent is empty string (e.g. empty map file), delete the target file
        try:
            os.unlink(savepath)
        except OSError, err:
            if err.errno != errno.ENOENT: # no such file
                raise

    # touch attachment directory to invalidate cache if new map is saved
    if ext == '.map':
        os.utime(attach_dir, None)

    request.emit_http_headers()
    request.write("OK")


def _do_del(pagename, request, filename):
    """
    Deleting an Attachment basically means creating a new, empty revision
    on an Item that happened to be an 'Attachment' at some point, setting
    the DELETED-Metadata-Key.
    """
    _ = request.getText

    error = ""

    if not request.user.may.delete(pagename):
        return _('You are not allowed to delete attachments on this page.')
    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form['target'][0])

    backend = request.cfg.data_backend
    try:
        item = backend.get_item(pagename + "/" + filename)
        current_rev = item.get_revision(-1)
        current_revno = current_rev.revno
        new_rev = item.create_revision(current_revno + 1)
    except (NoSuchItemError, NoSuchRevisionError):
        error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}

    try:
        deleted = current_rev[DELETED]
    except KeyError:
        deleted = False

    if error != "":
        error_msg(pagename, request, error)
    elif not deleted:
        # Everything ok. "Delete" the attachment, i.e., create a new, empty revision with according metadata
        # XXX Intentionally leaving out some of the information the old _addLogEntry saved. Maybe add them later.
        new_rev[EDIT_LOG_ACTION] = 'ATTDEL'
        new_rev[EDIT_LOG_HOSTNAME] = wikiutil.get_hostname(request, request.remote_addr)
        new_rev[EDIT_LOG_USERID] = request.user.valid and request.user.id or ''
        new_rev[EDIT_LOG_EXTRA] = wikiutil.url_quote(filename, want_unicode=True)
        new_rev[EDIT_LOG_COMMENT] = u''  # XXX At some point one may consider enabling attachment-comments
        new_rev[DELETED] = True

        item.commit()

        if request.cfg.xapian_search:
            from MoinMoin.search.Xapian import Index
            index = Index(request)
            if index.exists:
                index.remove_item(pagename, filename)

        upload_form(pagename, request, msg=_("Attachment '%(filename)s' deleted.") % {'filename': filename})

    else:
        return _("Attachment '%(filename)s' does not exist!") % {'filename': filename}

def move_attachment(request, pagename, new_pagename, attachment, new_attachment):
    """
    In order to move an attachment, we simply rename the item to which the
    attachment (i.e. a revision) belongs.
    """
    _ = request.getText

    backend = request.cfg.data_backend
    try:
        item = backend.get_item(pagename + "/" + attachment)
        item.rename(new_pagename + "/" + new_attachment)
    except NoSuchItemError:
        return _("Attachment '%s' does not exist!" % attachment)
    except ItemAlreadyExistsError:
        upload_form(pagename, request,
            msg=_("Attachment '%(new_pagename)s/%(new_attachment)s' already exists.") % {
                'new_pagename': new_pagename,
                'new_attachment': new_attachment})
        return

    upload_form(pagename, request,
                msg=_("Attachment '%(pagename)s/%(filename)s' moved to '%(new_pagename)s/%(new_filename)s'.") % {
                      'pagename': pagename,
                      'filename': attachment,
                      'new_pagename': new_pagename,
                      'new_filename': new_attachment})

def _do_attachment_move(pagename, request, filename):
    _ = request.getText

    if 'cancel' in request.form:
        return _('Move aborted!')
    if not wikiutil.checkTicket(request, request.form['ticket'][0]):
        return _('Please use the interactive user interface to move attachments!')
    if not request.user.may.delete(pagename):
        return _('You are not allowed to move attachments from this page.')

    if 'newpagename' in request.form:
        new_pagename = request.form.get('newpagename')[0]
    else:
        upload_form(pagename, request, msg=_("Move aborted because new page name is empty."))
    if 'newattachmentname' in request.form:
        new_attachment = request.form.get('newattachmentname')[0]
        if new_attachment != wikiutil.taintfilename(new_attachment):
            upload_form(pagename, request, msg=_("Please use a valid filename for attachment '%(filename)s'.") % {
                                  'filename': new_attachment})
            return
    else:
        upload_form(pagename, request, msg=_("Move aborted because new attachment name is empty."))

    attachment = request.form.get('oldattachmentname')[0]
    move_attachment(request, pagename, new_pagename, attachment, new_attachment)

def _do_move(pagename, request, filename):
    _ = request.getText

    if not request.user.may.delete(pagename):
        return _('You are not allowed to move attachments from this page.')

    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form['target'][0])
        try:
            backend = request.cfg.data_backend
            item = backend.get_item(pagename + "/" + filename)
            # We need to check if there is a revision with data
            rev = item.get_revision(-1)
        except (NoSuchItemError, NoSuchRevisionError):
            error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}

        # move file
        d = {'action': action_name,
             'baseurl': request.getScriptname(),
             'do': 'attachment_move',
             'ticket': wikiutil.createTicket(request),
             'pagename': pagename,
             'pagename_quoted': wikiutil.quoteWikinameURL(pagename),
             'attachment_name': filename,
             'move': _('Move'),
             'cancel': _('Cancel'),
             'newname_label': _("New page name"),
             'attachment_label': _("New attachment name"),
            }
        formhtml = '''
    <form action="%(baseurl)s/%(pagename_quoted)s" method="POST">
    <input type="hidden" name="action" value="%(action)s">
    <input type="hidden" name="do" value="%(do)s">
    <input type="hidden" name="ticket" value="%(ticket)s">
    <table>
        <tr>
            <td class="label"><label>%(newname_label)s</label></td>
            <td class="content">
                <input type="text" name="newpagename" value="%(pagename)s" size="80">
            </td>
        </tr>
        <tr>
            <td class="label"><label>%(attachment_label)s</label></td>
            <td class="content">
                <input type="text" name="newattachmentname" value="%(attachment_name)s" size="80">
            </td>
        </tr>
        <tr>
            <td></td>
            <td class="buttons">
                <input type="hidden" name="oldattachmentname" value="%(attachment_name)s">
                <input type="submit" name="move" value="%(move)s">
                <input type="submit" name="cancel" value="%(cancel)s">
            </td>
        </tr>
    </table>
    </form>''' % d
        thispage = Page(request, pagename)
        request.theme.add_msg(formhtml, "dialog")
        return thispage.send_page()

def _do_get(pagename, request, filename):
    _ = request.getText

    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form['target'][0])
    if not request.user.may.read(pagename):
        return _('You are not allowed to get attachments from this page.')

    backend = request.cfg.data_backend
    try:
        item = backend.get_item(pagename + "/" + filename)
        rev = item.get_revision(-1)
    except (NoSuchItemError, NoSuchRevisionError):
        error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}
    else:
        timestamp = timefuncs.formathttpdate(float(rev.timestamp))  # Mandatory backend variable
        try:
            mimestr = rev["mimetype"]
        except KeyError:
            mimestr = mimetypes.guess_type(rev.item.name)[0]

        if request.if_modified_since == timestamp:
            request.emit_http_headers(["Status: 304 Not modified"])
        else:
            mt = wikiutil.MimeType(mimestr=mimestr)
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

            request.emit_http_headers([
                'Content-Type: %s' % content_type,
                'Last-Modified: %s' % timestamp,
                'Content-Length: %s' % rev.size,
                'Content-Disposition: %s; filename="%s"' % (content_dispo, filename_enc),
            ])

            # send data
            request.send_file(rev)

def _do_install(pagename, request, filename):
    _ = request.getText

    pagename, target, targetpath = _access_file(pagename, request)
    if not request.user.isSuperUser():
        return _('You are not allowed to install files.')
    if not target:
        return

    package = packages.ZipPackage(request, targetpath)

    if package.isPackage():
        if package.installPackage():
            msg = _("Attachment '%(filename)s' installed.") % {'filename': wikiutil.escape(target)}
        else:
            msg = _("Installation of '%(filename)s' failed.") % {'filename': wikiutil.escape(target)}
        if package.msg:
            msg += "<br><pre>%s</pre>" % wikiutil.escape(package.msg)
    else:
        msg = _('The file %s is not a MoinMoin package file.') % wikiutil.escape(target)

    upload_form(pagename, request, msg=msg)


def _do_unzip(pagename, request, filename, overwrite=False):
    _ = request.getText
    pagename, filename, fpath = _access_file(pagename, request)

    if not (request.user.may.delete(pagename) and request.user.may.read(pagename) and request.user.may.write(pagename)):
        return _('You are not allowed to unzip attachments of this page.')

    if not filename:
        return # error msg already sent in _access_file

    try:
        if not zipfile.is_zipfile(fpath):
            return _('The file %(filename)s is not a .zip file.') % {'filename': filename}

        # determine how which attachment names we have and how much space each is occupying
        curr_fsizes = dict([(f, size(request, pagename, f)) for f in _get_files(request, pagename)])

        # Checks for the existance of one common prefix path shared among
        # all files in the zip file. If this is the case, remove the common prefix.
        # We also prepare a dict of the new filenames->filesizes.
        zip_path_sep = '/'  # we assume '/' is as zip standard suggests
        fname_index = None
        mapping = []
        new_fsizes = {}
        zf = zipfile.ZipFile(fpath)
        for zi in zf.infolist():
            name = zi.filename
            if not name.endswith(zip_path_sep):  # a file (not a directory)
                if fname_index is None:
                    fname_index = name.rfind(zip_path_sep) + 1
                    path = name[:fname_index]
                if (name.rfind(zip_path_sep) + 1 != fname_index  # different prefix len
                    or
                    name[:fname_index] != path): # same len, but still different
                    mapping = []  # zip is not acceptable
                    break
                if zi.file_size >= request.cfg.unzip_single_file_size:  # file too big
                    mapping = []  # zip is not acceptable
                    break
                finalname = name[fname_index:]  # remove common path prefix
                finalname = finalname.decode(config.charset, 'replace')  # replaces trash with \uFFFD char
                mapping.append((name, finalname))
                new_fsizes[finalname] = zi.file_size

        # now we either have an empty mapping (if the zip is not acceptable),
        # an identity mapping (no subdirs in zip, just all flat), or
        # a mapping (origname, finalname) where origname is the zip member filename
        # (including some prefix path) and finalname is a simple filename.

        # calculate resulting total file size / count after unzipping:
        if overwrite:
            curr_fsizes.update(new_fsizes)
            total = curr_fsizes
        else:
            new_fsizes.update(curr_fsizes)
            total = new_fsizes
        total_count = len(total)
        total_size = sum(total.values())

        if not mapping:
            msg = _("Attachment '%(filename)s' not unzipped because some files in the zip "
                    "are either not in the same directory or exceeded the single file size limit (%(maxsize_file)d kB)."
                   ) % {'filename': filename,
                        'maxsize_file': request.cfg.unzip_single_file_size / 1000, }
        elif total_size > request.cfg.unzip_attachments_space:
            msg = _("Attachment '%(filename)s' not unzipped because it would have exceeded "
                    "the per page attachment storage size limit (%(size)d kB).") % {
                        'filename': filename,
                        'size': request.cfg.unzip_attachments_space / 1000, }
        elif total_count > request.cfg.unzip_attachments_count:
            msg = _("Attachment '%(filename)s' not unzipped because it would have exceeded "
                    "the per page attachment count limit (%(count)d).") % {
                        'filename': filename,
                        'count': request.cfg.unzip_attachments_count, }
        else:
            not_overwritten = []
            for origname, finalname in mapping:
                try:
                    # Note: reads complete zip member file into memory. ZipFile does not offer block-wise reading:
                    add_attachment(request, pagename, finalname, zf.read(origname), overwrite)
                except AttachmentAlreadyExists:
                    not_overwritten.append(finalname)
            if not_overwritten:
                msg = _("Attachment '%(filename)s' partially unzipped (did not overwrite: %(filelist)s).") % {
                        'filename': filename,
                        'filelist': ', '.join(not_overwritten), }
            else:
                msg = _("Attachment '%(filename)s' unzipped.") % {'filename': filename}
    except RuntimeError, err:
        # We don't want to crash with a traceback here (an exception
        # here could be caused by an uploaded defective zip file - and
        # if we crash here, the user does not get a UI to remove the
        # defective zip file again).
        # RuntimeError is raised by zipfile stdlib module in case of
        # problems (like inconsistent slash and backslash usage in the
        # archive).
        logging.exception("An exception within zip file attachment handling occurred:")
        msg = _("A severe error occurred:") + ' ' + str(err)

    upload_form(pagename, request, msg=wikiutil.escape(msg))


def send_viewfile(pagename, request, filename):
    _ = request.getText
    fmt = request.html_formatter

    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form['target'][0])
        fpath = getFilename(request, pagename, filename)

    request.write('<h2>' + _("Attachment '%(filename)s'") % {'filename': filename} + '</h2>')
    # show a download link above the content
    label = _('Download')
    link = (fmt.url(1, getAttachUrl(pagename, filename, request, do='get'), css_class="download") +
            fmt.text(label) +
            fmt.url(0))
    request.write('%s<br><br>' % link)

    mt = wikiutil.MimeType(filename=filename)

    # destinguishs if browser need a plugin in place
    if mt.major == 'image' and mt.minor in config.browser_supported_images:
        request.write('<img src="%s" alt="%s">' % (
            getAttachUrl(pagename, filename, request, escaped=1),
            wikiutil.escape(filename, 1)))
        return
    elif mt.major == 'text':
        ext = os.path.splitext(filename)[1]
        Parser = wikiutil.getParserForExtension(request.cfg, ext)
        try:
            backend = request.cfg.data_backend
            item = backend.get_item(pagename + "/" + filename)
            rev = item.get_revision(-1)
        except (NoSuchItemError, NoSuchRevisionError):
            error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}
        else:
            content = rev.read()  # XXX unbuffered reading as before?!
            content = wikiutil.decodeUnknownInput(content)

            if Parser is not None:
                    colorizer = Parser(content, request, filename=filename)
                    colorizer.format(request.formatter)
                    return

            request.write(request.formatter.preformatted(1))
            # If we have text but no colorizing parser we try to decode file contents.
            content = wikiutil.escape(content)
            request.write(request.formatter.text(content))
            request.write(request.formatter.preformatted(0))
            return

    # XXX Fix this zipfile stuff
   # try:
   #     package = packages.ZipPackage(request, fpath)
   #     if package.isPackage():
   #         request.write("<pre><b>%s</b>\n%s</pre>" % (_("Package script:"), wikiutil.escape(package.getScript())))
   #         return

   #     if zipfile.is_zipfile(fpath) and mt.minor == 'zip':
   #         zf = zipfile.ZipFile(fpath, mode='r')
   #         request.write("<pre>%-46s %19s %12s\n" % (_("File Name"), _("Modified")+" "*5, _("Size")))
   #         for zinfo in zf.filelist:
   #             date = "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time
   #             request.write(wikiutil.escape("%-46s %s %12d\n" % (zinfo.filename, date, zinfo.file_size)))
   #         request.write("</pre>")
   #         return
   # except RuntimeError:
   #     # We don't want to crash with a traceback here (an exception
   #     # here could be caused by an uploaded defective zip file - and
   #     # if we crash here, the user does not get a UI to remove the
   #     # defective zip file again).
   #     # RuntimeError is raised by zipfile stdlib module in case of
   #     # problems (like inconsistent slash and backslash usage in the
   #     # archive).
   #     logging.exception("An exception within zip file attachment handling occurred:")
   #     return

    from MoinMoin import macro
    from MoinMoin.parser.text import Parser

    macro.request = request
    macro.formatter = request.html_formatter
    p = Parser("##\n", request)
    m = macro.Macro(p)

    # use EmbedObject to view valid mime types
    if mt is None:
        request.write('<p>' + _("Unknown file type, cannot display this attachment inline.") + '</p>')
        link = (fmt.url(1, getAttachUrl(pagename, filename, request)) +
                fmt.text(filename) +
                fmt.url(0))
        request.write('For using an external program follow this link %s' % link)
        return
    request.write(m.execute('EmbedObject', u'target="%s", pagename="%s"' % (filename, pagename)))
    return

def _do_view(pagename, request, filename):
    _ = request.getText

    if not request.user.may.read(pagename):
        return _('You are not allowed to view attachments of this page.')
    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
    else:
        filename = wikiutil.taintfilename(request.form["target"][0])

    backend = request.cfg.data_backend
    try:
        item = backend.get_item(pagename + "/" + filename)
        rev = item.get_revision(-1)
    except (NoSuchItemError, NoSuchRevisionError):
        error = _("Attachment '%(filename)s' does not exist!") % {'filename': filename}
    else:
        # send header & title
        request.emit_http_headers()
        # Use user interface language for this generated page
        request.setContentLanguage(request.lang)
        title = _('attachment:%s of %s') % (filename, pagename)
        request.theme.send_title(title, pagename=pagename)

        # send body
        request.write(request.formatter.startContent())
        send_viewfile(pagename, request, filename)
        send_uploadform(pagename, request)
        request.write(request.formatter.endContent())

        request.theme.send_footer(pagename)
        request.theme.send_closing_html()


#############################################################################
### File attachment administration
#############################################################################

def do_admin_browser(request):
    """ Browser for SystemAdmin macro. """
    from MoinMoin.util.dataset import TupleDataset, Column
    _ = request.getText

    data = TupleDataset()
    data.columns = [
        Column('page', label=('Page')),
        Column('file', label=('Filename')),
        Column('size', label=_('Size'), align='right'),
    ]

    # iterate over pages that might have attachments
    pages = request.rootpage.getPageList()
    for pagename in pages:
        # check for attachments directory
        page_dir = getAttachDir(request, pagename)
        if os.path.isdir(page_dir):
            # iterate over files of the page
            files = os.listdir(page_dir)
            for filename in files:
                filepath = os.path.join(page_dir, filename)
                data.addRow((
                    Page(request, pagename).link_to(request, querystr="action=AttachFile"),
                    wikiutil.escape(filename.decode(config.charset)),
                    os.path.getsize(filepath),
                ))

    if data:
        from MoinMoin.widget.browser import DataBrowserWidget

        browser = DataBrowserWidget(request)
        browser.setData(data)
        return browser.render(method="GET")

    return ''

