#!/usr/bin/env python
"""
    Start script for the Wiki server.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import sys
from os import path

MANUALLY = False # use True and adjust values below if False doesn't work for you

if MANUALLY:
    # hint: use None as value if the code already is in sys.path
    support_code = '/path/to/code/MoinMoin/support'
    moin_code = '/path/to/code'
    wiki_config = '/path/to/configs/wikiconfig.py'

else:
    # try magic for users who just unpack the moin archive or
    # developers who just run wikiserver.py from their workdir

    # directory where THIS file is located
    here = path.abspath(path.dirname(__file__))

    # support libraries that are bundled with moin:
    support_code = path.join(here, 'MoinMoin', 'support')
    if not path.exists(support_code):
        support_code = None # no idea where it is

    # moin's own code:
    moin_code = here
    if not path.exists(path.join(moin_code, 'MoinMoin')):
        moin_code = None # no idea where it is

    # wiki configuration:
    wiki_config = path.join(here, 'wikiconfig_local.py') # for development
    if not path.exists(wiki_config):
        wiki_config = path.join(here, 'wikiconfig.py') # normal usage


if support_code:
    # add the parent dir of the support code libraries to sys.path,
    # to make import work:
    sys.path.insert(0, support_code)

if moin_code:
    # add the parent dir of the MoinMoin code to sys.path,
    # to make import work:
    sys.path.insert(0, moin_code)


# app is the Flask application
from MoinMoin import create_app
app = create_app(wiki_config)

# please note: if you want to do some wsgi app wrapping, do it like shown below:
#app.wsgi_app = somewrapper(app.wsgi_app)

# get some configuration values for the builtin server:
host = app.config.get('HOST', '127.0.0.1')
port = app.config.get('PORT', 8080)
debug = app.config.get('DEBUG', True) # XXX change default to False later

# run the builtin server:
app.run(host=host, port=port, debug=debug)

