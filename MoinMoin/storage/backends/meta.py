"""
    MoinMoin storage backends like NamespaceBackend and LayerBackend

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.interfaces import StorageBackend
from MoinMoin.storage.error import BackendError, NoSuchItemError
from MoinMoin.support.python_compatibility import sorted, partial
from MoinMoin.search import term


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

        def call(name, instance, *args, **kwargs):
            """
            Do the call.
            """
            return instance._call(name, *args, **kwargs)

        return partial(call, name, self)

    def _call(self, method, *args, **kwargs):
        """
        Call the method from the first matching backend with the given parameters.
        """
        raise NotImplementedError

    def _news_helper(self, timestamp, backends):
        """
        Used to implement on-the-fly news sorting
        from multiple backends.
        """
        _items = []
        for backend, bdata in backends:
            try:
                iterator = backend.news(timestamp)
                _items.append((iterator.next(), iterator, bdata))
            except StopIteration:
                pass

        while len(_items):
            _items.sort(reverse=True)
            value, iterator, bdata = _items[0]
            yield value, bdata
            try:
                nval = iterator.next()
                _items[0] = (nval, iterator, bdata)
            except StopIteration:
                del _items[0]


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

    def list_items(self, filter):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        for namespace, backend in self.backends.iteritems():
            for item in backend.list_items(filter):
                yield namespace + item

    def news(self, timestamp=0):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.news
        """
        _backends = []
        for namespace, backend in self.backends.iteritems():
            _backends.append((backend, namespace))
        for item, namespace in self._news_helper(timestamp, _backends):
            yield (item[0], item[1], namespace + item[2])

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

    def addUnderlay(self, backend):
        backend._layer_marked_underlay = True
        self.backends.append(backend)

    def list_items(self, filter):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        items = {}
        nounderlay = False
        # optimise a bit
        def check_not_underlay(t):
            if isinstance(t, term.NOT):
                if isinstance(filter.term, term.FromUnderlay):
                    return True
            return False

        if check_not_underlay(filter):
            nounderlay = True
            filter = term.TRUE
        elif isinstance(filter, term.AND):
            for t in filter.terms:
                if check_not_underlay(filter):
                    nounderlay = True
                    filter.remove(t)
                    break

        for backend in self.backends:
            if nounderlay and hasattr(backend, '_layer_marked_underlay'):
                continue

            for item in backend.list_items(filter):
                # don't list a page more than once if it is
                # present in multiple layers
                if item in items:
                    continue
                items[item] = True
                yield item

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        for backend in self.backends:
            if backend.has_item(name):
                return backend
        return None

    def news(self, timestamp=0):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.news
        """
        _backends = [(b, None) for b in self.backends]
        for item, dummy in self._news_helper(timestamp, _backends):
            yield item

    def _call(self, method, *args, **kwargs):
        """
        Call the method from the first matching backend with the given parameters.
        """
        for backend in self.backends:
            try:
                return getattr(backend, method)(*args, **kwargs)
            except NoSuchItemError:
                pass
        raise NoSuchItemError(_("No such item %r.") % args[0])


_ = lambda x: x
