"""
MoinMoin - Converter registry

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

_marker = object()

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
        self._converters = []

    def _sort(self):
        self._converters.sort(key=lambda a: a.priority)

    def get(self, request, input, output, default=_marker):
        """
        @param input Input MIME-Type
        @param output Input MIME-Type
        @param default Default value
        @return A converter or default value
        """
        for entry in self._converters:
            conv = entry.factory(request, input, output)
            if conv is not None:
                return conv
        if default is _marker:
            raise TypeError(u"Couldn't find converter for %s to %s" % (input, output))
        return default

    def register(self, factory, priority=PRIORITY_MIDDLE):
        if factory not in self._converters:
            self._converters.append(self._Entry(factory, priority))
            self._sort()

    def unregister(self, factory):
        self._converters.remove(factory)
        self._sort()

default_registry = Registry()
