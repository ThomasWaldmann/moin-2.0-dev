import sys
from os import path, mkdir

from MoinMoin.error import ConfigurationError
from MoinMoin.storage.backends import fs, memory, router


DATA = 'data'
USER = 'user'

FS_PREFIX = "fs:"


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
    # TODO Add HG!
    if mapping is user is None:
        if backend_uri.startswith(FS_PREFIX):
            # Aha! We want to use the fs backend
            # create folders if they don't exist yet
            instance_folder = backend_uri[len(FS_PREFIX):]
            try:
                mkdir(instance_folder)
            except OSError:
                pass

            for folder in (DATA, USER):
                try:
                    mkdir(path.join(instance_folder, folder))
                except OSError:
                    # If the folder already exists, even better!
                    pass

            data = fs.FSBackend(path.join(instance_folder, DATA))
            user = fs.FSBackend(path.join(instance_folder, USER))
        elif backend_uri == ':memory:':
            data = memory.MemoryBackend()
            user = memory.MemoryBackend()
        else:
            raise ConfigurationError("No proper backend uri provided. Given: %r" % backend_uri)

        mapping = [('/', data), ]

    backend = router.RouterBackend(mapping, user)
    return backend
