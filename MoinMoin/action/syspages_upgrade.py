# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - syspages upgrade

    The superuser can select an item containing system pages that should be installed.
    It is also possible to upgrade already existing system pages this way.

    @copyright: 2009 MoinMoin:ChristopherDenter,
                2010 MoinMoin:DiogenesAugusto

    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage.backends import upgrade_syspages
from MoinMoin.storage.error import BackendError


def execute(item_name, request):
    _ = request.getText
    if request.method == 'GET':
        action = 'syspages_upgrade'
        label = 'Upgrade System Pages'
        content = request.theme.render('action_query.html',
                                  action=action,
                                  label=label,
                                  no_comment=True,
                                  target=' '  # stupid template...
                                  )
    elif request.method == 'POST':
        cancelled = 'button_cancel' in request.form
        if not cancelled:
            syspages = request.form.get('target')
            try:
                upgrade_syspages(request, syspages)
            except BackendError, e:
                content = _('<br> System pages upgrade failed due to the following error: %s.' % e)
            else:
                content = _('<br> System pages have been upgraded successfully!')
            content = request.theme.render('content.html', content=content)
    return content

