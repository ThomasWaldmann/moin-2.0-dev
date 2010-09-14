# -*- coding: ascii -*-
"""
    MoinMoin - interwiki support code

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from werkzeug import url_quote

from flask import current_app as app
from flask import request
from flask import flaskg

from MoinMoin import config


def split_interwiki(wikiurl):
    """ Split a interwiki name, into wikiname and pagename, e.g:

    'MoinMoin:FrontPage' -> "MoinMoin", "FrontPage"
    'FrontPage' -> "Self", "FrontPage"
    'MoinMoin:Page with blanks' -> "MoinMoin", "Page with blanks"
    'MoinMoin:' -> "MoinMoin", ""

    @param wikiurl: the url to split
    @rtype: tuple
    @return: (wikiname, pagename)
    """
    try:
        wikiname, pagename = wikiurl.split(":", 1)
    except ValueError:
        wikiname, pagename = 'Self', wikiurl
    return wikiname, pagename


def resolve_interwiki(wikiname, pagename):
    """ Resolve an interwiki reference (wikiname:pagename).

    @param wikiname: interwiki wiki name
    @param pagename: interwiki page name
    @rtype: tuple
    @return: (wikitag, wikiurl, wikitail, err)
    """
    this_wiki_url = request.script_root + '/'
    if wikiname in ('Self', app.cfg.interwikiname):
        return (wikiname, this_wiki_url, pagename, False)
    else:
        try:
            return (wikiname, app.cfg.interwiki_map[wikiname], pagename, False)
        except KeyError:
            return (wikiname, this_wiki_url, "InterWiki", True)


def join_wiki(wikiurl, wikitail):
    """
    Add a (url_quoted) page name to an interwiki url.

    Note: We can't know what kind of URL quoting a remote wiki expects.
          We just use a utf-8 encoded string with standard URL quoting.

    @param wikiurl: wiki url, maybe including a $PAGE placeholder
    @param wikitail: page name
    @rtype: string
    @return: generated URL of the page in the other wiki
    """
    wikitail = url_quote(wikitail, charset=config.charset, safe='/')
    if '$PAGE' in wikiurl:
        return wikiurl.replace('$PAGE', wikitail)
    else:
        return wikiurl + wikitail


def getInterwikiHome(username):
    """
    Get a user's homepage.

    cfg.user_homewiki influences behaviour of this:
    'Self' does mean we store user homepage in THIS wiki.
    When set to our own interwikiname, it behaves like with 'Self'.

    'SomeOtherWiki' means we store user homepages in another wiki.

    @param username: the user's name
    @rtype: tuple
    @return: (wikiname, itemname)
    """
    homewiki = app.cfg.user_homewiki
    if homewiki == app.cfg.interwikiname:
        homewiki = u'Self'
    return homewiki, username

