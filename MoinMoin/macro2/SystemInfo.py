# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - SystemInfo Macro

    This macro shows some info about your wiki, wiki software and your system.

    @copyright: 2006-2008 MoinMoin:ThomasWaldmann,
                2007 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import sys, os

from flask import current_app as app

from flask import flaskg

from MoinMoin import _, N_
from MoinMoin.macro2._base import MacroDefinitionListBase
from MoinMoin import wikiutil, version
from MoinMoin import action, macro
from MoinMoin.logfile import editlog
from MoinMoin.Page import Page

class Macro(MacroDefinitionListBase):
    def macro(self):
        return self.create_definition_list(self.get_items())

    def formatInReadableUnits(self, size):
        size = float(size)
        unit = u' Byte'
        if size > 9999:
            unit = u' KiB'
            size /= 1024
        if size > 9999:
            unit = u' MiB'
            size /= 1024
        if size > 9999:
            unit = u' GiB'
            size /= 1024
        return u"%.1f %s" % (size, unit)

    def getDirectorySize(self, path):
        try:
            dirsize = 0
            for root, dummy, files in os.walk(path):
                dirsize += sum([os.path.getsize(os.path.join(root, name)) for name in files])
        except EnvironmentError:
            dirsize = -1
        return dirsize

    def get_items(self):
        request = self.request

        desc_list = []
        row = lambda label, value, dl=desc_list: dl.append((label, value))

        row(_('Python Version'), sys.version)
        row(_('MoinMoin Version'), _('Release %s [Revision %s]') % (version.release, version.revision))

        if not flaskg.user.valid:
            # for an anonymous user it ends here.
            return desc_list

        if flaskg.user.isSuperUser():
            # superuser gets all page dependent stuff only
            try:
                import Ft
                ftversion = Ft.__version__
            except ImportError:
                ftversion = None
            except AttributeError:
                ftversion = 'N/A'

            if ftversion:
                row(_('4Suite Version'), ftversion)

            # TODO add python-xml check and display it

            # Get the full pagelist of the wiki
            pagelist = request.rootpage.getPageList(user='')
            systemPages = []
            totalsize = 0
            for num, page in enumerate(pagelist):
                if wikiutil.isSystemPage(request, page):
                    systemPages.append(page)
                totalsize += Page(request, page).size()
            pagecount = num + 1

            row(_('Number of pages'), str(pagecount - len(systemPages)))
            row(_('Number of system pages'), str(len(systemPages)))

            row(_('Accumulated page sizes'), self.formatInReadableUnits(totalsize))

        nonestr = _("NONE")
        # a valid user gets info about all installed extensions
        row(_('Global extension macros'), ', '.join(macro.modules) or nonestr)
        row(_('Local extension macros'),
            ', '.join(wikiutil.wikiPlugins('macro', app.cfg)) or nonestr)

        glob_actions = [x for x in action.modules
                        if not x in app.cfg.actions_excluded]
        row(_('Global extension actions'), ', '.join(glob_actions) or nonestr)
        loc_actions = [x for x in wikiutil.wikiPlugins('action', app.cfg)
                       if not x in app.cfg.actions_excluded]
        row(_('Local extension actions'), ', '.join(loc_actions) or nonestr)

        try:
            import xapian
            xapVersion = 'Xapian %s' % xapian.version_string()
        except ImportError:
            xapian = None
            xapVersion = _('Xapian and/or Python Xapian bindings not installed')

        xapian_enabled = app.cfg.xapian_search
        xapState = (_('Disabled'), _('Enabled'))
        xapRow = '%s, %s' % (xapState[xapian_enabled], xapVersion)

        if xapian and xapian_enabled:
            from MoinMoin.search.Xapian.indexing import XapianIndex
            idx = XapianIndex(request)
            idxState = (_('index unavailable'), _('index available'))
            idx_exists = idx.exists()
            xapRow += ', %s' % idxState[idx_exists]
            if idx_exists:
                xapRow += ', %s' % (_('last modified: %s') %
                    flaskg.user.getFormattedDateTime(idx.mtime()))

        row(_('Xapian search'), xapRow)

        if xapian and xapian_enabled:
            stems = xapian.Stem.get_available_languages()
            row(_('Stemming for Xapian'), xapState[app.cfg.xapian_stemming] +
                " (%s)" % (stems or nonestr))

        try:
            from threading import activeCount
            t_count = str(activeCount())
        except ImportError:
            t_count = None

        row(_('Active threads'), t_count or _('N/A'))

        return desc_list

