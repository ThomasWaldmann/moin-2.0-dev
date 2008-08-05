"""
Sample code showing possibilities of current devel mercurial version:
- commiting changesets created in memory without a need of working copy
"""

from mercurial import hg, ui, context, node
import tempfile
import shutil
import os

class TestSimpleRepository(object):
    def __init__(self):       
        self.user = "just-a-test"
        self.file = "TestPage"
        self.commits = {0: ("foo", "initial version"),
                        1: ("bar", "minor improvement"),
                        2: ("baz", "grande finale"),}
    
    def setup_method(self, method):
        self.spawn_repo()
        
    def teardown_method(self, method):
        self.slay_repo()    
    
    def spawn_repo(self):
        self.path = tempfile.mkdtemp(prefix="tmp-", suffix="-simplerepo")
        self.repo = hg.repository(ui.ui(quiet=True, interactive=False, 
                            report_untrusted=False), self.path, create=True)
    def slay_repo(self):
        shutil.rmtree(self.path)
        
    def commit(self, path, data, text):        
        def getfilectx(repo, memctx, path):                
            islink, isexec, iscopy = False, False, False
            return context.memfilectx(path, data, islink, isexec, iscopy)
        p1 = self.repo.changelog.tip()
        p2 = node.nullid        
        ctx = context.memctx(self.repo, (p1, p2), text, [path], getfilectx)
        self.repo.commitctx(ctx)
        
    def check_working_copy(self):
        files = os.listdir(self.path)
        assert len(files) == 1
        assert files[0] == '.hg'

    def check_commit(self, revno, data, text):
        ctx = self.repo.changectx(revno)
        ftx = ctx.filectx(self.file)
        assert ftx.data() == data
        assert ftx.description() == text
            
    def test_of_life_universe_and_everything(self):
        self.check_working_copy()
        for revno in self.commits.keys():
            cset = self.commits[revno]
            self.commit(self.file, cset[0], cset[1])            
            self.check_commit(revno, cset[0], cset[1])  # check correctness of data
            self.check_working_copy()  # check if any files created
        