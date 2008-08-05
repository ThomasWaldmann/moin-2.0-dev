from mercurial.node import short

def show_extra_dict(ui, repo, **opts):
    """Show contents of changesets extra dictionary"""
    def show_dict(repo, revno):
        ctx = repo[revno]
        print "%d:%s" % (ctx.rev(), short(ctx.node()))
        for k,v in ctx.extra().iteritems():
            print "\t%s : %s" % (k, v)
        print
    
    if opts['rev']:
        show_dict(repo, opts['rev'])
    else:
        for revno in reversed(list(iter(repo))):
            show_dict(repo, revno)

cmdtable = { "showextra|se": (show_extra_dict, 
                              [('r', 'rev', '', 'revision'),],
                              "hg showextra [-r REV]")
}