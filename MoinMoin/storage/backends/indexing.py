# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Indexing Mixin Classes

    Other backends mix in the Indexing*Mixin classes into their Backend,
    Item, Revision classes to support flexible metadata indexing and querying
    for wiki items / revisions

    Wiki items are identified by a UUID (in the index, it is internally mapped
    to an integer for more efficient processing).
    Revisions of an item are identified by a integer revision number (and the
    parent item).

    The wiki item name is contained in the item revision's metadata.
    If you rename an item, this is done by creating a new revision with a different
    (new) name in its revision metadata.

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import log
logging = log.getLogger(__name__)


class IndexingBackendMixin(object):
    """
    Backend indexing support
    """
    def __init__(self, *args, **kw):
        index_uri = kw.pop('index_uri', None)
        super(IndexingBackendMixin, self).__init__(*args, **kw)
        assert not hasattr(self, '_index')
        self._index = ItemIndex(index_uri)


class IndexingItemMixin(object):
    """
    Item indexing support

    When a commit happens, index stuff.
    """
    def __init__(self, backend, *args, **kw):
        super(IndexingItemMixin, self).__init__(backend, *args, **kw)
        assert not hasattr(self, '_index')
        self._index = backend._index
        self.__unindexed_revision = None

    def create_revision(self, revno):
        self.__unindexed_revision = super(IndexingItemMixin, self).create_revision(revno)
        return self.__unindexed_revision

    def commit(self):
        self.__unindexed_revision.update_index()
        self.__unindexed_revision = None
        return super(IndexingItemMixin, self).commit()

    def rollback(self):
        self.__unindexed_revision = None
        return super(IndexingItemMixin, self).rollback()

    def publish_metadata(self):
        self.update_index()
        return super(IndexingItemMixin, self).publish_metadata()

    def destroy(self):
        self.remove_index()
        return super(IndexingItemMixin, self).destroy()

    def update_index(self):
        """
        update the index with metadata of this item

        this is automatically called by item.publish_metadata() and can be used by a indexer script also.
        """
        logging.debug("item %r update index:" % (self.name, ))
        for k, v in self.items():
            logging.debug(" * item meta %r: %r" % (k, v))
        self._index.update_item(metas=self)

    def remove_index(self):
        """
        update the index, removing everything related to this item
        """
        logging.debug("item %r remove index!" % (self.name, ))
        self._index.remove_item(metas=self)


class IndexingRevisionMixin(object):
    """
    Revision indexing support
    """
    def __init__(self, item, *args, **kw):
        super(IndexingRevisionMixin, self).__init__(item, *args, **kw)
        assert not hasattr(self, '_index')
        self._index = item._index

    def destroy(self):
        self.remove_index()
        return super(IndexingRevisionMixin, self).destroy()

    def update_index(self):
        """
        update the index with metadata of this revision

        this is automatically called by item.commit() and can be used by a indexer script also.
        """
        name = self.item.name
        revno = self.revno
        metas = self
        logging.debug("item %r revno %d update index:" % (name, revno))
        for k, v in metas.items():
            logging.debug(" * rev meta %r: %r" % (k, v))
        uuid = name # XXX
        self._index.add_rev(uuid, revno, metas)

    def remove_index(self):
        """
        update the index, removing everything related to this revision
        """
        name = self.item.name
        revno = self.revno
        metas = self
        logging.debug("item %r revno %d remove index!" % (name, revno))
        uuid = name # XXX
        self._index.remove_rev(uuid, revno)

    # TODO maybe use this class later for data indexing also,
    # TODO by intercepting write() to index data written to a revision



import time, datetime
import os
from uuid import uuid4 as gen_uuid

from kvstore import KVStoreMeta, KVStore

from sqlalchemy import Table, Column, Integer, String, Unicode, DateTime, PickleType, MetaData, ForeignKey
from sqlalchemy import create_engine, select
from sqlalchemy.sql import and_, exists


class ItemIndex(object):
    """
    Index for Items/Revisions
    """
    def __init__(self, index_uri):
        self.engine = create_engine(index_uri, echo=False)
        metadata = MetaData()

        # for sqlite, lengths are not needed, but for other SQL DBs:
        UUID_LEN = 32
        VALUE_LEN = KVStoreMeta.VALUE_LEN # we duplicate values from there to our table

        # items have a persistent uuid
        self.item_table = Table('item_table', metadata,
            Column('id', Integer, primary_key=True), # item's internal uuid
            # reference to current revision:
            Column('current', ForeignKey('rev_table.id', name="current", use_alter=True), type_=Integer),
            # some important stuff duplicated here for easy availability:
            # from item metadata:
            Column('uuid', String(UUID_LEN), index=True, unique=True), # item's official persistent uuid
            # from current revision's metadata:
            Column('name', Unicode(VALUE_LEN), index=True, unique=True),
            Column('mimetype', Unicode(VALUE_LEN), index=True),
            Column('acl', Unicode(VALUE_LEN)),
        )

        # revisions have a revno and a parent item
        self.rev_table = Table('rev_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('item_id', ForeignKey('item_table.id')),
            Column('revno', Integer),
            # some important stuff duplicated here for easy availability:
            Column('datetime', DateTime, index=True),
        )

        item_kvmeta = KVStoreMeta('item', metadata, Integer)
        rev_kvmeta = KVStoreMeta('rev', metadata, Integer)
        metadata.create_all(self.engine)
        self.conn = self.engine.connect()
        self.item_kvstore = KVStore(item_kvmeta, self.conn)
        self.rev_kvstore = KVStore(rev_kvmeta, self.conn)

    def get_item_id(self, uuid):
        """
        return the internal item id for some item with uuid or
        None, if not found.
        """
        item_table = self.item_table
        sel = select([item_table.c.id], item_table.c.uuid == uuid)
        result = self.conn.execute(sel).fetchone()
        if result:
            return result[0]

    def update_item(self, metas):
        """
        update an item with item-level metadata <metas>

        note: if item does not exist already, it is added
        """
        name = metas.get('name', '') # item name (if revisioned: same as current revision's name) XXX not there yet
        uuid = metas.get('uuid', name) # item uuid (never changes) XXX we use name as long we have no uuid
        item_table = self.item_table
        item_id = self.get_item_id(uuid)
        if item_id is None:
            ins = item_table.insert().values(uuid=uuid, name=name)
            res = self.conn.execute(ins)
            item_id = res.last_inserted_ids()[0]
        self.item_kvstore.store_kv(item_id, metas)
        return item_id

    def cache_in_item(self, item_id, rev_id, rev_metas):
        """
        cache some important values from current revision into item for easy availability
        """
        item_table = self.item_table
        upd = item_table.update().where(item_table.c.id == item_id).values(
            current=rev_id,
            name=rev_metas['name'],
            mimetype=rev_metas['mimetype'],
            acl=rev_metas.get('acl', ''),
        )
        res = self.conn.execute(upd)

    def remove_item(self, metas):
        """
        remove an item

        note: does not remove revisions, these should be removed first
        """
        item_table = self.item_table
        uuid = metas['uuid'] # item uuid (never changes)
        item_id = self.get_item_id(uuid)
        if item_id is not None:
            self.item_kvstore.store_kv(item_id, {})
            delete = item_table.delete().where(item_table.c.id == item_id)
            self.conn.execute(delete)

    def add_rev(self, uuid, revno, metas):
        """
        add a new revision <revno> for item <uuid> with metadata <metas>

        currently assumes that added revision will be latest/current revision (not older/non-current)
        """
        rev_table = self.rev_table
        item_metas = dict(uuid=uuid, name=metas['name'])
        item_id = self.update_item(item_metas)

        # get (or create) the revision entry
        sel = select([rev_table.c.id], and_(rev_table.c.revno == revno, rev_table.c.item_id == item_id))
        result = self.conn.execute(sel).fetchone()
        if result:
            rev_id = result[0]
        else:
            dt = datetime.datetime.utcfromtimestamp(0)
            ins = rev_table.insert().values(revno=revno, item_id=item_id, datetime=dt)
            res = self.conn.execute(ins)
            rev_id = res.last_inserted_ids()[0]

        self.rev_kvstore.store_kv(rev_id, metas)

        self.cache_in_item(item_id, rev_id, metas)
        return rev_id

    def remove_rev(self, uuid, revno):
        """
        remove a revision <revno> of item <uuid>

        Note:
        * does not update metadata values cached in item (this is only a
          problem if you delete latest revision AND you don't delete the
          whole item anyway)
        """
        item_id = self.get_item_id(uuid)
        assert item_id is not None

        # get the revision entry
        rev_table = self.rev_table
        sel = select([rev_table.c.id], and_(rev_table.c.revno == revno, rev_table.c.item_id == item_id))
        result = self.conn.execute(sel).fetchone()
        if result:
            rev_id = result[0]
            self.rev_kvstore.store_kv(rev_id, {})
            delete = rev_table.delete().where(rev_table.c.id == rev_id)
            self.conn.execute(delete)

    def get_uuid_revno_name(self, rev_id):
        """
        get item uuid and revision number by rev_id
        """
        item_table = self.item_table
        rev_table = self.rev_table
        sel = select([item_table.c.uuid, rev_table.c.revno, item_table.c.name],
                 and_(
                      rev_table.c.id == rev_id,
                      item_table.c.id == rev_table.c.item_id))
        return self.conn.execute(sel).fetchone()

