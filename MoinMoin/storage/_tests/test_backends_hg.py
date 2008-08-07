# -*- coding: utf-8 -*-
"""
    MoinMoin - Test - MercurialBackend

    Testcases specific only for MercurialBackend.
    Common backend API tests are defined in test_backends.py

    ---

    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from tempfile import mkdtemp, mkstemp
import py.test
import shutil
import os

from MoinMoin.storage._tests.test_backends import BackendTest
from MoinMoin.storage.backends.hg import MercurialBackend
from MoinMoin.storage.error import BackendError
from MoinMoin.storage._tests.test_backends import item_names

class TestMercurialBackend(BackendTest):
    """MercurialBackend test class."""
    try:
        from mercurial.context import memctx
    except ImportError:
        py.test.skip("Wrong version of mercurial: please test on development version.")
        # disabled = True
    def __init__(self):
        names = item_names + (u'_ĄółóĄ_', ) # tricky for internal hg quoting, however
                                            # not much needed if item names are hashes
        BackendTest.__init__(self, None, valid_names=names)
        

    def create_backend(self):
        self.test_dir = mkdtemp()
        return MercurialBackend(self.test_dir)

    def kill_backend(self):
        shutil.rmtree(self.test_dir)

    def test_backend_init(self):
        nonexisting = os.path.join("/", "non-existing-dir")
        py.test.raises(BackendError, MercurialBackend, nonexisting)
        emptydir, file = mkdtemp(), mkstemp()[1]
        dirstruct = mkdtemp()
        os.mkdir(os.path.join(dirstruct, "meta"))
        os.mkdir(os.path.join(dirstruct, "rev"))
        try:
            py.test.raises(BackendError, MercurialBackend, emptydir, create=False)
            assert isinstance(MercurialBackend(emptydir), MercurialBackend)
            py.test.raises(BackendError, MercurialBackend, emptydir)
            assert isinstance(MercurialBackend(emptydir, create=False), MercurialBackend)
            py.test.raises(BackendError, MercurialBackend, file)
            assert isinstance(MercurialBackend(dirstruct), MercurialBackend)
        finally:
            shutil.rmtree(emptydir)
            shutil.rmtree(dirstruct)
            os.unlink(file)

    def test_backend_init_non_empty_datadir(self):
        datadir = mkdtemp()
        os.mkdir(os.path.join(datadir, "meta"))
        os.mkdir(os.path.join(datadir, "rev"))
        try:
            nameitem = mkstemp(dir=datadir)[1]
            py.test.raises(BackendError, MercurialBackend, datadir)
            os.unlink(nameitem)
            revitem = mkstemp(dir=os.path.join(datadir, "rev"))[1]
            py.test.raises(BackendError, MercurialBackend, datadir)
            os.unlink(revitem)
            mkstemp(dir=os.path.join(datadir, "meta"))[1]
            py.test.raises(BackendError, MercurialBackend, datadir)
        finally:
            shutil.rmtree(datadir)

    def test_large_revision_meta(self):
        item = self.backend.create_item('existing')
        rev = item.create_revision(0)
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            rev["%s" % num] = revval * 10
        item.commit()
        item = self.backend.get_item('existing')
        rev = item.get_revision(-1)
        assert len(dict(rev)) == 10000
        for num in xrange(10000):
            revval = "revision metatdata value for key %d" % num
            assert rev["%s" % num] == revval * 10

    def test_concurrent_create_revision(self):
        """
        < COVER GENERIC TEST >
        Hg backend will fail this generic test, because of
        completely different policy. You can create new revision
        in such case, just a new head is created (and currently we
        merge heads automatically). Thus, see merge tests below.
        """
        py.test.skip("Different policy: creating new head from parent revision\
instead of throwing RevisionAlreadyExistsError")

    def test_item_branch_and_merge(self):
        """
        This test depicts somehow strange behaviour:
        - if revisions have no/same data and metadata
        the latter commit (item2.commit()) has no effect -
        no revisions appear. Just adding some meta or data,
        or what is stranger, delay like time.sleep(1) beetwen
        item1 and item2 commits makes it work as expected.
        AFAIK this is not locking isssue, though needs more 
        ivestigation in later time.        
        This does not affect normal usage, since such empty
        merge is useless, and is just duplication of data.        
        """
        item = self.backend.create_item("double-headed")
        item.create_revision(0)
        item.commit()
        item1 = self.backend.get_item("double-headed")
        item2 = self.backend.get_item("double-headed")
        item1.create_revision(1)['a'] = 's'
        item2.create_revision(1)['a'] = 'ss'
        item1.commit()
        item2.commit()
        assert item2.list_revisions() == range(4)
        item1 = self.backend.get_item("double-headed")
        assert len(item1.list_revisions()) == 4  
        assert item1.list_revisions() == item2.list_revisions()

    def test_item_revmeta_merge(self):
        self.create_rev_item_helper("double-headed")
        item1 = self.backend.get_item("double-headed")
        item2 = self.backend.get_item("double-headed")
        rev1 = item1.create_revision(1)
        rev2 = item2.create_revision(1)
        rev1["age"] = "older"
        rev1["first"] = "alfa"
        rev2["age"] = "younger"
        rev2["second"] = "beta"
        item1.commit()
        item2.commit()
        item = self.backend.get_item("double-headed")
        for rev in (item1.get_revision(-1), item.get_revision(3)):
            assert rev["age"] == "younger"
            assert rev["first"] == "alfa"
            assert rev["second"] == "beta"
        assert len(rev._metadata.keys()) == 3

    def test_item_merge_data(self):
        first_text = "Lorem ipsum."
        second_text = "Lorem ipsum dolor sit amet."
        after_merge = "\n---- /!\ '''Edit conflict - other version:''' ----\nLorem ipsum.\n---- /!\ '''Edit conflict - your version:''' ----\nLorem ipsum dolor sit amet.\n---- /!\ '''End of edit conflict''' ----\n"
        self.create_rev_item_helper("lorem-ipsum")
        item1 = self.backend.get_item("lorem-ipsum")
        item2 = self.backend.get_item("lorem-ipsum")
        item1.create_revision(1).write(first_text)
        item2.create_revision(1).write(second_text)
        item1.commit()
        item2.commit()        
        item = self.backend.get_item("lorem-ipsum")
        rev = item.get_revision(-1)
        text = rev.read()            
        assert text == after_merge
