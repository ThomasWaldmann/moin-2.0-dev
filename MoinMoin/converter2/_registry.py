"""
MoinMoin - Converter registry

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util.registry import RegistryBase

class Registry(RegistryBase):
    def get(self, request, input, output):
        """
        @param input Input MIME-Type
        @param output Input MIME-Type
        @return A converter or default value
        """
        ret = self._get(request, input, output)
        if ret:
            return ret
        raise TypeError(u"Couldn't find converter for %s to %s" % (input, output))

default_registry = Registry()
