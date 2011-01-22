"""
Our reimplementation of flask's send_file(), which is still behaving
incorrect for us as of flask 0.6.1 (we can't wait until flask 1.0, sorry).

For details see: https://github.com/mitsuhiko/flask/issues/issue/104

This code is based on flask 0.6.0 and fixes all the issues described in the
bug report.

This code is under same license as flask.
Modifications were done by Thomas Waldmann.
"""
import os
import mimetypes
from time import time
from zlib import adler32

from werkzeug import Headers, wrap_file
from flask import current_app, request

def send_file(filename_or_fp=None,
              mimetype=None,
              as_attachment=False, attachment_filename=None,
              add_etags=True,
              cache_timeout=60 * 60 * 12, conditional=False,
              etag=None,
              file=None, filename=None):
    """Sends the contents of a file to the client.  This will use the
    most efficient method available and configured.  By default it will
    try to use the WSGI server's file_wrapper support.  Alternatively
    you can set the application's :attr:`~Flask.use_x_sendfile` attribute
    to ``True`` to directly emit an `X-Sendfile` header.  This however
    requires support of the underlying webserver for `X-Sendfile`.

    By default it will try to guess the mimetype for you, but you can
    also explicitly provide one.  For extra security you probably want
    to sent certain files as attachment (HTML for instance).

    Please never pass filenames to this function from user sources without
    checking them first.  Something like this is usually sufficient to
    avoid security problems::

        if '..' in filename or filename.startswith('/'):
            abort(404)

    .. versionadded:: 0.2

    .. versionadded:: 0.5
       The `add_etags`, `cache_timeout` and `conditional` parameters were
       added.  The default behaviour is now to attach etags.

    .. versionadded:: 0.6.0-moin (moin's private reimplementation)
       The `file`, `filename` and `etag` parameters were added.
       `filename_or_fp` is deprecated now.

    :param filename_or_fp: *** DEPRECATED - use file/filename param ***
    :param mimetype: the mimetype of the file if provided, otherwise
                     auto detection happens.
    :param as_attachment: set to `True` if you want to send this file with
                          a ``Content-Disposition: attachment`` header.
    :param attachment_filename: the filename for the attachment if it
                                differs from the file's filename.
    :param add_etags: set to `False` to disable attaching of etags.
    :param conditional: set to `True` to enable conditional responses.
    :param cache_timeout: the timeout in seconds for the headers.
    :param etag: you can give an etag here, None means to try to compute the
                 etag from the file's filesystem metadata.
    :param file: a file object, if we can't make up the filename and you
                 do not provide it, `X-Sendfile` will not work and we'll
                 fall back to the traditional method.
    :param filename: the filesystem filename of the file to send,
                     None means to try to autodetect it from `name` attr
                     of the given file object. If you give any falsy non-None
                     value (e.g. '' or False) it will not try to autodetect,
                     nor assume that this is a fs file.
                     The filename is relative to the :attr:`~Flask.root_path`
                     if a relative path is specified.
    """
    mtime = None
    if filename_or_fp is not None:
        current_app.logger.warning('send_file filename_or_fp param is deprecated, use file=... and/or filename=...')

    if filename is None:
        if file is not None:
            filename = getattr(file, 'name', None)
        # vv support for deprecated filename_or_fp param vv
        elif isinstance(filename_or_fp, basestring):
            filename = filename_or_fp
        elif hasattr(filename_or_fp, 'read'):
            filename = getattr(filename_or_fp, 'name', None)
        # ^^ support for deprecated filename_or_fp param ^^

    if filename is None:
        raise ValueError("can't determine filename")

    if filename:
        if not os.path.isabs(filename):
            filename = os.path.join(current_app.root_path, filename)

    # vv support for deprecated filename_or_fp param vv
    if file is None:
        if hasattr(filename_or_fp, 'read'):
            file = filename_or_fp
    # ^^ support for deprecated filename_or_fp param ^^

    if mimetype is None and (filename or attachment_filename):
        mimetype = mimetypes.guess_type(filename or attachment_filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    headers = Headers()
    if as_attachment:
        if attachment_filename is None:
            if not filename:
                raise TypeError('filename unavailable, required for '
                                'sending as attachment')
            attachment_filename = os.path.basename(filename)
        headers.add('Content-Disposition', 'attachment',
                    filename=attachment_filename)

    if current_app.use_x_sendfile and filename:
        if file:
            file.close()
        headers['X-Sendfile'] = filename
        data = None
    else:
        if not file and filename:
            file = open(filename, 'rb')
            mtime = os.path.getmtime(filename)
        data = wrap_file(request.environ, file)

    rv = current_app.response_class(data, mimetype=mimetype, headers=headers,
                                    direct_passthrough=True)

    # if we know the file modification date, we can store it as the
    # current time to better support conditional requests.  Werkzeug
    # as of 0.6.1 will override this value however in the conditional
    # response with the current time.  This will be fixed in Werkzeug
    # with a new release, however many WSGI servers will still emit
    # a separate date header.
    if mtime is not None:
        rv.date = int(mtime)

    rv.cache_control.public = True
    if cache_timeout:
        rv.cache_control.max_age = cache_timeout
        rv.expires = int(time() + cache_timeout)

    if add_etags:
        if filename and etag is None:
            etag = 'flask-%s-%s-%s' % (
                mtime or os.path.getmtime(filename),
                os.path.getsize(filename),
                adler32(filename) & 0xffffffff
            )
        if etag is not None:
            rv.set_etag(etag)
        else:
            raise ValueError("can't determine etag - please give etag or filename")
        if conditional:
            rv = rv.make_conditional(request)
            # make sure we don't send x-sendfile for servers that
            # ignore the 304 status code for x-sendfile.
            if rv.status_code == 304:
                rv.headers.pop('x-sendfile', None)
    return rv

