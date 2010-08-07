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

from MoinMoin import log
logging = log.getLogger(__name__)

class ArchiveException(Exception):
    """
    exception class used in case of trouble with opening/listing an archive
    """

class ArchiveConverter(TableMixin):
    """
    Base class for archive converters, convert an archive to a DOM table
    with an archive listing.
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, fileobj):
        try:
            contents = self.list_contents(fileobj)
            return self.build_dom_table(contents)
        except ArchiveException, err:
            logging.exception("An exception within archive file handling occurred:")
            # XXX we also use a table for error reporting, could be
            # something more adequate, though:
            return self.build_dom_table([[str(err)]])

    def list_contents(self, fileobj):
        """
        analyze archive we get as fileobj and return data for table rendering.
        
        We return a list of rows, each row is a list of cells.
        
        Usually each row is [size, timestamp, name] for each archive member.

        In case of problems, it shall raise ArchiveException(error_msg).
        """
        raise NotImplementedError


class TarConverter(ArchiveConverter):
    """
    Support listing tar files.
    """
    def list_contents(self, fileobj):
        try:
            rows = []
            tf = tarfile.open(fileobj=fileobj, mode='r')
            for tinfo in tf.getmembers():
                rows.append([
                    tinfo.size,
                    time.strftime("%Y-%02m-%02d %02H:%02M:%02S", time.gmtime(tinfo.mtime)),
                    tinfo.name,
                ])
            return rows
        except tarfile.TarError, err:
            raise ArchiveException(str(err))


class ZipConverter(ArchiveConverter):
    """
    Support listing zip files.
    """
    def list_contents(self, fileobj):
        try:
            rows = []
            zf = zipfile.ZipFile(fileobj, mode='r')
            for zinfo in zf.filelist:
                rows.append([
                    zinfo.file_size,
                    "%d-%02d-%02d %02d:%02d:%02d" % zinfo.date_time,
                    zinfo.filename,
                ])
            return rows
        except (RuntimeError, zipfile.BadZipfile), err:
            # RuntimeError is raised by zipfile stdlib module in case of
            # problems (like inconsistent slash and backslash usage in the
            # archive or a defective zip file).
            raise ArchiveException(str(err))


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(TarConverter._factory, Type('application/x-tar'), type_moin_document)
default_registry.register(TarConverter._factory, Type('application/x-gtar'), type_moin_document)
default_registry.register(ZipConverter._factory, Type('application/zip'), type_moin_document)

