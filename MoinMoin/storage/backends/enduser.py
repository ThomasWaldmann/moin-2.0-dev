from os import path

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

        mapping = [('/', data), ]

    backend = router.RouterBackend(mapping, user)
    return backend
