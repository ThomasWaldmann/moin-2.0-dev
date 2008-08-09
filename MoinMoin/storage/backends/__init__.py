"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

import shutil

from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError

def clone(source, destination, verbose=False):
    """
    Create exact copy of source Backend with all its Items in the given
    destination Backend. Return a tuple consisting of:
    - converted, skipped, failed count list,
    - skipped Item:Revsion numbers list dict,
    - failed Item:Revision numbers list dict
    """
    def compare_revision(rev1, rev2):
        if rev1.timestamp != rev2.timestamp:
            return False
        for k, v in rev1.iteritems():
            if rev2[k] != v:
                return False
        if rev1.size != rev2.size:
            return False
        # else:
        # comparing data may hurt a lot
        return True

    if verbose:
        import sys, os
        # reopen stdout file descriptor with write mode
        # and 0 as the buffer size (unbuffered)
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        sys.stdout.write("[connverting %s to %s]: " % (source.__class__.__name__,
                                                       destination.__class__.__name__, ))
    count = [0, 0, 0]
    skips, fails = {}, {}

    for revision in source.history(reverse=False):
        name = revision.item.name
        try:
            new_item = destination.get_item(name)
            count[0] += 1
        except NoSuchItemError:
            new_item = destination.create_item(name)
            new_item.change_metadata()
            for k, v in revision.item.iteritems():
                new_item[k] = v
            new_item.publish_metadata()

        try:
            new_rev = new_item.create_revision(revision.revno)
        except RevisionAlreadyExistsError:
            existing_revision = new_item.get_revision(revision.revno)
            if compare_revision(existing_revision, revision):
                count[1] += 1
                try:
                    skips[name].append(revision.revno)
                except KeyError:
                    skips[name] = [revision.revno]
                if verbose:
                    sys.stdout.write("s")
            else:
                count[2] += 1
                try:
                    fails[name].append(revision.revno)
                except KeyError:
                    fails[name] = [revision.revno]
                if verbose:
                    sys.stdout.write("F")
        else:
            for k, v in revision.iteritems():
                try:
                    new_rev[k] = v
                except TypeError:           # remove as soon as this gets fixed: see 17:32 < ThomasWaldmann>
                    new_rev[k] = tuple(v)   # http://www.moinmo.in/MoinMoinChat/Logs/moin-dev/2008-08-09
            new_rev.timestamp = revision.timestamp
            shutil.copyfileobj(revision, new_rev)

            new_item.commit()
            count[0] += 1
            if verbose:
                sys.stdout.write(".")

    if verbose:
        sys.stdout.write("\n")
    return count, skips, fails
