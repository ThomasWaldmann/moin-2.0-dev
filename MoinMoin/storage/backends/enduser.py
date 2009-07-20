import sys
from os import path, mkdir

from MoinMoin.error import ConfigurationError
from MoinMoin.storage.backends import fs, hg, memory, router


DATA = 'data'
USER = 'user'

FS_PREFIX = "fs:"
HG_PREFIX = "hg:"
MEMORY = "memory:"


def get_enduser_backend(backend_uri='fs:instance', mapping=None, user=None):
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
    def _create_folders(instance_folder):
        # create folders if they don't exist yet
        inst = instance_folder
        folders = (inst, path.join(inst, DATA), path.join(inst, USER))
        for folder in folders:
            try:
                mkdir(folder)
            except OSError:
                # If the folder already exists, even better!
                pass

    if mapping is user is None:
        if backend_uri.startswith(FS_PREFIX):
            # Aha! We want to use the fs backend
            instance_folder = backend_uri[len(FS_PREFIX):]
            _create_folders(instance_folder)

            data = fs.FSBackend(path.join(instance_folder, DATA))
            user = fs.FSBackend(path.join(instance_folder, USER))

        elif backend_uri.startswith(HG_PREFIX):
            instance_folder = backend_uri[len(HG_PREFIX):]
            _create_folders(instance_folder)

            data = hg.MercurialBackend(path.join(instance_folder, DATA))
            user = hg.MercurialBackend(path.join(instance_folder, USER))

        elif backend_uri == MEMORY:
            data = memory.MemoryBackend()
            user = memory.MemoryBackend()
        else:
            raise ConfigurationError("No proper backend uri provided. Given: %r" % backend_uri)

        mapping = [('/', data), ]

    backend = router.RouterBackend(mapping, user)
    return backend
