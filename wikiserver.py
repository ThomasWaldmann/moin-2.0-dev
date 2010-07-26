#!/usr/bin/env python
"""
    Start script for the Wiki server.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from os import path
support = path.abspath(path.join(path.dirname(__file__), 'MoinMoin', 'support'))

import sys
sys.path.insert(0, support)

from MoinMoin import app

app.run(host='127.0.0.1', port=8080, debug=True)

