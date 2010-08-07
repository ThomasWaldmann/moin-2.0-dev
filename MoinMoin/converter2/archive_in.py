"""
MoinMoin - Archives converter (e.g. zip, tar)

Make a DOM Tree representation of an archive (== list contents of it in a table).

@copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import time
import tarfile
import zipfile

from ._table import TableMixin

class ArchiveConverter(TableMixin):
    """
    Base class for archive converters, convert an archive to a DOM table
    with an archive listing.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, fileobj):
        contents = self.list_contents(fileobj)
        return self.build_dom_table(contents)

    def list_contents(self, fileobj):
        """
        analyze archive we get as fileobj and return data for table rendering.
        
        We return a list of rows, each row is a list of cells.
        
        Usually each row is [size, timestamp, name] for each archive member.

        In case of problems, we return only 1 row with [error_msg].
        """
        raise NotImplementedError


class TarConverter(ArchiveConverter):
    """
    Support listing tar files.
    """
    def list_contents(self, fileobj):
        rows = []
        try:
            tf = tarfile.open(fileobj=fileobj, mode='r')
            for tinfo in tf.getmembers():
                rows.append([
                    tinfo.size,
                    time.strftime("%Y-%02m-%02d %02H:%02M:%02S", time.gmtime(tinfo.mtime)),
                    tinfo.name,
                ])
        except tarfile.TarError, err:
            logging.exception("An exception within tar file handling occurred:")
            rows = [[str(err)]]
        return rows


class ZipConverter(ArchiveConverter):
    """
    Support listing zip files.
    """
    def list_contents(self, fileobj):
        rows = []
        try:
            zf = zipfile.ZipFile(fileobj, mode='r')
            for zinfo in zf.filelist:
                rows.append([
                    zinfo.file_size,
                    "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time,
                    zinfo.filename,
                ])
        except (RuntimeError, zipfile.BadZipfile), err:
            # RuntimeError is raised by zipfile stdlib module in case of
            # problems (like inconsistent slash and backslash usage in the
            # archive or a defective zip file).
            logging.exception("An exception within zip file handling occurred:")
            rows = [[str(err)]]
        return rows


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(TarConverter._factory, Type('application/x-tar'), type_moin_document)
default_registry.register(TarConverter._factory, Type('application/x-gtar'), type_moin_document)
default_registry.register(ZipConverter._factory, Type('application/zip'), type_moin_document)

