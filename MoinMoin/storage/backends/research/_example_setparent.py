import os
import sys
import random
import weakref
import tempfile

from mercurial import hg, ui, util, node, commands
from mercurial.repo import RepoError

class MercurialStorage(object):

    def __init__(self, path, page):
        self.path = os.path.abspath(path)
        self._lockref = None
        self.ui = ui.ui(report_untrusted=False, interactive=False)

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        if not os.path.exists(self._path(page)):
            _page = open(self._path(page), 'w')
            _page.write('test page, see entries below\n')
            _page.close()

        try:
            self.repo = hg.repository(self.ui, self.path)
        except RepoError:
            self.repo = hg.repository(self.ui, self.path, create=True)
            self.repo.add(os.listdir(self.path))
            self.repo.commit(text="created test environment", user='hgstore')


    def _path(self, page):
        return os.path.join(self.path, page)


    def _lock(self):
        if self._lockref and self._lockref():
            return self._lockref()
        lock = self.repo._lock(os.path.join(self.path, 'hgstore_lock'), True,
                None, None, "")
        self._lockref = weakref.ref(lock)
        return lock


    def _load_page(self, page, rev=None):
        ctx = self.repo.changectx()

        if rev is None:
            ftx = ctx.filectx(page)
        else:
            ftx = ctx.filectx(page).filectx(rev)

        return ftx.data(), ftx.rev()


    def edit_page(self, page, message, editor, parent=None):

        if not parent:
            data, rev = self._load_page(page)
        else:
            data, rev = self._load_page(page, parent)

        data = "%s>> %s" % (data, message)

        fd, fname = tempfile.mkstemp(prefix=page, dir=self.path)
        file = os.fdopen(fd, 'w')
        file.write(data)
        file.close()


        lock = self._lock()

        util.rename(fname, self._path(page))

        try:
            print '\tparent:', rev

            wlock = self.repo.wlock()
            try:
                self.repo.dirstate.setparents(self.repo.lookup(rev))
            finally:
                del wlock

            self.repo.commit(text=message, user=editor)

        finally:
            del lock


if __name__ == '__main__':

    ms = MercurialStorage('dsp_test', 'TestPage')

    ms.edit_page('TestPage', 'test write linear 1\n', 'test user')
    ms.edit_page('TestPage', 'test write linear 2\n', 'test user')

    pid = os.fork()
    if pid:
        ms.edit_page('TestPage', 'parent write\n', 'parent editor')
        os.wait()

    else:
        ms.edit_page('TestPage', 'child write\n', 'child editor')
        sys.exit()

