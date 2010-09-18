# -*- coding: iso-8859-1 -*-
"""
    MoinMoin caching module

    @copyright: 2001-2004 by Juergen Hermann <jh@web.de>,
                2006-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:ThomasPfaff
    @license: GNU GPL, see COPYING for details.
"""

import hashlib
import hmac

from flask import current_app as app


def cache_key(_secret=None, **kw):
    """
    Calculate a (hard-to-guess) cache key

    Important key properties:
    * The key must be hard to guess (so you do not need permission checks
      when a user access the cache via URL - if he knows the key, he is allowed
      to see the contents). Because of that we use hmac and a server secret
      to compute the key.
    * The key must be different for different **kw.

    @param **kw: keys/values to compute cache key from
    @param _secret: secret for hMAC calculation (default: use secret from cfg)
    """
    hmac_data = repr(kw)
    if _secret is None:
        _secret = app.cfg.secrets['action/cache']
    return hmac.new(_secret, hmac_data, digestmod=hashlib.sha1).hexdigest()

