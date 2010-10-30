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

.. todo::

   describe moin configuration

