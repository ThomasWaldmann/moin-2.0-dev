"""
MoinMoin - Converter support

Converters are used to convert between formats or between different featuresets
of one format.

There are usualy three types of converters:
- Between an input format like Moin Wiki or Creole and the internal tree
  representation.
- Between the internal tree and an output format like HTML.
- Between different featuresets of the internal tree representation like URI
  types or macro expansion.

TODO: Merge with new-style macros.

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util.registry import Registry as _RegistryBase


class Registry(_RegistryBase):
    def get(self, request, input, output):
        """
        @param input Input MIME-Type
        @param output Input MIME-Type
        @return A converter or default value
        """
        ret = super(Registry, self).get(request, input, output)
        if ret:
            return ret
        raise TypeError(u"Couldn't find converter for %s to %s" % (input, output))


# TODO: Move somewhere else. Also how to do that for per-wiki modules?
def _load():
    import imp, os, sys
    for path in __path__:
        for root, dirs, files in os.walk(path):
            del dirs[:]
            for file in files:
                if file.startswith('_') or not file.endswith('.py'):
                    continue
                module = file[:-3]
                module_complete = __name__ + '.' + module
                if module_complete in sys.modules:
                    continue
                info = imp.find_module(module, [root])
                try:
                    try:
                        imp.load_module(module_complete, *info)
                    except Exception, e:
                        import MoinMoin.log as logging
                        logger = logging.getLogger(__name__)
                        logger.exception("Failed to import converter package %s: %s" % (module, e))
                finally:
                    info[0].close()

default_registry = Registry()

_load()
