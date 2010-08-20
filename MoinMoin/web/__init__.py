# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Low-level interface code between the wiki and the web

    This package contains everything related to interfacing the wiki with
    the actual request from the web. It replaces the former packages
    `MoinMoin.request` and `MoinMoin.server`. There is code for convenient
    access to the supplied request parameters (using the werkzeug library),
    wrappers (called contexts) that try to capture the use of the former
    Request-objects in MoinMoin, session handling and interfaces to
    common webserver deployment methods.

    @copyright: 2008-2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""
