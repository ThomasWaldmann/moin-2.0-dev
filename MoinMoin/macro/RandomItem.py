# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - RandomItem Macro (was: RandomPage)

    TODO: add mimetype param and only show items matching this mimetype

    @copyright: 2000 Juergen Hermann <jh@web.de>,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import random
random.seed()

from MoinMoin.items import Item, AccessDeniedError

Dependencies = ["time"]

def macro_RandomItem(macro, links=1):
    request = macro.request
    item_count = max(links, 1) # at least 1 link

    # Get full page list - very fast!
    all_item_names = [i.name for i in request.rootitem.list_items()]

    # Now select random page from the full list, and if it exists and we
    # can read it, save.
    random_item_names = []
    found = 0
    while found < item_count and all_item_names:
        # Take one random page from the list
        item_name = random.choice(all_item_names)
        all_item_names.remove(item_name)

        # Filter out pages the user may not read.
        try:
            item = Item.create(request, item_name)
            random_item_names.append(item_name)
            found += 1
        except AccessDeniedError:
            pass

    if not random_item_names:
        return ''

    f = macro.formatter

    # return a single page link
    if item_count == 1:
        name = random_item_names[0]
        return (f.pagelink(1, name, generated=1) +
                f.text(name) +
                f.pagelink(0, name))

    # return a list of page links
    random_item_names.sort()
    result = []
    write = result.append

    write(f.bullet_list(1))
    for name in random_item_names:
        write(f.listitem(1))
        write(f.pagelink(1, name, generated=1))
        write(f.text(name))
        write(f.pagelink(0, name))
        write(f.listitem(0))
    write(f.bullet_list(0))

    result = ''.join(result)
    return result

