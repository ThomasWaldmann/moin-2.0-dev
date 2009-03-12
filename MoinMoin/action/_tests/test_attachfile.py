# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - tests of AttachFile action

    @copyright: 2007 by Karol Nowak <grywacz@gmail.com>
                2007-2008 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""
import os, StringIO
from MoinMoin.action import AttachFile
from MoinMoin.PageEditor import PageEditor
from MoinMoin._tests import become_trusted, create_page

class TestAttachFile:
    """ testing action AttachFile"""
    pagename = u"AutoCreatedSillyPageToTestAttachments"

    def test_add_attachment(self):
        """Test if add_attachment() works"""

        become_trusted(self.request)
        filename = "AutoCreatedSillyAttachment"

        create_page(self.request, self.pagename, u"Foo!")

        AttachFile.add_attachment(self.request, self.pagename, filename, "Test content", True)
        assert self.request.cfg.data_backend.has_item(self.pagename + '/' + filename)
        assert AttachFile.exists(self.request, self.pagename, filename)

    def test_add_attachment_for_file_object(self):
        """Test if add_attachment() works with file like object"""

        become_trusted(self.request)

        filename = "AutoCreatedSillyAttachment.png"

        create_page(self.request, self.pagename, u"FooBar!")
        data = "Test content"

        filecontent = StringIO.StringIO(data)

        AttachFile.add_attachment(self.request, self.pagename, filename, filecontent, True)

        assert self.request.cfg.data_backend.has_item(self.pagename + '/' + filename)
        assert AttachFile.exists(self.request, self.pagename, filename)
        rev = self.request.cfg.data_backend.get_item(self.pagename + '/' + filename).get_revision(-1)
        assert rev.size == len(data)


    def test_get_attachment_path_created_on_getFilename(self):
        """
        Tests if AttachFile.getFilename creates the attachment dir on self.requesting
        """
        filename = ""
        file_exists = os.path.exists(AttachFile.getFilename(self.request, self.pagename, filename))

        assert file_exists

    def test_getAttachUrl(self):
        """
        Tests if AttachFile.getAttachUrl taints a filename
        """
        filename = "<test2.txt>"
        expect = "rename=_test2.txt_"
        result = AttachFile.getAttachUrl(self.pagename, filename, self.request, upload=True)

        assert expect in result

coverage_modules = ['MoinMoin.action.AttachFile']
