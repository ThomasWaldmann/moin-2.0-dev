"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel,
    @copyright: 2008 MoinMoin:PawelPacana,
    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import shutil
import sys
import os

from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError


def copy_item(item, destination, verbose=False, name=None):
    if name is None:
        name = item.name
    status = dict(converts={}, skips={}, fails={})
    progress_char = dict(converts='.', skips='s', fails='F')
    revisions = item.list_revisions()

    for revno in revisions:
        revision = item.get_revision(revno)
        try:
            new_item = destination.get_item(name)
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
            st = same_revision(existing_revision, revision) and 'skips' or 'fails'
        else:
            for k, v in revision.iteritems():
                new_rev[k] = v
            new_rev.timestamp = revision.timestamp
            shutil.copyfileobj(revision, new_rev)
            new_item.commit()
            st = 'converts'
        try:
            status[st][name].append(revision.revno)
        except KeyError:
            status[st][name] = [revision.revno]
        if verbose:
            sys.stdout.write(progress_char[st])

    return status['converts'], status['skips'], status['fails']


def clone(source, destination, verbose=False, only_these=[]):
    """
    Create exact copy of source Backend with all the Items in the given
    destination Backend whose names are given in the only_these list.
    Return a tuple consisting of three dictionaries (Item name:Revision numbers list):
    converted, skipped and failed Items dictionary.
    """
    def same_revision(rev1, rev2):
        if rev1.timestamp != rev2.timestamp:
            return False
        for k, v in rev1.iteritems():
            if rev2[k] != v:
                return False
        if rev1.size != rev2.size:
            return False
        return True

    def item_generator(source, only_these):
        if only_these:
            for name in only_these:
                try:
                    yield source.get_item(name)
                except NoSuchItemError:
                    # TODO Find out why this fails sometimes.
                    #sys.stdout.write("Unable to copy %s\n" % itemname)
                    pass
        else:
            for item in source.iteritems():
                yield item

    if verbose:
        # reopen stdout file descriptor with write mode
        # and 0 as the buffer size (unbuffered)
        sys.stdout = os.fdopen(os.dup(sys.stdout.fileno()), 'w', 0)
        sys.stdout.write("[converting %s to %s]: " % (source.__class__.__name__,
                                                       destination.__class__.__name__, ))

    converts, skips, fails = {}, {}, {}
    for item in item_generator(source, only_these):
        c, s, f = copy_item(item, destination, verbose)
        converts.update(c)
        skips.update(s)
        fails.update(f)

    if verbose:
        sys.stdout.write("\n")
    return converts, skips, fails

