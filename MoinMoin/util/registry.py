"""
MoinMoin - Module registry

Every module registers a factory for itself at the registry with a given
priority.  During the lookup each factory is called with the given arguments and
can return a callable to consider itself as a match.

@copyright: 2008,2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""


class Registry(object):
    PRIORITY_REALLY_FIRST = -20
    PRIORITY_FIRST = -10
    PRIORITY_MIDDLE = 0
    PRIORITY_LAST = 10
    PRIORITY_REALLY_LAST = 20

    class _Entry(object):
        def __init__(self, factory, priority):
            self.factory, self.priority = factory, priority

        def __cmp__(self, other):
            if isinstance(other, self.__class__):
                return cmp(self.factory, other.factory)
            return cmp(self.factory, other)

    def __init__(self):
        self._entries = []

    def _sort(self):
        self._entries.sort(key=lambda a: a.priority)

    def get(self, *args, **kw):
        """
        Lookup a matching module

        Each registered factory is called with the given arguments and
        the first matching wins.
        """
        for entry in self._entries:
            conv = entry.factory(*args, **kw)
            if conv is not None:
                return conv

    def register(self, factory, priority=PRIORITY_MIDDLE):
        """
        Register a factory

        @param factory: Factory to register. Callable, have to return a class
        """
        if factory not in self._entries:
            self._entries.append(self._Entry(factory, priority))
            self._sort()

    def unregister(self, factory):
        """
        Unregister a factory

        @param: factory: Factory to unregister
        """
        self._entries.remove(factory)
