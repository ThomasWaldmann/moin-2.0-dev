=============
Configuration
=============

There are basically 2 things needing configuration:
* the web server (IP address, port, hostname, ...)
* the MoinMoin wiki engine (how the wiki behaves)

Builtin Web Server (easy)
=========================
Moin comes with some simple builtin web server (provided by werkzeug), which
is suitable for development, debugging, personal and small group wikis.

It is not made for serving bigger loads, but it is easy to use.

To start moin using the builtin web server, just run "moin".

If you'ld like to see all subcommands and options of the moin command, use:
$ ./moin help
$ ./moin moin --help

Example:
$ ./moin moin --config /srv/wiki/wikiconfig.py --host 1.2.3.4 --port 7777

Use an absolute path for the wikiconfig.py!

.. todo::

   add stuff above to man page and reference man page from here

External Web Server (advanced)
==============================
We won't go into details about this, because every web server software is
different and has its own documentation (please read it). Also, in general,
server administration requires advanced experience with the operating system,
permissions management, dealing with security, the server software, etc.

What you need to achieve is that your web server talks via WSGI to moin.
General infos about WSGI can be found on http://wsgi.org/.

For example, for Apache2 there is mod_wsgi, which is a very good choice and
has nice own documentation. See also the commented moin.wsgi file we provide.

If your web server can't directly talk via WSGI to moin, you maybe want to use
some middleware like flup translating fastcgi, ajp, scgi, cgi to WSGI. Flup
also has its own docs. Avoid using cgi, if possible, it is SLOW.


Wiki Engine
===========
To change how moin behaves and looks like, you may customize it by editing
its configuration file (often called wikiconfig.py).

When editing the config, please note that this is Python code, so be careful
with indentation, only use multiples of 4 spaces to indent, no tabs!

It is a good idea to start from one of the sample configs provided with moin
and only do small careful changes, then trying it, then doing next change.
If you're not used to Python syntax, backup your last working config so you
can revert to it in case you make some hard to find typo or other error.


Authentication
--------------
MoinMoin uses a configurable `auth` list of authenticators, so the admin can
configure whatever he likes to allow for authentication. Moin processes this
list from left to right.

Each authenticator is an instance of some specific class, configuration of
the authenticators usually works by giving them keyword arguments. Most have
reasonable defaults, though.

MoinAuth
~~~~~~~~
This is the default authentication moin uses if you don't configure something
else. The user logs in by filling out the login form with username and
password, moin compares the password hash against the one stored in the user's
profile and if both match, the user is authenticated::

    from MoinMoin.auth import MoinAuth
    auth = [MoinAuth()]  # this is the default!


HTTPAuthMoin
~~~~~~~~~~~~
With HTTPAuthMoin moin does http basic auth all by itself (without help of
the web server)::

    from MoinMoin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin(autocreate=True)]

If configured like that, moin will request authentication by emitting a
http header. Browsers then usually show some login dialogue to the user,
asking for username and password. Both then gets transmitted to moin and it
is compared against the password hash stored in the user's profile.


OpenID
~~~~~~
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
~~~~~~~~~
With GivenAuth moin relies on the webserver doing the authentication and giving
the result to moin (usually via environment variable REMOTE_USER)::

    from MoinMoin.auth import GivenAuth
    auth = [GivenAuth(autocreate=True)]


Passwords
---------
As you might know, many users are bad at choosing reasonable passwords and some
are tempted to use passwords like 123456 everywhere.

To help the users choose reasonable passwords, moin has a simple builtin
password checker that does some sanity checks (the checker is enabled by
default), so users don't choose too short or too easy passwords.

If you don't like this and your site has rather low security requirements,
feel free to DISABLE the checker by::

    password_checker = None # no password checking


.. todo::

   describe moin configuration

