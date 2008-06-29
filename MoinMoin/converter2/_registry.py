"""
MoinMoin - Converter registry

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

class Registry(object):
    def __init__(self):
        self._converters = []

    def get(self, input, output):
        """
        @param input Input MIME-Type
        @param output Input MIME-Type
        @return A converter
        """
        for factory in self._converters:
            conv = factory(input, output)
            if conv is not None:
                return conv
        raise TypeError

    def register(self, factory):
        if factory not in self._converters:
            self._converters.append(factory)

    def unregister(self, factory):
        self._converters.remove(factory)
