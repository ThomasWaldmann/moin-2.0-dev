"""
MoinMoin - Converter support

@copyright: 2008 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from _registry import default_registry

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
                    imp.load_module(module_complete, *info)
                finally:
                    info[0].close()

_load()
