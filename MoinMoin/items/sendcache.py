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

import hashlib
import hmac

from MoinMoin import log
logging = log.getLogger(__name__)

from MoinMoin import wikiutil
from MoinMoin import config, caching

class SendCache(object):
    cache_arena = 'sendcache' # Do NOT get this directly from request.values or user would be able to read any cache!
    cache_scope = 'wiki'
    do_locking = False

    @classmethod
    def from_meta(cls, request, meta, secret=None):
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

        We calculate the key from meta (meta contains a hash digest of the original
        content, so it is already unique and collisions unlikely). To even improve
        security more, we create a hmac using a server secret (it also has the side
        effect that if the hmac is shorter than all the meta info, it will result in
        shorter URLs).

        @param meta: object to compute cache key from
        @param secret: secret for hMAC calculation (default: use secret from cfg)
        """
        hmac_data = repr(meta)
        if secret is None:
            secret = request.cfg.secrets['action/cache']
        key = hmac.new(secret, hmac_data, digestmod=hashlib.sha1).hexdigest()
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
            original=None):
        """
        Put an object into the cache to send it with cache action later.

        @param data: content data (str or open file-like obj) or None.
                     if None is given, you need to write content data directly to data_cache
                     before invoking put() method.
        @param filename: filename for content-disposition header and for autodetecting
                         content_type (unicode, default: None)
        @param content_type: content-type header value (str, default: autodetect from filename)
        @param content_disposition: type for content-disposition header (str, default: None)
        @param content_length: data length for content-length header (int, default: autodetect)
        @param original: location of original object (default: None) - this is just written to
                         the metadata cache "as is" and could be used for cache cleanup,
                         use (wikiname, itemname).
        """
        request = self.request
        key = self.key
        import os.path

        if filename:
            # make sure we just have a simple filename (without path)
            filename = os.path.basename(filename)
            mt = wikiutil.MimeType(filename=filename)
        else:
            mt = None

        if content_type is None:
            if mt is not None:
                content_type = mt.content_type()
            else:
                content_type = 'application/octet-stream'
        else:
            mt = wikiutil.MimeType(mimestr=content_type)

        if data is not None:
            self.data_cache.update(data)
        content_length = content_length or self.data_cache.size()
        headers = [('Content-Type', content_type),
                   ('Content-Length', content_length),
                  ]
        if content_disposition is None and mt is not None:
            content_disposition = mt.content_disposition(request.cfg)
        if content_disposition:
            headers.append(('Content-Disposition', content_disposition))

        self.meta_cache.update({
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
        """ get headers cached for key """
        meta = self.meta_cache.content()
        return meta['headers']

    def _get_datafile(self):
        """ get an open data file for the data cached for key """
        self.data_cache.open(mode='r')
        return self.data_cache

