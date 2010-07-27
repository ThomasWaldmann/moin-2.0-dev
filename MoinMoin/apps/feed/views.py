# -*- coding: ascii -*-
"""
    MoinMoin - feed views
    
    This contains all sort of feeds.

    @copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

from MoinMoin.apps.feed import feed

@feed.route('/atom/<itemname:item_name>')
@feed.route('/atom', defaults=dict(item_name=''))
def atom(item_name):
    return "NotImplemented"
