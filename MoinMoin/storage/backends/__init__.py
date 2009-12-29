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
from MoinMoin.storage.backends import fs, fs2, memory


CONTENT = 'content'
USERPROFILES = 'userprofiles'
TRASH = 'trash'

FS_PREFIX = "fs:"
FS2_PREFIX = "fs2:"
HG_PREFIX = "hg:"
SQLA_PREFIX = "sqla:"
MEMORY_PREFIX = "memory:"


def create_simple_mapping(backend_uri='fs:instance', content_acl=None, user_profile_acl=None):
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
        contentdir, userprofiledir, trashdir = _create_folders(instance_folder)
        content = BackendClass(contentdir)
        userprofile = BackendClass(userprofiledir)
        trash = BackendClass(trashdir)
        return content, userprofile, trash


    if backend_uri.startswith(FS_PREFIX):
        # Aha! We want to use the fs backend
        instance_folder = backend_uri[len(FS_PREFIX):]
        content, userprofile, trash = _create_backends(fs.FSBackend, instance_folder)

    elif backend_uri.startswith(FS2_PREFIX):
        # Aha! We want to use the fs2 backend
        instance_folder = backend_uri[len(FS2_PREFIX):]
        content, userprofile, trash = _create_backends(fs2.FS2Backend, instance_folder)

    elif backend_uri.startswith(HG_PREFIX):
        # Due to external dependency that may not always be present, import hg backend here:
        from MoinMoin.storage.backends import hg
        instance_folder = backend_uri[len(HG_PREFIX):]
        content, userprofile, trash = _create_backends(hg.MercurialBackend, instance_folder)

    elif backend_uri.startswith(SQLA_PREFIX):
        # XXX Move this import to the module level once sqlalchemy is in MoinMoin.support
        from MoinMoin.storage.backends.sqla import SQLAlchemyBackend
        db_uri = backend_uri[len(SQLA_PREFIX):]

        content = SQLAlchemyBackend(db_uri % dict(nsname=CONTENT))
        userprofile = SQLAlchemyBackend(db_uri % dict(nsname=USERPROFILES))
        trash = SQLAlchemyBackend(db_uri % dict(nsname=TRASH))

    elif backend_uri == MEMORY_PREFIX:
        content = memory.MemoryBackend()
        userprofile = memory.MemoryBackend()
        trash = memory.MemoryBackend()

    else:
        raise ConfigurationError("No proper backend uri provided. Given: %r" % backend_uri)

    if not content_acl:
        content_acl = dict(
            before=u'',
            default=u'All:read,write,create', # mostly harmless by default
            after=u'',
            hierarchic=False,
        )

    if not user_profile_acl:
        user_profile_acl = dict(
            before=u'All:', # harmless by default
            default=u'',
            after=u'',
            hierarchic=False,
        )

    # XXX How to properly get these values from the users config?
    ns_content = u'/'
    ns_user_profile = u'UserProfile/'
    ns_trash = u'Trash/'

    namespace_mapping = [
                    (ns_trash, trash, content_acl),
                    (ns_user_profile, userprofile, user_profile_acl),
                    (ns_content, content, content_acl),
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

