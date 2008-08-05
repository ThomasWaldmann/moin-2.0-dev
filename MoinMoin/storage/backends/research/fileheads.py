from mercurial.node import short

def show_file_heads(ui, repo, filename):
    filelog = repo.file(filename)    
    for node in filelog.heads():
        rev = filelog.linkrev(node)
        print rev, ": ", short(repo[rev].node()) 

cmdtable = {"fileheads|fh": (show_file_heads, [], "hg fileheads FILE")}
