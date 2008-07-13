"""
MoinMoin - Converter registry

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

_marker = object()

class Registry(object):
    def __init__(self):
        self._converters = []

    def get(self, input, output, default=_marker):
        """
        @param input Input MIME-Type
        @param output Input MIME-Type
        @param default Default value
        @return A converter or default value
        """
        for factory in self._converters:
            conv = factory(input, output)
            if conv is not None:
                return conv
        if default is _marker:
            raise TypeError("Couldn't find converter for %s to %s" % (input, output))
        return default

    def register(self, factory):
        if factory not in self._converters:
            self._converters.append(factory)

    def unregister(self, factory):
        self._converters.remove(factory)

default_registry = Registry()
