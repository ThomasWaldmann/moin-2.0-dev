"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel,
    @copyright: 2008 MoinMoin:PawelPacana,
    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import shutil
from os import path

from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError
from MoinMoin.storage.backends import fs, memory, router


def get_enduser_backend(backend_uri='instance/', mapping=None, user=None):
    """
    To ease storage configuration for the user, he may provide just a backend_uri
    or a mapping and a backend for user storage (allowing fine grained control over
    storage configuration).
    If he chooses to provide a backend uri, data and user backends are constructed
    automatically and encapsulated in a RouterBackend.
    If the user chooses to provide mapping and user backend himself, those are just
    passed to the RouterBackend as they are.
    If the user did not specify anything, we use a FSBackend with user/ and data/
    subdirectories by default.
    """
    if mapping is user is None:
        if path.isdir(backend_uri):
            data = fs.FSBackend(path.join(backend_uri, 'data'))
            user = fs.FSBackend(path.join(backend_uri, 'user'))
        elif backend_uri == ':memory:':
            data = memory.MemoryBackend()
            user = memory.MemoryBackend()

        mapping = [('/', data),]

    backend = router.RouterBackend(mapping, user)
    return backend


def clone(source, destination, verbose=False, only_these=[]):
    """
    Create exact copy of source Backend with all the Items in the given
    destination Backend whose names are given in the only_these list.
    Return a tuple consisting of three dictionaries (Item name:Revsion numbers list):
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

    if verbose:
        import sys, os
        # reopen stdout file descriptor with write mode
        # and 0 as the buffer size (unbuffered)
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        sys.stdout.write("[converting %s to %s]: " % (source.__class__.__name__,
                                                       destination.__class__.__name__, ))
    converts, skips, fails = {}, {}, {}

    for item in source.iteritems():
        name = item.name
        if only_these and name not in only_these:
            continue
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
                if same_revision(existing_revision, revision):
                    try:
                        skips[name].append(revision.revno)
                    except KeyError:
                        skips[name] = [revision.revno]
                    if verbose:
                        sys.stdout.write("s")
                else:
                    try:
                        fails[name].append(revision.revno)
                    except KeyError:
                        fails[name] = [revision.revno]
                    if verbose:
                        sys.stdout.write("F")
            else:
                for k, v in revision.iteritems():
                    new_rev[k] = v
                new_rev.timestamp = revision.timestamp
                shutil.copyfileobj(revision, new_rev)

                new_item.commit()
                try:
                    converts[name].append(revision.revno)
                except KeyError:
                    converts[name] = [revision.revno]
                if verbose:
                    sys.stdout.write(".")

    if verbose:
        sys.stdout.write("\n")
    return converts, skips, fails
