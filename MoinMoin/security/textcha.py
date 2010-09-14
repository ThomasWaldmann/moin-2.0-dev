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

    def __init__(self, question=None):
        """ Initialize the TextCha.

            @param question: see _init_qa()
        """
        self.user_info = flaskg.user.valid and flaskg.user.name or request.remote_addr
        self.textchas = self._get_textchas()
        self._init_qa(question)

    def _get_textchas(self):
        """ get textchas from the wiki config for the user's language (or default_language or en) """
        groups = flaskg.groups
        cfg = app.cfg
        user = flaskg.user
        disabled_group = cfg.textchas_disabled_group
        textchas = cfg.textchas
        use_textchas = disabled_group and user.name and user.name in groups.get(disabled_group, [])
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

    def check_answer(self, given_answer):
        """ check if the given answer to the question is correct """
        if self.is_enabled():
            if self.answer_re is not None:
                success = self.answer_re.match(given_answer.strip()) is not None
            else:
                # someone trying to cheat!?
                success = False
            success_status = success and u"success" or u"failure"
            logging.info(u"TextCha: %s (u='%s', a='%s', re='%s', q='%s')" % (
                             success_status,
                             self.user_info,
                             given_answer,
                             self.answer_regex,
                             self.question,
                             ))
            return success
        else:
            return True

    def _make_form_values(self, question, given_answer):
        question_form = escape(question, True)
        given_answer_form = escape(given_answer, True)
        return question_form, given_answer_form

    def _extract_form_values(self, form=None):
        if form is None:
            form = request.form
        question = form.get('textcha-question')
        given_answer = form.get('textcha-answer', u'')
        return question, given_answer

    def render(self, form=None):
        """ Checks if textchas are enabled and returns HTML for one,
            or an empty string if they are not enabled.

            @return: unicode result html
        """
        if self.is_enabled():
            question, given_answer = self._extract_form_values(form)
            if question is None:
                question = self.question
            question_form, given_answer_form = self._make_form_values(question, given_answer)
            result = u"""
<div id="textcha">
<span id="textcha-question">%s</span>
<input type="hidden" name="textcha-question" value="%s">
<input id="textcha-answer" type="text" name="textcha-answer" value="%s" size="20" maxlength="80">
</div>
""" % (escape(question), question_form, given_answer_form)
        else:
            result = u''
        return result

    def check_answer_from_form(self, form=None):
        if self.is_enabled():
            question, given_answer = self._extract_form_values(form)
            self._init_qa(question)
            return self.check_answer(given_answer)
        else:
            return True

