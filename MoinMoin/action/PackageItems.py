# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - PackagePages action

    This action allows you to package pages.

    TODO: use ActionBase class

    @copyright: 2005 MoinMoin:AlexanderSchremmer
                2007-2009 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""
import cStringIO
import os
import zipfile
from datetime import datetime

from MoinMoin import wikiutil, config, user
from MoinMoin.items import Item
from MoinMoin.Page import Page
from MoinMoin.packages import MOIN_PACKAGE_FILE, packLine, unpackLine
from MoinMoin.search import searchPages
from MoinMoin.storage.error import NoSuchItemError

ACTION_NAME = __name__.split('.')[-1]

class ActionError(Exception):
    pass

class PackageItems:
    def __init__(self, item_name, request):
        self.request = request
        self.item_name = item_name

    def render(self):
        """ Calls collectpackage() with the arguments specified. """
        _ = self.request.getText
        request = self.request

        if self.__class__.__name__ in request.cfg.actions_excluded:
            raise ActionError
        if not request.values.get('button_ok'):
            template = request.theme.env.get_template('action_packageitems.html')
            content = template.render(gettext=request.getText,
                          action=ACTION_NAME,
                          label='package items',
                          item_name=self.item_name,
                          )
            request.theme.render_content(self.item_name, content)
            return
        # Get new name from form and normalize.
        target = request.form.get('target')
        item_list = request.form.get('item_list')
        include_subitems = request.values.get('sub_items', False)
        
        target = wikiutil.taintfilename(target)

        if not target:
            raise ActionError

        filelike = cStringIO.StringIO()
        package = self.collectpackage(unpackLine(item_list, ","), filelike, target, include_subitems)
        request.content_type = 'application/zip'
        request.content_length = filelike.tell()
        request.headers.add('Content-Disposition', 'inline; filename="%s"' % target)
        request.write(filelike.getvalue())
        filelike.close()

    def searchpackage(self, request, searchkey):
        """ Search MoinMoin for the string specified and return a list of
        matching pages, provided they are not system pages and not
        present in the underlay.

        @param request: current request
        @param searchkey: string to search for
        @rtype: list
        @return: list of pages matching searchkey
        """

        pagelist = searchPages(request, searchkey)

        titles = []
        for title in pagelist.hits:
            if not wikiutil.isSystemPage(request, title.page_name) or not title.page.isUnderlayPage():
                titles.append(title.page_name)
        return titles

    def collectpackage(self, item_list, fileobject, pkgname="", include_subitems=False):
        """ Expects a list of items as an argument, and fileobject to be an open
        file object, which a zipfile will get written to.

        @param item_list: items to package
        @param fileobject: open file object to write to
        @param pkgname: optional file name, to prevent self packaging
        @rtype: string or None
        @param include_subitems: True if you want subitems collected
        """
        _ = self.request.getText
        comment = "Created by the PackageItems action."
        COMPRESSION_LEVEL = zipfile.ZIP_DEFLATED
        zf = zipfile.ZipFile(fileobject, "w", COMPRESSION_LEVEL)
        cnt = 0
        userid = user.getUserIdentification(self.request)
        script = [packLine(['MoinMoinPackage', '1']), ]
        rev_no = -1
        for item_name in item_list:
            item_name = item_name.strip()
            cnt += 1
            try:
                item = self.request.cfg.data_backend.get_item(item_name)
            except NoSuchItemError:
                continue
            r = item.get_revision(rev_no)
            mimetype = r.get('mimetype') or 'application/x-unknown' # XXX why do we need ... or ..?
            contenttype = 'utf-8'
            script.append(packLine(["AddItem", str(cnt), item_name, mimetype, contenttype, userid, comment]))
            timestamp = float(r.timestamp)
            zi = zipfile.ZipInfo(filename=str(cnt), date_time=datetime.fromtimestamp(timestamp).timetuple()[:6])
            zi.compress_type = COMPRESSION_LEVEL
            zf.writestr(zi, r.read_data().encode("utf-8"))
            if include_subitems:
                # ToDo implement subitems, currently removed
                pass
        script += [packLine(['Print', 'Thank you for using PackageItems!'])]
        zf.writestr(MOIN_PACKAGE_FILE, u"\n".join(script).encode("utf-8"))
        zf.close()
        

def execute(item_name, request):
    """ Glue code for actions """
    PackageItems(item_name, request).render()
