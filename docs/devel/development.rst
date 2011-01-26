===========
Development
===========

Project Organisation
====================
We mainly use IRC and the wiki for communication, documentation and
planning.

IRC channels (on chat.freenode.net):

* #moin-dev (core development topics)
* #moin (user support, extensions)

Wikis:

* http://moinmo.in/

We use Mercurial DVCS (hg) for distributed version control.

Repositories:

* http://hg.moinmo.in/moin/2.0-dev (main repository)
* http://bitbucket.org/thomaswaldmann/moin-2.0-dev (bb mirror for your
  convenience, simplifying forking and contributing)

If you are not using Mercurial, you can of course also just send us patches.


MoinMoin architecture
=====================
moin2 is a WSGI application and uses:

* flask as framework

  - flask-script for commandline scripts
  - flask-babel / babel / pytz / parsedatetime for i18n/l10n
  - flask-themes for theme switching
  - flask-cache as cache storage abstraction
* werkzeug for lowlevel web/http stuff, debugging, builtin server, etc.
* jinja2 for templating (theme, user interface)
* flatland for form data processing
* EmeraldTree for xml / tree processing
* blinker for signalling
* pygments for syntax highlighting
* sqlalchemy as sql database abstraction (for indexing)

  - by default using sqlite as database
* jquery javascript lib
* CKeditor - GUI editor for (x)html
* TWikiDraw, AnyWikiDraw, svgdraw drawing tools

.. todo::

   add some nice gfx


How MoinMoin works
------------------
This is just a very high level overview about how moin works, if you'ld like
to know more details, you'll have to read more docs and the code.

First, the moin Flask application is created (see `MoinMoin.app.create_app`) -
this will:

* load the configuration (app.cfg)
* register some Modules that handle different parts of the functionality

  - MoinMoin.apps.frontend - most stuff a normal user uses
  - MoinMoin.apps.admin - some stuff for admins
  - MoinMoin.apps.feed - feeds (e.g. atom)
  - MoinMoin.apps.serve - serving some configurable static 3rd party stuff
* register before/after request handlers
* initialize the cache (app.cache)
* initialize the storage (app.storage)
* initialize the translation system
* initialize theme support

This app is then given to a WSGI compatible server somehow and will be called
by the server for each request for it.

Let's look at how it shows a wiki item:

* the Flask app receives a GET request for /WikiItem
* Flask's routing rules determine that this request should be served by
  `MoinMoin.apps.frontend.show_item`.
* Flask calls the before request handler of this module, which:

  - sets up the user as flaskg.user (anon user or logged in user)
  - initializes dicts/groups as flaskg.dicts, flaskg.groups
  - initializes jinja2 environment (templating)
* Flask then calls the handler function `MoinMoin.apps.frontend.show_item`,
  which

  - creates an in-memory Item

    + by fetching the item of name "WikiItem" from storage
    + it looks at the mimetype of this item (stored in metadata)
    + it creates an appropriately typed Item instance (depending on the mimetype)
  - calls Item._render_data() to determine how the rendered item looks like
    as HTML
  - renders the `show_item.html` template (and gives it the rendered item html)
  - returns the result to Flask
* Flask calls the after request handler which does some cleanup
* Flask returns an appropriate response to the server

