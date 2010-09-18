# -*- coding: iso-8859-1 -*-
"""
    MoinMoin caching module

    @copyright: 2001-2004 by Juergen Hermann <jh@web.de>,
                2006-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:ThomasPfaff
    @license: GNU GPL, see COPYING for details.
"""

import os
import shutil
import tempfile
import hashlib
import hmac

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app

from MoinMoin import config
from MoinMoin.util import filesys, lock, pickle, PICKLE_PROTOCOL


class CacheError(Exception):
    """ raised if we have trouble locking, reading or writing """
    pass


def get_arena_dir(arena, scope):
    """ Get a cache storage directory for some specific scope and arena.

        scope     arena
        ---------------------------------------------------------------------
        'item'    should be the item name (is stored in a per-wiki cache arena)
                  [unicode]
        'wiki'    some unique name for a per-wiki cache arena
                  [ascii str]
        'farm'    some unique name for a common farm-global cache arena
                  [ascii str]
        'dir'     arena directly gives some storage directory, just use that
    """
    if scope == 'dir':
        return arena
    if scope == 'item':
        path = app.cfg.siteid, 'item', hashlib.new('sha1', arena.encode('utf-8')).hexdigest()
    elif scope == 'wiki':
        path = app.cfg.siteid, arena
    elif scope == 'farm':
        path = '__common__', arena
    else:
        raise ValueError('Unsupported scope: %r' % scope)
    return os.path.join(app.cfg.cache_dir, *path)


def get_cache_list(arena, scope):
    arena_dir = get_arena_dir(arena, scope)
    try:
        return os.listdir(arena_dir)
    except OSError:
        return []


class CacheEntry(object):
    def __init__(self, arena, key, scope='wiki', do_locking=True,
                 use_pickle=False, use_encode=False):
        """ init a cache entry
            @param scope: see get_arena_dir()
            @param arena: see get_arena_dir()
            @param key: under which key we access the cache content [str, ascii]
            @param do_locking: if there should be a lock, normally True
            @param use_pickle: if data should be pickled/unpickled (nice for arbitrary cache content)
            @param use_encode: if data should be encoded/decoded (nice for readable cache files)
        """
        self.key = key
        self.locking = do_locking
        self.use_pickle = use_pickle
        self.use_encode = use_encode
        self.arena_dir = get_arena_dir(arena, scope)
        if not os.path.exists(self.arena_dir):
            os.makedirs(self.arena_dir)
        self._fname = os.path.join(self.arena_dir, key)

        # used by file-like api:
        self._lock = None  # either a read or a write lock
        self._fileobj = None  # open cache file object
        self._tmp_fname = None  # name of temporary file (used for write)
        self._mode = None  # mode of open file object

    def exists(self):
        return os.path.exists(self._fname)

    def mtime(self):
        # DEPRECATED for checking a changed on-disk cache, please use
        # self.uid() for this, see below
        try:
            return os.path.getmtime(self._fname)
        except (IOError, OSError):
            return 0

    def size(self):
        try:
            return os.path.getsize(self._fname)
        except (IOError, OSError):
            return 0

    def uid(self):
        """ Return a value that likely changes when the on-disk cache was updated.

            See docstring of MoinMoin.util.filesys.fuid for details.
        """
        return filesys.fuid(self._fname)

    def needsUpdate(self, *timestamps):
        """ Checks whether cache needs to get updated because some
            timestamp is newer than the cache contents. The list of
            timestamps can be built from objects that the cache contents
            are built from / depends on.

        @param timestamps: UNIX timestamps (int or float)
        @return: True if cache needs updating, False otherwise.
        """
        try:
            cache_mtime = os.path.getmtime(self._fname)
        except os.error:
            # no cache file or other problem accessing it
            return True

        for timestamp in timestamps:
            assert isinstance(timestamp, (int, long, float))
            if timestamp > cache_mtime:
                return True

        return False

    def lock(self, mode, timeout=10.0):
        """
        acquire a lock for <mode> ("r" or "w").
        we just raise a CacheError if this doesn't work.

        Note:
         * .open() calls .lock(), .close() calls .unlock() if do_locking is True.
         * if you need to do a read-modify-write, you want to use a CacheEntry
           with do_locking=False and manually call .lock('w') and .unlock().
        """
        lock_dir = os.path.join(self.arena_dir, '__lock__')
        if 'r' in mode:
            _lock = lock.LazyReadLock(lock_dir, 60.0)
        elif 'w' in mode:
            _lock = lock.LazyWriteLock(lock_dir, 60.0)
        acquired = _lock.acquire(timeout)
        if acquired:
            self._lock = _lock
        else:
            self._lock = None
            err = "Can't acquire %s lock in %s" % (mode, lock_dir)
            logging.error(err)
            raise CacheError(err)

    def unlock(self):
        """
        release the lock.
        """
        if self._lock:
            self._lock.release()
            self._lock = None

    # file-like interface ----------------------------------------------------

    def open(self, filename=None, mode='r', bufsize=-1):
        """ open the cache for reading/writing

        Typical usage:
            try:
                cache.open('r')  # open file, create locks
                data = cache.read()
            finally:
                cache.close()  # important to close file and remove locks

        @param filename: must be None (default - automatically determine filename)
        @param mode: 'r' (read, default), 'w' (write)
                     Note: if mode does not include 'b' (binary), it will be
                           automatically changed to include 'b'.
        @param bufsize: size of read/write buffer (default: -1 meaning automatic)
        @return: None (the opened file object is kept in self._fileobj and used
                 implicitely by read/write/close functions of CacheEntry object.
        """
        assert self._fileobj is None, 'caching: trying to open an already opened cache'
        assert filename is None, 'caching: giving a filename is not supported (yet?)'
        assert 'r' in mode or 'w' in mode, 'caching: mode must contain "r" or "w"'

        if 'b' not in mode:
            mode += 'b'  # we want to use binary mode, ever!
        self._mode = mode  # for self.close()

        if self.locking:
            self.lock(mode)
        try:
            if 'r' in mode:
                filename = self._fname
                self._fileobj = open(filename, mode, bufsize)
            elif 'w' in mode:
                # we do not write content to old inode, but to a new file
                # so we don't need to lock when we just want to read the file
                # (at least on POSIX, this works)
                filename = None
                fd, filename = tempfile.mkstemp('.tmp', self.key, self.arena_dir)
                self._tmp_fname = filename
                self._fileobj = os.fdopen(fd, mode, bufsize)
        except IOError, err:
            if 'w' in mode:
                # IOerror for 'r' can be just a non-existing file, do not log that,
                # but if open fails for 'w', we likely have some bigger problem:
                logging.error(str(err))
            raise CacheError(str(err))

    def read(self, size=-1):
        """ read data from cache file

        @param size: how many bytes to read (default: -1 == everything)
        @return: read data (str)
        """
        return self._fileobj.read(size)

    def write(self, data):
        """ write data to cache file

        @param data: write data (str)
        """
        self._fileobj.write(data)

    def close(self):
        """ close cache file (and release lock, if any) """
        try:
            if self._fileobj:
                self._fileobj.close()
                self._fileobj = None
                if 'w' in self._mode:
                    filesys.chmod(self._tmp_fname, 0666 & config.umask) # fix mode that mkstemp chose
                    # this is either atomic or happening with real locks set:
                    filesys.rename(self._tmp_fname, self._fname)
        finally:
            if self.locking:
                self.unlock()

    # ------------------------------------------------------------------------

    def update(self, content):
        try:
            if hasattr(content, 'read'):
                # content is file-like
                assert not (self.use_pickle or self.use_encode), 'caching: use_pickle and use_encode not supported with file-like api'
                try:
                    self.open(mode='w')
                    shutil.copyfileobj(content, self)
                finally:
                    self.close()
            else:
                # content is a string
                if self.use_pickle:
                    content = pickle.dumps(content, PICKLE_PROTOCOL)
                elif self.use_encode:
                    content = content.encode(config.charset)

                try:
                    self.open(mode='w')
                    self.write(content)
                finally:
                    self.close()
        except (pickle.PicklingError, OSError, IOError, ValueError), err:
            raise CacheError(str(err))

    def content(self):
        # no file-like api yet, we implement it when we need it
        try:
            try:
                self.open(mode='r')
                data = self.read()
            finally:
                self.close()
            if self.use_pickle:
                data = pickle.loads(data)
            elif self.use_encode:
                data = data.decode(config.charset)
            return data
        except (pickle.UnpicklingError, IOError, EOFError, ValueError), err:
            raise CacheError(str(err))

    def remove(self):
        if self.locking:
            self.lock('w')
        try:
            try:
                os.remove(self._fname)
            except OSError:
                pass
        finally:
            if self.locking:
                self.unlock()


def cache_key(_secret=None, **kw):
    """
    Calculate a (hard-to-guess) cache key

    Important key properties:
    * The key must be hard to guess (so you do not need permission checks
      when a user access the cache via URL - if he knows the key, he is allowed
      to see the contents). Because of that we use hmac and a server secret
      to compute the key.
    * The key must be different for different **kw.

    @param **kw: keys/values to compute cache key from
    @param _secret: secret for hMAC calculation (default: use secret from cfg)
    """
    hmac_data = repr(kw)
    if _secret is None:
        _secret = app.cfg.secrets['action/cache']
    return hmac.new(_secret, hmac_data, digestmod=hashlib.sha1).hexdigest()

