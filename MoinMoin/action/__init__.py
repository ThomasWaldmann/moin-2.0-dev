# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Action Implementation

    Actions are triggered by the user clicking on special links on the page
    (e.g. the "edit" link). The name of the action is passed in the "do" param.

    The sub-package "MoinMoin.action" contains external actions, you can
    place your own extensions there (similar to extension macros). User
    actions that start with a capital letter will be displayed in a list
    at the bottom of each page.

    User actions starting with a lowercase letter can be used to work
    together with a user macro; those actions a likely to work only if
    invoked BY that macro, and are thus hidden from the user interface.

    Additionally to the usual stuff, we provide an ActionBase class here with
    some of the usual base functionality for an action, like checking
    actions_excluded, making and checking tickets, rendering some form,
    displaying errors and doing stuff after an action. Also utility functions
    regarding actions are located here.

    @copyright: 2000-2004 Juergen Hermann <jh@web.de>,
                2006 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:ChristopherDenter,
                2008 MoinMoin:FlorianKrupicka
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.util import pysupport
from MoinMoin import config, wikiutil

# create a list of extension actions from the package directory
modules = pysupport.getPackageModules(__file__)

# Dispatching ----------------------------------------------------------------
def get_names(config):
    """ Get a list of known actions.

    @param config: a config object
    @rtype: set
    @return: set of known actions
    """
    if not hasattr(config.cache, 'action_names'):
        actions = wikiutil.getPlugins('action', config)
        actions = set([action for action in actions
                      if not action in config.actions_excluded])
        config.cache.action_names = actions # remember it
    return config.cache.action_names

def getHandler(cfg, action, identifier="execute"):
    """ return a handler function for a given action.  """
    if action not in get_names(cfg):
        raise ValueError("excluded or unknown action")

    try:
        handler = wikiutil.importPlugin(cfg, "action", action, identifier)
    except wikiutil.PluginMissingError:
        raise ValueError("excluded or unknown action")

    return handler

