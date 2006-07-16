# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - search engine
    
    @copyright: 2005 MoinMoin:FlorianFesti,
                2005 MoinMoin:NirSoffer,
                2005 MoinMoin:AlexanderSchremmer,
                2006 MoinMoin:ThomasWaldmann,
                2006 MoinMoin:FranzPletz
    @license: GNU GPL, see COPYING for details
"""

import time, sys, os, errno
from MoinMoin import wikiutil, config
from MoinMoin.Page import Page
from MoinMoin.util import filesys, lock
from MoinMoin.search.results import getSearchResults
from MoinMoin.search.queryparser import TextMatch, TitleMatch

##############################################################################
# Search Engine Abstraction
##############################################################################

class UpdateQueue:
    def __init__(self, file, lock_dir):
        self.file = file
        self.writeLock = lock.WriteLock(lock_dir, timeout=10.0)
        self.readLock = lock.ReadLock(lock_dir, timeout=10.0)

    def exists(self):
        return os.path.exists(self.file)

    def append(self, pagename):
        """ Append a page to queue """
        if not self.writeLock.acquire(60.0):
            request.log("can't add %r to xapian update queue: can't lock queue" %
                        pagename)
            return
        try:
            f = codecs.open(self.file, 'a', config.charset)
            try:
                f.write(pagename + "\n")
            finally:
                f.close()
        finally:
            self.writeLock.release()

    def pages(self):
        """ Return list of pages in the queue """
        if self.readLock.acquire(1.0):
            try:
                return self._decode(self._read())
            finally:
                self.readLock.release()
        return []

    def remove(self, pages):
        """ Remove pages from the queue
        
        When the queue is empty, the queue file is removed, so exists()
        can tell if there is something waiting in the queue.
        """
        if self.writeLock.acquire(30.0):
            try:
                queue = self._decode(self._read())
                for page in pages:
                    try:
                        queue.remove(page)
                    except ValueError:
                        pass
                if queue:
                    self._write(queue)
                else:
                    self._removeFile()
                return True
            finally:
                self.writeLock.release()
        return False

    # Private -------------------------------------------------------

    def _decode(self, data):
        """ Decode queue data """
        pages = data.splitlines()
        return self._filterDuplicates(pages)

    def _filterDuplicates(self, pages):
        """ Filter duplicates in page list, keeping the order """
        unique = []
        seen = {}
        for name in pages:
            if not name in seen:
                unique.append(name)
                seen[name] = 1
        return unique

    def _read(self):
        """ Read and return queue data
        
        This does not do anything with the data so we can release the
        lock as soon as possible, enabling others to update the queue.
        """
        try:
            f = codecs.open(self.file, 'r', config.charset)
            try:
                return f.read()
            finally:
                f.close()
        except (OSError, IOError), err:
            if err.errno != errno.ENOENT:
                raise
            return ''

    def _write(self, pages):
        """ Write pages to queue file
        
        Requires queue write locking.
        """
        # XXX use tmpfile/move for atomic replace on real operating systems
        data = '\n'.join(pages) + '\n'
        f = codecs.open(self.file, 'w', config.charset)
        try:
            f.write(data)
        finally:
            f.close()

    def _removeFile(self):
        """ Remove queue file 
        
        Requires queue write locking.
        """
        try:
            os.remove(self.file)
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise

class BaseIndex:
    class LockedException(Exception):
        pass

    def __init__(self, request):
        self.request = request
        cache_dir = request.cfg.cache_dir
        main_dir = self._main_dir()
        self.dir = os.path.join(main_dir, 'index')
        filesys.makeDirs(self.dir)
        self.sig_file = os.path.join(main_dir, 'complete')
        lock_dir = os.path.join(main_dir, 'index-lock')
        self.lock = lock.WriteLock(lock_dir,
                                   timeout=3600.0, readlocktimeout=60.0)
        self.read_lock = lock.ReadLock(lock_dir, timeout=3600.0)
        self.queue = UpdateQueue(os.path.join(main_dir, 'update-queue'),
                                 os.path.join(main_dir, 'update-queue-lock'))

        # Disabled until we have a sane way to build the index with a
        # queue in small steps.
        ## if not self.exists():
        ##    self.indexPagesInNewThread(request)

    def _main_dir(self):
        raise NotImplemented

    def exists(self):
        """ Check if index exists """        
        return os.path.exists(self.sig_file)
                
    def mtime(self):
        return os.path.getmtime(self.dir)
    
    def _search(self, query):
        raise NotImplemented

    def search(self, query):
        if not self.read_lock.acquire(1.0):
            raise self.LockedException
        try:
            hits = self._search(query)
        finally:
            self.read_lock.release()
        return hits

    def update_page(self, page):
        self.queue.append(page.page_name)
        self._do_queued_updates_InNewThread()

    def indexPages(self, files=None, mode='update'):
        """ Index all pages (and files, if given)
        
        Can be called only from a script. To index pages during a user
        request, use indexPagesInNewThread.
        @arg files: iterator or list of files to index additionally
        """
        if not self.lock.acquire(1.0):
            self.request.log("can't index: can't acquire lock")
            return
        try:
            self._unsign()
            start = time.time()
            request = self._indexingRequest(self.request)
            self._index_pages(request, files, mode)
            request.log("indexing completed successfully in %0.2f seconds." %
                        (time.time() - start))
            self._sign()
        finally:
            self.lock.release()

    def indexPagesInNewThread(self, files=None, mode='update'):
        """ Index all pages in a new thread
        
        Should be called from a user request. From a script, use indexPages.
        """
        # Prevent rebuilding the index just after it was finished
        if self.exists():
            return

        from threading import Thread
        indexThread = Thread(target=self._index_pages, args=(files, mode))
        indexThread.setDaemon(True)
        
        # Join the index thread after current request finish, prevent
        # Apache CGI from killing the process.
        def joinDecorator(finish):
            def func():
                finish()
                indexThread.join()
            return func

        self.request.finish = joinDecorator(self.request.finish)
        indexThread.start()

    def _index_pages(self, request, files=None, mode='update'):
        """ Index all pages (and all given files)
        
        This should be called from indexPages or indexPagesInNewThread only!
        
        This may take some time, depending on the size of the wiki and speed
        of the machine.

        When called in a new thread, lock is acquired before the call,
        and this method must release it when it finishes or fails.
        """
        raise NotImplemented

    def _do_queued_updates_InNewThread(self):
        """ do queued index updates in a new thread
        
        Should be called from a user request. From a script, use indexPages.
        """
        if not self.lock.acquire(1.0):
            self.request.log("can't index: can't acquire lock")
            return
        try:
            def lockedDecorator(self, f):
                def func(*args, **kwargs):
                    try:
                        return f(*args, **kwargs)
                    finally:
                        self.lock.release()
                return func

            from threading import Thread
            indexThread = Thread(
                    target=lockedDecorator(self._do_queued_updates),
                    args=(self._indexingRequest(self.request),))
            indexThread.setDaemon(True)
            
            # Join the index thread after current request finish, prevent
            # Apache CGI from killing the process.
            def joinDecorator(finish):
                def func():
                    finish()
                    indexThread.join()
                return func
                
            self.request.finish = joinDecorator(self.request.finish)
            indexThread.start()
        except:
            self.lock.release()
            raise

    def _do_queued_updates(self, request, amount=5):
        raise NotImplemented

    def optimize(self):
        raise NotImplemented

    def contentfilter(self, filename):
        """ Get a filter for content of filename and return unicode content. """
        request = self.request
        mt = wikiutil.MimeType(filename=filename)
        for modulename in mt.module_name():
            try:
                execute = wikiutil.importPlugin(request.cfg, 'filter', modulename)
                break
            except wikiutil.PluginMissingError:
                pass
            else:
                request.log("Cannot load filter for mimetype." + modulename)
        try:
            data = execute(self, filename)
            # XXX: proper debugging?
            #if debug:
            #    request.log("Filter %s returned %d characters for file %s" % (modulename, len(data), filename))
        except (OSError, IOError), err:
            data = ''
            request.log("Filter %s threw error '%s' for file %s" % (modulename, str(err), filename))
        return mt.mime_type(), data

    def test(self, request):
        raise NotImplemented

    def _indexingRequest(self, request):
        """ Return a new request that can be used for index building.
        
        This request uses a security policy that lets the current user
        read any page. Without this policy some pages will not render,
        which will create broken pagelinks index.        
        """
        from MoinMoin.request.CLI import Request
        from MoinMoin.security import Permissions
        request = Request(request.url)
        class SecurityPolicy(Permissions):
            def read(*args, **kw):
                return True        
        request.user.may = SecurityPolicy(request.user)
        return request

    def _unsign(self):
        """ Remove sig file - assume write lock acquired """
        try:
            os.remove(self.sig_file)
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise

    def _sign(self):
        """ Add sig file - assume write lock acquired """
        f = file(self.sig_file, 'w')
        try:
            f.write('')
        finally:
            f.close()

##############################################################################
### Searching
##############################################################################

class Search:
    """ A search run """
    
    def __init__(self, request, query):
        self.request = request
        self.query = query
        self.filtered = False
        self.fs_rootpage = "FS" # XXX FS hardcoded

    def run(self):
        """ Perform search and return results object """
        start = time.time()
        if self.request.cfg.xapian_search:
            hits = self._xapianSearch()
        else:
            hits = self._moinSearch()
            
        # important - filter deleted pages or pages the user may not read!
        if not self.filtered:
            hits = self._filter(hits)

        return getSearchResults(self.request, self.query, hits, start)
        

    # ----------------------------------------------------------------
    # Private!

    def _xapianSearch(self):
        """ Search using Xapian
        
        Get a list of pages using fast xapian search and
        return moin search in those pages.
        """
        pages = None
        try:
            from MoinMoin.search.Xapian import Index
            index = Index(self.request)
        except ImportError:
            index = None
        
        if index and index.exists(): #and self.query.xapian_wanted():
            self.request.clock.start('_xapianSearch')
            try:
                from MoinMoin.support import xapwrap
                query = self.query.xapian_term(self.request, index.allterms)
                self.request.log("xapianSearch: query = %r" %
                        query.get_description())
                query = xapwrap.index.QObjQuery(query)
                enq, hits = index.search(query)
                self.request.log("xapianSearch: finds: %r" % hits)
                def dict_decode(d):
                    """ decode dict values to unicode """
                    for k, v in d.items():
                        d[k] = d[k].decode(config.charset)
                    return d
                pages = [{'uid': hit['uid'], 'values': dict_decode(hit['values'])}
                        for hit in hits]
                self.request.log("xapianSearch: finds pages: %r" % pages)
                self._xapianEnquire = enq
                self._xapianIndex = index
            except BaseIndex.LockedException:
                pass
            #except AttributeError:
            #    pages = []
            self.request.clock.stop('_xapianSearch')
            return self._getHits(hits, self._xapianMatch)
        else:
            return self._moinSearch(pages)

    def _xapianMatch(self, page, uid):
        matches = []
        term = self._xapianEnquire.get_matching_terms_begin(uid)
        #print hit['uid']
        while term != self._xapianEnquire.get_matching_terms_end(uid):
            print term.get_term(), ':', list(self._xapianIndex.termpositions(uid, term.get_term()))
            for pos in self._xapianIndex.termpositions(uid, term.get_term()):
                matches.append(TextMatch(start=pos,
                    end=pos+len(term.get_term())))
            term.next()
        return matches

    def _moinSearch(self, pages=None):
        """ Search pages using moin's built-in full text search 
        
        Return list of tuples (page, match). The list may contain
        deleted pages or pages the user may not read.
        """
        self.request.clock.start('_moinSearch')
        from MoinMoin.Page import Page
        if pages is None:
            # if we are not called from _xapianSearch, we make a full pagelist,
            # but don't search attachments (thus attachment name = '')
            pages = [{'pagename': p, 'attachment': '', 'wikiname': 'Self', } for p in self._getPageList()]
        hits = self._getHits(pages, self._moinMatch)
        self.request.clock.stop('_moinSearch')
        return hits
    
    def _moinMatch(self, page, uid):
        return self.query.search(page)

    def _getHits(self, pages, matchSearchFunction):
        hits = []
        fs_rootpage = self.fs_rootpage
        for hit in pages:
            if 'values' in hit:
                valuedict = hit['values']
                uid = hit['uid']
            else:
                valuedict = hit

            wikiname = valuedict['wikiname']
            pagename = valuedict['pagename']
            attachment = valuedict['attachment']
            if wikiname in (self.request.cfg.interwikiname, 'Self'): # THIS wiki
                page = Page(self.request, pagename)
                if attachment:
                    if pagename == fs_rootpage: # not really an attachment
                        page = Page(self.request, "%s/%s" % (fs_rootpage, attachment))
                        hits.append((wikiname, page, None, None))
                    else:
                        hits.append((wikiname, page, attachment, None))
                else:
                    match = matchSearchFunction(page, uid)
                    if match:
                        hits.append((wikiname, page, attachment, match))
            else: # other wiki
                hits.append((wikiname, pagename, attachment, None))
        return hits

    def _getPageList(self):
        """ Get list of pages to search in 
        
        If the query has a page filter, use it to filter pages before
        searching. If not, get a unfiltered page list. The filtering
        will happen later on the hits, which is faster with current
        slow storage.
        """
        filter = self.query.pageFilter()
        if filter:
            # There is no need to filter the results again.
            self.filtered = True
            return self.request.rootpage.getPageList(filter=filter)
        else:
            return self.request.rootpage.getPageList(user='', exists=0)
        
    def _filter(self, hits):
        """ Filter out deleted or acl protected pages """
        userMayRead = self.request.user.may.read
        fs_rootpage = self.fs_rootpage + "/"
        thiswiki = (self.request.cfg.interwikiname, 'Self')
        filtered = [(wikiname, page, attachment, match) for wikiname, page, attachment, match in hits
                    if not wikiname in thiswiki or
                       page.exists() and userMayRead(page.page_name) or
                       page.page_name.startswith(fs_rootpage)]
        return filtered
