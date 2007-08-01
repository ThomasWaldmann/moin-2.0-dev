"""
    MoinMoin storage backends like NamespaceBackend and LayerBackend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.error import BackendError, NoSuchItemError


class Callable(object):
    """
    Class that just does a call to instance.name with the given parameters.
    """
    name = ""
    instance = None

    def __init__(self, name, instance):
        """
        Init parameters.
        """
        self.name = name
        self.instance = instance

    def call(self, *args, **kwargs):
        """
        Do the call.
        """
        return self.instance._call(self.name, *args, **kwargs)


class MetaBackend(object):
    """
    Super class which does the _call methods calls. Subclasses need to implement the missing
    backend methods and _call.
    """

    __implements__ = StorageBackend

    def __init__(self, backends):
        """
        Initialize the namespaces.
        """
        self.backends = backends

    def __getattr__(self, name):
        """
        Get attribute from other backend if we don't have one.
        """
        return Callable(name, self).call

    def _call(self, method, *args, **kwargs):
        """
        Call the method from the first matching backend with the given parameters.
        """
        raise NotImplementedError


class NamespaceBackend(MetaBackend):
    """
    This class implements backends structured via namespaces.

    e.g. /tmp/ -> TmpBackend
         /    -> PageBackend
    """

    def __init__(self, backends):
        """
        Make sure all keys end with / and don't start with / for easier handling.
        """
        if not "/" in backends:
            raise BackendError(_("Root ('/') backend is missing from configuration."))

        new_backends = dict()
        for namespace, backend in backends.iteritems():
            if not namespace.endswith("/"):
                namespace += "/"
            if namespace.startswith("/"):
                namespace = namespace[1:]
            new_backends[namespace] = backend

        MetaBackend.__init__(self, new_backends)

    def list_items(self, filters=None):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        items = []
        for namespace, backend in self.backends.iteritems():
            items.extend([namespace + item for item in backend.list_items(filters) if item not in items])
        items.sort()
        return items

    def _get_backend(self, name):
        """
        Returns the backend that should contain the given item.
        """
        for namespace in sorted(self.backends, reverse=True):
            if name.startswith(namespace):
                name = name.replace(namespace, "", 1)
                return name, self.backends[namespace]
        raise NoSuchItemError(_("No such item %r.") % name)

    def _call(self, method, name, *args, **kwargs):
        """
        Call the method from the first matching backend with the given parameters.
        """
        name, backend = self._get_backend(name)

        return getattr(backend, method)(name, *args, **kwargs)


class LayerBackend(MetaBackend):
    """
    This class implements the underlay backend structure. The requested page will
    be searched in the order the backends appear in the configuration, first fit.
    """

    def list_items(self, filters=None):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        items = []
        for backend in self.backends:
            items.extend(backend.list_items(filters))
        items.sort()
        return items

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        for backend in self.backends:
            if backend.has_item(name):
                return backend
        return None

    def _call(self, method, *args, **kwargs):
        """
        Call the method from the first matching backend with the given parameters.
        """
        for backend in self.backends:
            try:
                return getattr(backend, method)(*args, **kwargs)
            except NoSuchItemError:
                pass
        raise NoSuchItemError(_("No such item %r.") % method)


_ = lambda x: x
