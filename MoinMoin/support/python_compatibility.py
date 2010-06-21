"""
    MoinMoin - Support Package

    Stuff for compatibility with older Python versions

    @copyright: 2007 Heinrich Wendel <heinrich.wendel@gmail.com>,
                2009-2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

min_req_exc = Exception("Minimum requirement for MoinMoin is Python 2.6.")

try:
    from functools import partial # Python >= 2.5 needed
except (NameError, ImportError):
    raise min_req_exc

try:
    import hashlib, hmac # Python >= 2.5 needed
    hash_new = hashlib.new
    def hmac_new(key, msg, digestmod=hashlib.sha1):
        return hmac.new(key, msg, digestmod)

except (NameError, ImportError):
    raise min_req_exc

