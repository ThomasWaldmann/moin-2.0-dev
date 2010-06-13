# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MoinMoin.items Tests

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import py

from MoinMoin._tests import become_trusted
from MoinMoin.items import Item, ContainerItem, NonExistent, Binary, Text, Image, TransformableBitmapImage, PythonSrc, \
                           MIMETYPE, \
                           EDIT_LOG_ADDR, EDIT_LOG_COMMENT, \
                           EDIT_LOG_HOSTNAME, EDIT_LOG_USERID, EDIT_LOG_ACTION

class TestItem:
    def testNonExistent(self):
        item = Item.create(self.request, 'DoesNotExist')
        assert isinstance(item, NonExistent)
        meta, data = item.meta, item.data
        assert meta == {MIMETYPE: 'application/x-unknown'}
        assert data == ''

    def testClassFinder(self):
        for mimetype, ExpectedClass in [
                ('application/x-foobar', Binary),
                ('text/plain', Text),
                ('text/x-python', PythonSrc),
                ('image/tiff', Image),
                ('image/png', TransformableBitmapImage),
            ]:
            item = Item.create(self.request, 'foo', mimetype=mimetype)
            assert isinstance(item, ExpectedClass)

    def testCRUD(self):
        name = u'NewItem'
        mimetype = 'text/plain'
        data = 'foobar'
        meta = dict(foo='bar')
        comment = u'saved it'
        become_trusted(self.request)
        item = Item.create(self.request, name)
        # save rev 0
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(self.request, name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
        assert saved_meta[EDIT_LOG_COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 0

        data = rev1_data = data * 10000
        comment = comment + u' again'
        # save rev 1
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(self.request, name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
        assert saved_meta[EDIT_LOG_COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 1

        data = ''
        comment = 'saved empty data'
        # save rev 2 (auto delete)
        item._save(meta, data, mimetype=mimetype, comment=comment)
        # check save result
        item = Item.create(self.request, name)
        saved_meta, saved_data = dict(item.meta), item.data
        assert saved_meta[MIMETYPE] == mimetype
        assert saved_meta[EDIT_LOG_COMMENT] == comment
        assert saved_data == data
        assert item.rev.revno == 2

        # access old revision
        item = Item.create(self.request, name, rev_no=1)
        assert item.data == rev1_data

    def testIndex(self):
        # create a toplevel and some sub-items
        basename = u'Foo'
        for name in ['', '/ab', '/cd/ef', '/gh', '/ij/kl', ]:
            item = Item.create(self.request, basename + name)
            item._save({}, "foo", mimetype='text/plain')

        # check index
        baseitem = Item.create(self.request, basename)
        index = baseitem.get_index()
        assert index == [(u'Foo/ab', u'ab', 'text/plain'),
                         (u'Foo/cd/ef', u'cd/ef', 'text/plain'),
                         (u'Foo/gh', u'gh', 'text/plain'),
                         (u'Foo/ij/kl', u'ij/kl', 'text/plain'),
                        ]
        flat_index = baseitem.flat_index()
        assert flat_index == [(u'Foo/ab', u'ab', 'text/plain'),
                              (u'Foo/gh', u'gh', 'text/plain'),
                             ]


class TestContainerItems:
    """
    tests for the container items
    """
    def testCreateContainerRevision(self):
        """
        creates a container and tests the content saved to the container
        """
        request = self.request
        item_name = 'ContainerItem1'
        ci = ContainerItem(request, item_name)
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = ['example1.txt', 'example2.txt']
        ci.put('example1.txt', filecontent, content_length, members=members)
        ci.put('example2.txt', filecontent, content_length, members=members)

        nci = ContainerItem(request, item_name)
        tf_names = nci.get_members()
        assert sorted(tf_names) == sorted(members)
        assert nci.get('example1.txt').read() == filecontent

    def testRevisionUpdate(self):
        """
        creates two revisions of a container item
        """
        request = self.request
        item_name = 'ContainterItem2'
        ci = ContainerItem(request, item_name)
        filecontent = 'abcdefghij'
        content_length = len(filecontent)
        members = ['example1.txt']
        ci.put('example1.txt', filecontent, content_length, members=members)
        filecontent = 'AAAABBBB'
        content_length = len(filecontent)
        members = ['example1.txt']
        ci.put('example1.txt', filecontent, content_length, members=members)

        item = request.storage.get_item(item_name)
        assert item.next_revno == 2

        nci = ContainerItem(request, item_name)
        assert nci.get('example1.txt').read() == filecontent

coverage_modules = ['MoinMoin.items']

