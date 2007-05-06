# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Create an action link

    Usage:

        [[Action(action)]]

        Create a link to page with ?action=action and the text action

        [[Action(action, text)]]

        Same with custom text.

    @copyright: 2004 Johannes Berg <johannes@sipsolutions.de>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import wikiutil

Dependencies = ["language"]


class ActionLink:
    """ ActionLink - link to page with valid action """

    arguments = ['action', 'text']

    def __init__(self, macro, args):
        self.macro = macro
        self.request = macro.request
        self.args = self.getArgs(args)
        
    def getValidActions(self):  
        """ lists all valid actions """
        from MoinMoin import action
        actions = [x for x in action.modules
                   if not x in self.macro.request.cfg.actions_excluded]
        loc_actions = [x for x in wikiutil.wikiPlugins('action', self.macro.cfg)
                       if not x in self.macro.request.cfg.actions_excluded]
        if loc_actions:
            actions.append(loc_actions)
        return actions

    def getArgs(self, argstr):
        """ Temporary function until Oliver Graf args parser is finished

        @param string: string from the wiki markup [[NewPage(string)]]
        @rtype: dict
        @return: dictionary with macro options
        """
        if not argstr:
            return {}
        args = [s.strip() for s in argstr.split(',')]
        args = dict(zip(self.arguments, args))
        return args

    def renderInText(self):
        """ Render macro in text context

        The parser should decide what to do if this macro is placed in a
        paragraph context.
        """
        _ = self.request.getText

        # Default to show page instead of an error message (too lazy to
        # do an error message now).
        action = self.args.get('action', 'show')

        # Use translated text or action name
        text = self.args.get('text', action)
        text = _(text, formatted=False)
        text = wikiutil.escape(text, 1)
        if action in self.getValidActions():
            # Escape user input
            action = wikiutil.escape(action, 1)
            # Create link
            page = self.macro.formatter.page
            link = page.link_to(self.request, text, querystr='action=%s' % action)
            return link
        else:
            return text

def execute(macro, args):
    """ Temporary glue code to use with moin current macro system """
    return ActionLink(macro, args).renderInText()


