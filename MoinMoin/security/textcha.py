# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Text CAPTCHAs

    This is just asking some (admin configured) questions and
    checking if the answer is as expected. It is up to the wiki
    admin to setup questions that a bot can not easily answer, but
    humans can. It is recommended to setup SITE SPECIFIC questions
    and not to share the questions with other sites (if everyone
    asks the same questions / expects the same answers, spammers
    could adapt to that).

    TODO:
    * roundtrip the question in some other way:
     * use safe encoding / encryption for the q
     * make sure a q/a pair in the POST is for the q in the GET before
    * make some nice CSS
    * make similar changes to GUI editor

    @copyright: 2007 by MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import re
import random

from MoinMoin import log
logging = log.getLogger(__name__)

from flask import current_app as app
from flask import request
from flask import flaskg

from werkzeug import escape


class TextCha(object):
    """ Text CAPTCHA support """

    def __init__(self, form):
        """ Initialize the TextCha.

            @param form: flatland form to use; must subclass TextChaizedForm
        """
        self.user_info = flaskg.user.valid and flaskg.user.name or request.remote_addr
        self.textchas = self._get_textchas()
        self._init_qa(form['textcha_question'].value)
        self.form = form

    def _get_textchas(self):
        """ get textchas from the wiki config for the user's language (or default_language or en) """
        groups = flaskg.groups
        cfg = app.cfg
        user = flaskg.user
        disabled_group = cfg.textchas_disabled_group
        textchas = cfg.textchas

        use_textchas = not (disabled_group and user.name and user.name in groups.get(disabled_group, []))

        if textchas and use_textchas:
            locales = [user.locale, cfg.locale_default, 'en', ]
            for locale in locales:
                logging.debug(u"TextCha: trying locale == '%s'." % locale)
                if locale in textchas:
                    logging.debug(u"TextCha: using locale = '%s'" % locale)
                    return textchas[locale]

    def _init_qa(self, question=None):
        """ Initialize the question / answer.

         @param question: If given, the given question will be used.
                          If None, a new question will be generated.
        """
        if self.is_enabled():
            if question is None:
                self.question = random.choice(self.textchas.keys())
            else:
                self.question = question
            try:
                self.answer_regex = self.textchas[self.question]
                self.answer_re = re.compile(self.answer_regex, re.U|re.I)
            except KeyError:
                # this question does not exist, thus there is no answer
                self.answer_regex = ur"[Never match for cheaters]"
                self.answer_re = None
                logging.warning(u"TextCha: Non-existing question '%s'. User '%s' trying to cheat?" % (
                                self.question, self.user_info))
            except re.error:
                logging.error(u"TextCha: Invalid regex in answer for question '%s'" % self.question)
                self._init_qa()

    def is_enabled(self):
        """ check if textchas are enabled.

            They can be disabled for all languages if you use textchas = None or = {},
            also they can be disabled for some specific language, like:
            textchas = {
                'en': {
                    'some question': 'some answer',
                    # ...
                },
                'de': {}, # having no questions for 'de' means disabling textchas for 'de'
                # ...
            }
        """
        return not not self.textchas # we don't want to return the dict

    def amend_form(self):
        """ Amend the form by doing the following:

            * set the question if textcha is enabled, or
            * make the fields optional if it isn't.
        """
        if self.is_enabled():
            self.form['textcha_question'].set(self.question)
        else:
            self.form['textcha_question'].optional = True
            self.form['textcha'].optional = True
