==================
Wiki Configuration
==================

To change how moin behaves and looks like, you may customize it by editing
its configuration file (often called wikiconfig.py).

When editing the config, please note that this is Python code, so be careful
with indentation, only use multiples of 4 spaces to indent, no tabs!

It is a good idea to start from one of the sample configs provided with moin
and only do small careful changes, then trying it, then doing next change.
If you're not used to Python syntax, backup your last working config so you
can revert to it in case you make some hard to find typo or other error.

Python powered
==============

At first, you might wonder why we use Python code for configuration. It is
simply because it is powerful and we can make use of that power there.

One of Python's powerful features is class inheritance: you can inherit most
settings from a DefaultConfig class (which is defined in the moin code) and
just override the settings you want different from the defaults.

So, a typical wikiconfig.py works like this::

 from MoinMoin.config.default import DefaultConfig

 class Config(DefaultConfig):
     # a comment
     sometext = u'your value'
     somelist = [1, 2, 3]

Let's go through this line-by-line:

1. this gets the DefaultConfig class from the moin code
2. an empty line, for better readability
3. now we define a new class `Config` that inherits most stuff from
   `DefaultConfig`
4. with a `#` character you can write a comment into your config. This line (as
   well as all other following lines with Config settings) is indented by 4
   blanks, because Python defines blocks by indentation.
5. define a Config attribute called `sometext` with value u'your value' -
   the `u'...'` means that this is a unicode string.
6. define a Config attribute called `somelist` with value [1, 2, 3] - this is
   a list with the numbers 1, 2 and 3 as list elements.


Authentication
==============
MoinMoin uses a configurable `auth` list of authenticators, so the admin can
configure whatever he likes to allow for authentication. Moin processes this
list from left to right.

Each authenticator is an instance of some specific class, configuration of
the authenticators usually works by giving them keyword arguments. Most have
reasonable defaults, though.

MoinAuth
--------
This is the default authentication moin uses if you don't configure something
else. The user logs in by filling out the login form with username and
password, moin compares the password hash against the one stored in the user's
profile and if both match, the user is authenticated::

    from MoinMoin.auth import MoinAuth
    auth = [MoinAuth()]  # this is the default!


HTTPAuthMoin
------------
With HTTPAuthMoin moin does http basic auth all by itself (without help of
the web server)::

    from MoinMoin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin(autocreate=True)]

If configured like that, moin will request authentication by emitting a
http header. Browsers then usually show some login dialogue to the user,
asking for username and password. Both then gets transmitted to moin and it
is compared against the password hash stored in the user's profile.


OpenID
------
With OpenID moin can re-use the authentication done by some OpenID provider
(like Google, Yahoo, Microsoft or others)::

    from MoinMoin.auth.openidrp import OpenIDAuth
    auth = [OpenIDAuth()]

By default OpenID authentication accepts all OpenID providers. If you
like, you can configure what providers to allow (which ones you want to trust)
by adding their URLs to the trusted_providers keyword of OpenIDAuth. If left
empty, moin will allow all providers::

    # Allow google profile OpenIDs only:
    auth = [OpenIDAuth(trusted_providers=['https://www.google.com/accounts/o8/ud?source=profiles'])]

To be able to log in with OpenID, the user needs to have his OpenID stored
in his user profile.


GivenAuth
---------
With GivenAuth moin relies on the webserver doing the authentication and giving
the result to moin (usually via environment variable REMOTE_USER)::

    from MoinMoin.auth import GivenAuth
    auth = [GivenAuth(autocreate=True)]


Passwords
=========
As you might know, many users are bad at choosing reasonable passwords and some
are tempted to use passwords like 123456 everywhere.

To help the users choose reasonable passwords, moin has a simple builtin
password checker that does some sanity checks (the checker is enabled by
default), so users don't choose too short or too easy passwords.

If you don't like this and your site has rather low security requirements,
feel free to DISABLE the checker by::

    password_checker = None # no password checking


.. todo::

   describe more moin configuration


=====================
Logging configuration
=====================

By default, logging is configured to emit output on `stderr`. This will work
OK for the builtin server (will just show on the console) or for e.g. Apache2
(will be put into error.log).

Logging is very configurable and flexible due to the use of the `logging`
module of the Python standard library.

The configuration file format is described there:

http://www.python.org/doc/lib/logging-config-fileformat.html

There are also some logging configurations in the `examples/` directory.

Logging configuration needs to be done very early, usually it will be done
from your adaptor script (e.g. moin.wsgi)::

    from MoinMoin import log
    log.load_config('wiki/config/logging/logfile')

You have to fix that path to use a logging configuration matching your
needs.

Please note that the logging configuration has to be a separate file (don't
try this in your wiki configuration file)!

