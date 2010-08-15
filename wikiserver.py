#!/usr/bin/env python
"""
    Start script for the Wiki server.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import sys
from os import path

here = path.abspath(path.dirname(__file__))

support = path.join(here, 'MoinMoin', 'support')
sys.path.insert(0, support)

from MoinMoin import app

try:
    app.config.from_pyfile(path.join(here, 'wikiconfig_local.py'))
except IOError, err:
    if 'wikiconfig_local' not in str(err):
        raise
    # it couldn't load from wikiconfig_local.py, retry with wikiconfig.py
    app.config.from_pyfile(path.join(here, 'wikiconfig.py'))

host = app.config.get('HOST', '127.0.0.1')
port = app.config.get('PORT', 8080)
debug = app.config.get('DEBUG', True) # XXX change default to False later

app.run(host=host, port=port, debug=debug)

