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


