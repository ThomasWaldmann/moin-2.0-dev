"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @copyright: 2008 MoinMoin:PawelPacana
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError

def clone(source, destination, verbose=False):
    """
    Creates exact copy of source Backend with all its Items in the given
    destination Backend. Optionally outputs results of copy.
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
        from MoinMoin import log
        logging = log.getLogger(__name__)
    skips, fails = {}, {}

    for revision in source.history(reverse=False):
        name = revision.item.name
        try:
            new_item = destination.get_item(name)
        except NoSuchItemError:
            new_item = destination.create_item(name)
            new_item.change_metadata()
            for k, v in revision.item.iteritems():
                new_item[k] = v
            new_item.publish_metadata()

        new_rev = copy.create_revision(revision.revo)
        for k, v in revision.iteritems():
            try:
                new_rev[k] = v
            except TypeError:
                new_rev[k] = tuple(v)
        new_rev.timestamp = revision.timestamp
        shutil.copyfileobj(revision, new_rev)

        try:
            new_item.commit()
            if verbose:
                logging.info('.')
        except RevisionAlreadyExistsError:
            if compare_revision(new_rev, revision):
                try:
                    skips[name].append(revision.revno)
                except KeyError:
                    skips[name] = [revision.revno]
                if verbose:
                    logging.info('s')
            else:
                try:
                    fails[name].append(revision.revno)
                except KeyError:
                    fails[name] = [revision.revno]
                if verbose:
                    logging.info('F')
    return skips, fails
