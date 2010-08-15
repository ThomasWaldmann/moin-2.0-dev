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

app.run(host='127.0.0.1', port=8080, debug=True)

