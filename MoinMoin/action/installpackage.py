# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - installpackage action

    TODO: acl checks were removed, have to be done on storage layer

    @copyright: 2009 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin import packages, wikiutil

def execute(item_name, request):
    data_file = request.files.get('data_file')
    if data_file.filename:
        # user selected a file to upload
        data = data_file.stream
        mimetype = wikiutil.MimeType(filename=data_file.filename).mime_type()
        package = packages.ZipPackage(request, data)
        if package.installPackage():
            msg = "Installation was successful!"
            msgtype = "info"
        else:
            msg = "Installation failed."
            msgtype = "error"
        request.theme.add_msg(msg, msgtype)

