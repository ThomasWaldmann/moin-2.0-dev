# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - syspages upgrade

    The superuser can select an item containing system pages that should be installed.
    It is also possible to upgrade already existing system pages this way.

    @copyright: 2009 MoinMoin:ChristopherDenter

    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.storage import upgrade_syspages
from MoinMoin.storage.error import BackendError


def execute(item_name, request):
    _ = request.getText
    if request.method == 'GET':
        env = request.theme.env
        template = env.get_template('action_query.html')
        action = 'syspages_upgrade'
        label = 'Upgrade System Pages'
        content = template.render(gettext=request.getText,
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
                # XXX in order to avoid a cyclic import... improve!
                from MoinMoin.storage.backends import memory
                upgrade_syspages(request, syspages, memory.MemoryBackend())
            except BackendError, e:
                content = _('<br> System pages upgrade failed due to the following error: %s.' % e)
            else:
                content = _('<br> System pages have been upgraded successfully!')

    request.theme.render_content(item_name, content)

