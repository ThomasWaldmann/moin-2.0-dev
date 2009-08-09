"""
    MoinMoin - Backends

    This package contains code for the backends of the new storage layer.

    @copyright: 2007 MoinMoin:HeinrichWendel,
    @copyright: 2008 MoinMoin:PawelPacana,
    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

import sys
from os import makedirs
from os.path import join

from MoinMoin.storage.serialization import unserialize
from MoinMoin.storage.error import NoSuchItemError, RevisionAlreadyExistsError
from MoinMoin.storage.backends import fs, memory


CONTENT = 'content'
USERPROFILES = 'userprofiles'
TRASH = 'trash'

FS_PREFIX = "fs:"
HG_PREFIX = "hg:"
MEMORY = "memory:"


def create_simple_mapping(backend_uri='fs:instance', content_acl=None):
    """
    When configuring storage, the admin needs to provide a namespace_mapping.
    To ease creation of such a mapping, this function provides sane defaults
    for different types of backends.
    The admin can just call this function, pass a hint on what type of backend
    he wants to use and a proper mapping is returned.
    If the user did not specify anything, we use three FSBackends with user/,
    data/ and trash/ directories by default.
    """
    def _create_folders(instance_folder):
        # create folders if they don't exist yet
        inst = instance_folder
        folders = (join(inst, CONTENT), join(inst, USERPROFILES), join(inst, TRASH))
        for folder in folders:
            try:
                makedirs(folder)
            except OSError:
                # If the folder already exists, even better!
                pass
        return folders

    def _create_backends(BackendClass, instance_folder):
        # creates the actual backends
        datadir, userdir, trashdir = _create_folders(instance_folder)
        data = BackendClass(datadir)
        user = BackendClass(userdir)
        trash = BackendClass(trashdir)
        return data, user, trash


    if backend_uri.startswith(FS_PREFIX):
        # Aha! We want to use the fs backend
        instance_folder = backend_uri[len(FS_PREFIX):]
        data, user, trash = _create_backends(fs.FSBackend, instance_folder)

    elif backend_uri.startswith(HG_PREFIX):
        # Due to external dependency that may not always be present, import hg backend here:
        from MoinMoin.storage.backends import hg
        instance_folder = backend_uri[len(HG_PREFIX):]
        data, user, trash = _create_backends(hg.MercurialBackend, instance_folder)

    elif backend_uri == MEMORY:
        data = memory.MemoryBackend()
        user = memory.MemoryBackend()
        trash = memory.MemoryBackend()

    else:
        raise ConfigurationError("No proper backend uri provided. Given: %r" % backend_uri)

    # XXX How to properly get these values from the users config?
    ns_content = '/'
    ns_user_profile = 'UserProfile/'
    ns_trash = 'Trash/'
    if not content_acl:
        content_acl = dict(
            before="",
            default="All:read,write,admin,create,destroy", # MMDE -> superpowers by default
            after="",
            hierarchic=False,
        )
    user_profile_acl = dict(
        before="All:read,write,admin,create,destroy", # TODO: change this before release, just for development
        default="",
        after="",
        hierarchic=False,
    )

    namespace_mapping = [
                    (ns_trash, trash, content_acl),
                    (ns_user_profile, user, user_profile_acl),
                    (ns_content, data, content_acl),
    ]

    return namespace_mapping


def upgrade_syspages(request, packagepath):
    """
    Upgrade the wiki's system pages from an XML file.

    @type packagepath: basestring
    @param packagepath: Name of the item containing the system pages xml as data.
    """
    # !! Uses ACL-free storage !!
    storage = request.unprotected_storage
    try:
        item = storage.get_item(packagepath)
        rev = item.get_revision(-1)
    except NoSuchItemError, NoSuchRevisionError:
        raise BackendError("No such item %r." % packagepath)

    tmp_backend = memory.MemoryBackend()
    unserialize(tmp_backend, rev)

    # clone to real backend from config WITHOUT checking ACLs!
    storage.clone(tmp_backend)

