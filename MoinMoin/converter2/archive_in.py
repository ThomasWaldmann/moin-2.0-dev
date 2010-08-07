"""
MoinMoin - Archives converter (e.g. zip, tar)

Make a DOM Tree representation of an archive (== list contents of it in a table).

@copyright: 2010 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import time

from ._table import TableMixin

class TarConverter(TableMixin):
    """
    Convert a tar file to the corresponding <object> in the DOM Tree (listing of tar contents).
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content):
        import tarfile
        fileobj = content # we just get the open revision data file as content
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
        return self.build_dom_table(rows)


class ZipConverter(TableMixin):
    """
    Convert a zip file to the corresponding <object> in the DOM Tree (listing of zip contents).
    """
    @classmethod
    def _factory(cls, input, output, **kw):
        return cls()

    def __call__(self, content):
        import zipfile
        fileobj = content # we just get the open revision data file as content
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
        return self.build_dom_table(rows)


from . import default_registry
from MoinMoin.util.mime import Type, type_moin_document
default_registry.register(TarConverter._factory, Type('application/x-tar'), type_moin_document)
default_registry.register(TarConverter._factory, Type('application/x-gtar'), type_moin_document)
default_registry.register(ZipConverter._factory, Type('application/zip'), type_moin_document)

