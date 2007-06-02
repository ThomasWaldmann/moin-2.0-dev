"""
    Common stuff for storage unit tests.

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

datadir = "data/user"

names = [ "1180352194.13.59241", "1180424607.34.55818", "1180424618.59.18110" ]

metadata = {u'aliasname' : u'',
            u'bookmarks' : {},
            u'css_url' : u'',
            u'date_fmt' : u'',
            u'datetime_fmt' : u'',
            u'disabled' : u'0',
            u'edit_on_doubleclick' : u'0',
            u'edit_rows' : u'20',
            u'editor_default' : u'text',
            u'editor_ui' : u'freechoice',
            u'email' : u'h_wendel@cojobo.net',
            u'enc_password' : u'{SHA}ujz/zJOpLgj4LDPFXYh2Zv3zZK4=',
            u'language': u'',
            u'last_saved': u'1180435816.61',
            u'mailto_author' : u'0',
            u'name': u'HeinrichWendel',
            u'quicklinks': [u'www.google.de', u'www.test.de', u'WikiSandBox'],
            u'remember_last_visit': u'0',
            u'remember_me' : u'1',
            u'show_comments' : u'0',
            u'show_fancy_diff' : u'1',
            u'show_nonexist_qm' : u'0',
            u'show_page_trail' : u'1',
            u'show_toolbar' : u'1',
            u'show_topbottom' : u'0',
            u'subscribed_pages' : [u'WikiSandBox', u'FrontPage2'],
            u'theme_name' : u'modern',
            u'tz_offset' : u'0',
            u'want_trivial' : u'0',
            u'wikiname_add_spaces' : u'0'
            }
    
def assert_dicts(dict1, dict2):
    """
    Assert the equality of two dictionaries.
    """
    for key, value in dict1.iteritems():
        assert dict2[key] == value

def assert_lists(list1, list2):
    """
    Assert the equality of two lists.
    """
    for key in list1:
        assert key in list2
        
    for key in list2:
        assert key in list1