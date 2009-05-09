# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - SendCache - send a raw object from the caching system (and
    offer utility functions to put data into cache, calculate cache key, ...).

    Sample usage
    ------------
    Assume we have a big picture item named bigpic and we want to efficiently
    show some thumbnail (thumbpic) for it:

    # create a cache object from some meta data values (this internally computes
    # cache.key in a non-guessable way):
    cache = SendCache.from_meta(request, itemname=bigpic)

    # check if we don't have it in cache yet
    if not cache.exists():
        # if we don't have it in cache, we need to render it - this is an
        # expensive operation that we want to avoid by caching:
        thumbpic = render_thumb(bigpic)
        # put expensive operation's results into cache:
        cache.put(thumbpic, ...)

    html = '<img src="%s">' % cache.url()

    @copyright: 2008 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import log
logging = log.getLogger(__name__)

# keep both imports below as they are, order is important:
from MoinMoin import wikiutil
import mimetypes

from MoinMoin import config, caching
from MoinMoin.support.python_compatibility import hmac_new

class SendCache(object):
    cache_arena = 'sendcache' # Do NOT get this directly from request.values or user would be able to read any cache!
    cache_scope = 'wiki'
    do_locking = False

    @classmethod
    def from_meta(request, wikiname=None, itemname=None, revision=None,
                  content=None, secret=None):
        """
        Calculate a (hard-to-guess) cache key from meta data

        Important key properties:
        * The key must be hard to guess (this is because do=get does no ACL checks,
          so whoever got the key [e.g. from html rendering of an ACL protected wiki
          page], will be able to see the cached content.
        * The key must change if the (original) content changes. This is because
          ACLs on some item may change and even if somebody was allowed to see some
          revision of some item, it does not implicate that he is allowed to see
          any other revision also. There will be no harm if he can see exactly the
          same content again, but there could be harm if he could access a revision
          with different content.

        If content is supplied, we will calculate and return a hMAC of the content.

        If wikiname, itemname is given, we don't touch the content (nor do we read
        it ourselves from the item data), but we just calculate a key from the
        item's metadata).

        Hint: if you need multiple cache objects for the same source content (e.g.
              thumbnails of different sizes for the same image), calculate the key
              only once and then add some different prefixes to it to get the final
              cache keys.

        @param wikiname: the name of the wiki (if not given, will be read from cfg)
        @param itemname: the name of the page
        @param content: content data as unicode object (e.g. for page content or
                        parser section content)
        @param secret: secret for hMAC calculation (default: use secret from cfg)
        """
        if content:
            hmac_data = content
        elif itemname is not None and revision is not None:
            wikiname = wikiname or request.cfg.interwikiname or request.cfg.siteid
            def _uid(wikiname, itemname, revision):
                # XXX this works as long as no renames happen, a content
                # hash would be better, though, but we have none yet.
                return u':'.join([wikiname, itemname, str(revision)])
            hmac_data = _uid(wikiname, itemname, revision)
        else:
            raise ValueError('from_meta called with unsupported parameters')

        if isinstance(hmac_data, unicode):
            hmac_data = hmac_data.encode('utf-8')
        if secret is None:
            secret = request.cfg.secrets['action/cache']
        key = hmac_new(secret, hmac_data).hexdigest()
        return cls(request, key)

    def __init__(self, request, key):
        """
        A cache object for http responses (e.g. for expensive-to-compute stuff)

        @param request: the request object
        @param key: non-guessable key into cache (str)
        """
        self.request = request
        self.key = key
        self._meta_cache = None
        self._data_cache = None

    def _get_cache(self, cache_type):
        return caching.CacheEntry(self.request, self.cache_arena, self.key+'.'+cache_type,
                                  self.cache_scope, do_locking=self.do_locking, use_pickle=(cache_type=='meta'))
    def _get_meta_cache(self):
        if self._meta_cache is None:
            self._meta_cache = self._get_cache('meta')
        return self._meta_cache
    meta_cache = property(_get_meta_cache)

    def _get_data_cache(self):
        if self._data_cache is None:
            self._data_cache = self._get_cache('data')
        return self._data_cache
    data_cache = property(_get_data_cache)

    def put(self, data,
            filename=None,
            content_type=None,
            content_disposition=None,
            content_length=None,
            last_modified=None,
            original=None):
        """
        Put an object into the cache to send it with cache action later.

        @param data: content data (str or open file-like obj)
        @param filename: filename for content-disposition header and for autodetecting
                         content_type (unicode, default: None)
        @param content_type: content-type header value (str, default: autodetect from filename)
        @param content_disposition: type for content-disposition header (str, default: None)
        @param content_length: data length for content-length header (int, default: autodetect)
        @param last_modified: last modified timestamp (int, default: autodetect)
        @param original: location of original object (default: None) - this is just written to
                         the metadata cache "as is" and could be used for cache cleanup,
                         use (wikiname, itemname).
        """
        request = self.request
        key = self.key
        import os.path
        from MoinMoin.util import timefuncs

        if filename:
            # make sure we just have a simple filename (without path)
            filename = os.path.basename(filename)

            if content_type is None:
                # try autodetect
                mt, enc = mimetypes.guess_type(filename)
                if mt:
                    content_type = mt

        if content_type is None:
            content_type = 'application/octet-stream'

        self.data_cache.update(data)
        content_length = content_length or data_cache.size()
        last_modified = last_modified or data_cache.mtime()

        httpdate_last_modified = timefuncs.formathttpdate(int(last_modified))
        headers = [('Content-Type', content_type),
                   ('Last-Modified', httpdate_last_modified),
                   ('Content-Length', content_length),
                  ]
        if content_disposition and filename:
            # TODO: fix the encoding here, plain 8 bit is not allowed according to the RFCs
            # There is no solution that is compatible to IE except stripping non-ascii chars
            filename = filename.encode(config.charset)
            headers.append(('Content-Disposition', '%s; filename="%s"' % (content_disposition, filename)))

        self.meta_cache.update({
            'httpdate_last_modified': httpdate_last_modified,
            'last_modified': last_modified,
            'headers': headers,
            'original': original,
        })


    def exists(self, strict=False):
        """
        Check if a cached object for this key exists.

        @param strict: if True, also check the data cache, not only meta (bool, default: False)
        @return: is object cached? (bool)
        """
        request = self.request
        key = self.key
        if strict:
            data_cached = self.data_cache.exists()
        else:
            data_cached = True  # we assume data will be there if meta is there

        meta_cached = self.meta_cache.exists()

        return meta_cached and data_cached


    def remove(self):
        """ delete headers/data cache for key

        @param key: non-guessable key into cache (str)
        """
        self.meta_cache.remove()
        self.data_cache.remove()


    def url(self):
        """ return URL for the object cached for key """
        return self.request.href(action='get', from_cache=self.key)

    def _get_headers(self):
        """ get last_modified and headers cached for key """
        meta = self.meta_cache.content()
        return meta['httpdate_last_modified'], meta['headers']

    def _get_datafile(self):
        """ get an open data file for the data cached for key """
        self.data_cache.open(mode='r')
        return self.data_cache

    def do_get(self):
        """ send a complete http response with headers/data cached for key """
        request = self.request
        try:
            last_modified, headers = self._get_headers()
            if request.if_modified_since == last_modified:
                request.status_code = 304
            else:
                data_file = self._get_datafile()
                for key, value in headers:
                    lkey = key.lower()
                    if lkey == 'content-type':
                        request.content_type = value
                    elif lkey == 'last-modified':
                        request.last_modified = value
                    elif lkey == 'content-length':
                        request.content_length = value
                    else:
                        request.headers.add(key, value)
                request.send_file(data_file)
        except caching.CacheError:
            request.status_code = 404

