"""
    MoinMoin storage backends like NamespaceBackend and LayerBackend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.error import BackendError, NoSuchItemError


class MetaBackend(StorageBackend):
    """
    Super class which does the _call methods calls. Subclasses need to implement the missing
    backend methods and _call.
    """

    def __init__(self, backends):
        """
        Initialize the namespaces.
        """
        self.backends = backends

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_has_item
        """
        return self._call("has_item", name)

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        return self._call("create_item", name)

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        return self._call("remove_item", name)

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        return self._call("list_revisions", name)

    def current_revision(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        return self._call("current_revision", name)

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        return self._call("has_revision", name, revno)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revision
        """
        return self._call("create_revision", name, revno)

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revision
        """
        return self._call("remove_revision", name, revno)

    def get_metadata(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata
        """
        return self._call("get_metadata", name, revno)

    def set_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.set_metadata
        """
        return self._call("set_metadata", name, revno, metadata)

    def remove_metadata(self, name, revno, keylist):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_metadata
        """
        return self._call("remove_metadata", name, revno, keylist)

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        return self._call("get_data_backend", name, revno)

    def _call(self, method, *args):
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
            raise BackendError("Root ('/') backend is missing from configuration.")

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
        keys = self.backends.keys()
        keys.sort()
        keys.reverse()
        for namespace in keys:
            if name.startswith(namespace):
                name = name.replace(namespace, "", 1)
                return name, self.backends[namespace]
        raise NoSuchItemError("No such item %r." % name)

    def _call(self, method, name, *args):
        """
        Call the method from the first matching backend with the given parameters.
        """
        name, backend = self._get_backend(name)

        return getattr(backend, method)(name, *args)


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
        return False

    def _call(self, method, *args):
        """
        Call the method from the first matching backend with the given parameters.
        """
        for backend in self.backends:
            try:
                return getattr(backend, method)(*args)
            except NoSuchItemError:
                pass
        raise NoSuchItemError("No such item %r." % args[0])
