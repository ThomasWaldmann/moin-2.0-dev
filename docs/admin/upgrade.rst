=========
Upgrading
=========

.. note::
   moin2 is internally working very differently compared to moin 1.x.

   moin 2.0 is *not* just a +0.1 step from 1.9 (like 1.8 -> 1.9), but the
   change of the major revision is indicating *major and incompatible changes*.

   So please consider it to be a different, incompatible software that tries
   to be compatible at some places:

   * Server and wiki engine Configuration: expect to review/rewrite it
   * Wiki content: expect 90% compatibility for existing moin 1.9 content. The
     most commonly used simple moin wiki markup (like headlines, lists, bold,
     ...) will still work, but expect to change macros, parsers, action links,
     3rd party extensions (for example).

From moin < 1.9
---------------
As MoinMoin 1.9.x has been out there for quite a while, we only describe how
to upgrade from moin 1.9.x to moin2. If you still run an older moin
version than this, please first upgrade to moin 1.9.x. Maybe run 1.9.x for a
while, so you can be sure everything is working as expected.

Note: moin 1.9.x is a WSGI application, moin2 is also a WSGI application.
So, upgrading to 1.9 first makes also sense concerning the WSGI / server side.

From moin 1.9.x
---------------
* Have a backup of everything, so you can go back in case it doesn't do what
  you expect. If you have a 2nd machine, it is a good idea to try it there
  first (and not directly modify your production machine).
* Install and configure moin2, make it work, start configuring it from the
  moin2 sample config (do not just use your 1.9 wikiconfig)
* Take some values from your old wikiconfig: ...
* Configure moin2 to use fs19 backend to access your moin 1.9 content (pages,
  attachments and users). Use a copy of the 1.9 content, do not point it at
  your original data.
* Serialize everything to an xml file and keep the xml file (you can use it to
  try different backend configurations)
* Reconfigure moin2 to use the backend you like to use (e.g. fs2 backend)
* Unserialize your xml file to fill the backend with your data

.. todo::

   describe values that should be taken from old wikiconfig
   add more details, examples for upgrading moin
