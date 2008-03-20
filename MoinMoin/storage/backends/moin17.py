"""
    MoinMoin 1.7 storage backend

    TODO:
    * revision meta data currently only has edit_log* entries
        * add data size
        * later: mimetype
        * maybe sha1 or md5sum
        * maybe store a pointer to the data file revision into the meta file revision
    * use YAML for metadata?

    @copyright: 2007 MoinMoin:ThomasWaldmann, based on moin16
                backend code from MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import codecs
import os
import shutil
import tempfile

from MoinMoin import config
from MoinMoin.storage.backends.filesystem import BaseFilesystemBackend, AbstractData, AbstractMetadata, _get_rev_string, _create_file
from MoinMoin.storage.backends.moin16 import UserBackend # use this from 1.6 for now

class ItemBackend(BaseFilesystemBackend):
    """
    This class implements the MoinMoin 1.7 Item Storage Stuff.
    """

    def __init__(self, name, path, cfg, is_underlay=False):
        """
        Init the Backend with the correct path.
        """
        BaseFilesystemBackend.__init__(self, name, path, cfg, True, is_underlay=is_underlay)

    def list_items(self, filters, filterfn):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_items
        """
        for f in os.listdir(self._path):
            if not os.path.isfile(os.path.join(self._path, f, "meta")):
                continue
            if not BaseFilesystemBackend._filter(self, f, filters, filterfn):
                continue
            yield f

    def has_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_item
        """
        return os.path.isfile(self._get_item_path(name, "meta"))

    def create_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_item
        """
        os.mkdir(self._get_item_path(name))
        os.mkdir(self._get_item_path(name, "cache"))
        os.mkdir(self._get_item_path(name, "cache", "__lock__"))
        _create_file(self._get_item_path(name, "meta"))
        os.mkdir(self._get_item_path(name, "meta.revisions"))
        os.mkdir(self._get_item_path(name, "data.revisions"))

    def remove_item(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_item
        """
        shutil.rmtree(self._get_item_path(name))

    def rename_item(self, name, newname):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.rename_item
        """
        shutil.move(self._get_item_path(name), self._get_item_path(newname))

    def list_revisions(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.list_revisions
        """
        revs = os.listdir(self._get_item_path(name, "meta.revisions"))
        revs = [int(rev) for rev in revs if not rev.endswith(".tmp")]
        revs.sort()

        revs.reverse()
        return revs

    def current_revision(self, name):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.current_revision
        """
        meta = self.get_metadata_backend(name, -1)
        try:
            rev = int(meta['current'])
        except (ValueError, KeyError):
            rev = 0

        return rev

    def has_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.has_revision
        """
        return -1 <= revno <= self.current_revision(name)

    def create_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.create_revisions
        """
        _create_file(self._get_rev_path(name, revno, 'data'))
        _create_file(self._get_rev_path(name, revno, 'meta'))
        self._update_current(name)

    def remove_revision(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.remove_revisions
        """
        os.remove(self._get_rev_path(name, revno, 'meta'))
        os.remove(self._get_rev_path(name, revno, 'data'))
        self._update_current(name)

    def _update_current(self, name):
        """
        Update the current file.
        """
        revnos = self.list_revisions(name)
        if revnos:
            revno = revnos[0]
        else:
            revno = 0

        meta = self.get_metadata_backend(name, -1)
        meta['current'] = str(revno)
        meta.save()

    def get_data_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_data_backend
        """
        return ItemData(self, name, revno)

    def get_metadata_backend(self, name, revno):
        """
        @see MoinMoin.storage.interfaces.StorageBackend.get_metadata_backend
        """
        return ItemMetadata(self, name, revno)

    def _get_rev_path(self, name, revno, kind):
        """
        @see MoinMoin.storage.backends.filesystem.BaseFilesystemBackend._get_rev_path

        Returns the path to a specified revision of kind 'meta' or 'data'.
        """
        return self._get_item_path(name, "%s.revisions" % kind, _get_rev_string(revno))


class ItemData(AbstractData):
    """
    This class implements a file like object for MoinMoin 1.7 Item stuff.
    """


class ItemMetadata(AbstractMetadata):
    """
    Metadata implementation of the Item backend.
    """

    def _parse_metadata(self, name, revno):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._parse_metadata
        """
        if revno == -1:
            meta_file = codecs.open(self._backend._get_item_path(name, 'meta'), "r", config.charset)
        else:
            meta_file = codecs.open(self._backend._get_rev_path(name, revno, 'meta'), "r", config.charset)

        meta = meta_file.read()
        meta_file.close()

        return parse_meta(meta)

    def _save_metadata(self, name, revno, metadata):
        """
        @see MoinMoin.storage.backends.filesystem.AbstractMetadata._save_metadata
        """
        meta = make_meta(metadata)

        tmp_handle, tmp_name = tempfile.mkstemp(dir=self._backend._cfg.tmp_dir)

        meta_file = codecs.getwriter(config.charset)(os.fdopen(tmp_handle, "w"))
        meta_file.write(meta)
        meta_file.close()

        if revno == -1:
            shutil.move(tmp_name, self._backend._get_item_path(name, 'meta'))
        else:
            shutil.move(tmp_name, self._backend._get_rev_path(name, revno, 'meta'))


def parse_meta(meta):
    metadata = {}
    meta_lines = meta.splitlines()
    for line in meta_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        try:
            key, value = line.split('=', 1)
            # Decode list values
            if key.endswith('[]'):
                key = key[:-2]
                value = _decode_list(value)
            # Decode dict values
            elif key.endswith('{}'):
                key = key[:-2]
                value = _decode_dict(value)
            metadata[key] = value
        except ValueError:
            pass
    return metadata

def make_meta(metadata):
    result = []
    for key, value in metadata.iteritems():
        # Encode list values
        if isinstance(value, list):
            key += '[]'
            value = _encode_list(value)
        # Encode dict values
        elif isinstance(value, dict):
            key += '{}'
            value = _encode_dict(value)
        line = u"%s=%s\n" % (key, unicode(value))
        result.append(line)
    return u''.join(result)


def _encode_list(items):
    """
    Encode list of items in user data file

    Items are separated by '\t' characters.

    @param items: list unicode strings
    @rtype: unicode
    @return: list encoded as unicode
    """
    line = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        line.append(item)

    line = '\t'.join(line)
    return line


def _decode_list(line):
    """
    Decode list of items from user data file

    @param line: line containing list of items, encoded with _encode_list
    @rtype: list of unicode strings
    @return: list of items in encoded in line
    """
    items = []
    for item in line.split('\t'):
        item = item.strip()
        if not item:
            continue
        items.append(item)
    return items


def _encode_dict(items):
    """
    Encode dict of items in user data file

    Items are separated by '\t' characters.
    Each item is key:value.

    @param items: dict of unicode:unicode
    @rtype: unicode
    @return: dict encoded as unicode
    """
    line = []
    for key, value in items.items():
        item = u'%s:%s' % (key, value)
        line.append(item)
    line = '\t'.join(line)
    return line


def _decode_dict(line):
    """
    Decode dict of key:value pairs from user data file

    @param line: line containing a dict, encoded with _encode_dict
    @rtype: dict
    @return: dict  unicode:unicode items
    """
    items = {}
    for item in line.split('\t'):
        item = item.strip()
        if not item:
            continue
        key, value = item.split(':', 1)
        items[key] = value
    return items


_ = lambda x: x

