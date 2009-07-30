# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - syspages upgrade

    The superuser can select an item containing system pages that should be installed.
    It is also possible to upgrade already existing system pages this way.

    @copyright: 2009 MoinMoin:ReimarBauer,
                     MoinMoin:ThomasWaldmann,
                     MoinMoin:ChristopherDenter

    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import i18n, packages
from MoinMoin.i18n import strings
i18n.strings = strings

from MoinMoin.util.dataset import TupleDataset, Column
from MoinMoin.widget.browser import DataBrowserWidget

from MoinMoin.storage import upgrade_syspages
from MoinMoin.storage.error import BackendError

def execute(pagename, request):
    if not request.user or not request.user.isSuperUser():
        return ''
    _ = request.getText
    fmt = request.html_formatter

    lang = request.values.get('language') or 'English'
    syspages = request.values.get('syspages_package') or ''
    msg = (_('Please specify a the system pages that you would like to install.'), 'info')

    if syspages:
        try:
            # XXX in order to avoid a cyclic import... improve!
            from MoinMoin.storage.backends import memory
            upgrade_syspages(request, syspages, memory.MemoryBackend())
        except BackendError, e:
            msg = (_('System pages upgrade failed due to the following error: %s.' % e), 'error')
        else:
            msg = (_('System pages have been upgraded successfully!'), 'info')

    data = TupleDataset()
    data.columns = [
           Column('syspage', label=_('System Pages')),
           Column('action', label=_('Install')),
        ]

    label_install = _("install")

    table = DataBrowserWidget(request)
    table.setData(data)
    page_table = ''.join(table.format(method='GET'))

    fmt = request.formatter

    title = _("Install or upgrade system pages")
    request.theme.add_msg(*msg)
    request.theme.send_title(title, page=request.page, pagename=pagename)
    request.write(request.formatter.startContent("content"))
    request.write(page_table)
    request.write(request.formatter.endContent())
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()

