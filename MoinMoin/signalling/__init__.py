# -*- coding: ascii -*-
"""
    MoinMoin - signalling support

    MoinMoin uses blinker for sending signals and letting listeners subscribe
    to signals.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from blinker import Namespace, ANY

_signals = Namespace()

item_displayed = _signals.signal('item_displayed')
item_modified = _signals.signal('item_modified')


from MoinMoin import log
logging = log.getLogger(__name__)


@item_displayed.connect_via(ANY)
def log_item_displayed(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item %s:%s displayed" % (wiki_name, item_name))

@item_modified.connect_via(ANY)
def log_item_modified(app, item_name):
    wiki_name = app.cfg.interwikiname
    logging.info("item %s:%s modified" % (wiki_name, item_name))
