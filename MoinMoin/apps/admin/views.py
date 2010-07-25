# -*- coding: ascii -*-
"""
    MoinMoin - admin views
    
    This shows the user interface for wiki admins.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import werkzeug
from flask import request, g, url_for

from MoinMoin.apps.admin import admin

@admin.route('/')
def index():
    return "hello admin"


