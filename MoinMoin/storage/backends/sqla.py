# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Backends - SQLAlchemy Backend

    This backend utilizes the power of SQLAlchemy.
    You can use it to store your wiki contents using any database supported by
    SQLAlchemy. This includes SQLite, PostgreSQL and MySQL.

    @copyright: 2009 MoinMoin:ChristopherDenter,
    @license: GNU GPL, see COPYING for details.
"""
import time
from StringIO import StringIO
from threading import Lock

from sqlalchemy import create_engine, Column, Unicode, Integer, Binary, String, PickleType, ForeignKey
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import sessionmaker, relation, backref, deferred
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
# Only used/needed for development/testing:
from sqlalchemy.pool import StaticPool

from MoinMoin.storage import Backend, Item, Revision, NewRevision, StoredRevision
from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError, NoSuchRevisionError, \
                                   RevisionAlreadyExistsError, StorageError


Base = declarative_base()

NAME_LEN = 512


class SQLAlchemyBackend(Backend):
    """
    The actual SQLAlchemyBackend.
    """
    def __init__(self, db_uri=None, verbose=False):
        if db_uri is None:
            # These are settings that apply only for development / testing only. The additional args are necessary
            # due to some limitations of the in-memory sqlite database.
            db_uri = 'sqlite:///:memory:'
            self.engine = create_engine(db_uri, poolclass=StaticPool, connect_args={'check_same_thread': False})
        else:
            self.engine = create_engine(db_uri, echo=verbose, echo_pool=verbose)

        # Our factory for sessions. Note: We do NOT define this module-level because then different SQLABackends
        # using different engines (potentially different databases) would all use the same Session object with the
        # same engine that the backend instance that was created last bound it to.
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create the database schema (for all tables)
        SQLAItem.metadata.bind = self.engine
        SQLAItem.metadata.create_all()
        # {id : Lockobject} -- lock registry for item metadata locks
        self._item_metadata_lock = {}

    def has_item(self, itemname):
        try:
            session = self.Session()
            session.query(SQLAItem).filter_by(_name=itemname).one()
            return True
        except NoResultFound:
            return False
        finally:
            session.close()

    def get_item(self, itemname):
        """
        Returns item object or raises Exception if that item does not exist.

        @type itemname: unicode
        @param itemname: The name of the item we want to get.
        @rtype: item object
        @raise NoSuchItemError: No item with name 'itemname' is known to this backend.
        """
        session = self.Session()
        # The following fails if not EXACTLY one column is found, i.e., it also fails
        # if MORE than one item is found, which should not happen since names should be
        # unique
        try:
            item = session.query(SQLAItem).filter_by(_name=itemname).one()
            # SQLA doesn't call __init__, so we need to take care of that.
            item.setup(self)
            # Maybe somebody already got an instance of this Item and thus there already is a Lock for that Item.
            if not item.id in self._item_metadata_lock:
                self._item_metadata_lock[item.id] = Lock()
            return item
        except NoResultFound:
            raise NoSuchItemError("The item '%s' could not be found." % itemname)
        finally:
            session.close()

    def create_item(self, itemname):
        """
        Creates an item with a given itemname. If that item already exists,
        raise an exception.

        @type itemname: unicode
        @param itemname: Name of the item we want to create.
        @rtype: item object
        @raise ItemAlreadyExistsError: The item you were trying to create already exists.
        """
        if not isinstance(itemname, (str, unicode)):
            raise TypeError("Itemnames must have string type, not %s" % (type(itemname)))

        if self.has_item(itemname):
            raise ItemAlreadyExistsError("An item with the name %s already exists." % itemname)

        item = SQLAItem(self, itemname)
        return item

    def history(self, reverse=True):
        session = self.Session()
        col = SQLARevision.id
        if reverse:
            col = col.desc()
        for rev in session.query(SQLARevision).order_by(col).yield_per(1):
            rev.setup(self)
            yield rev
        session.close()

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).
        As iteritems() is used rather often while accessing *all* items in most cases,
        we preload them all at once and then just iterate over them, yielding each
        item individually to conform with the storage API.
        The benefit is that we do not issue a query for each individual item, but
        only a single query.

        @see: Backend.history.__doc__
        """
        session = self.Session()
        all_items = session.query(SQLAItem).all()
        session.close()
        for item in all_items:
            item.setup(self)
            yield item

    def _create_revision(self, item, revno):
        """
        Takes an item object and creates a new revision. Note that you need to pass
        a revision number for concurrency-reasons. The revno passed must be
        greater than the revision number of the items most recent revision.
        The newly created revision-object is returned to the caller.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision we want to create.
        @precondition: item.get_revision(-1).revno < revno
        @return: Object of class Revision.
        @raise RevisionAlreadyExistsError: Raised if a revision with that number
        already exists on item.
        @raise RevisionNumberMismatchError: Raised if precondition is not
        fulfilled. Note: This behavior will be changed, allowing monotonic
        revnos and not requiring revnos to be subsequent as well.
        """
        rev = SQLARevision(item, revno)
        rev.session = self.Session()
        rev.session.add(rev)
        return rev

    def _rename_item(self, item, newname):
        """
        Renames a given item. Raises Exception if the item you are trying to rename
        does not exist or if the newname is already chosen by another item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type newname: string
        @param newname: Name of item after this operation has succeeded.
        @precondition: self.has_item(newname) == False
        @postcondition: self.has_item(newname) == True
        @raises ItemAlreadyExistsError: Raised if an item with name 'newname'
        already exists.
        @raises AssertionError: Precondition not fulfilled. (Item not yet
        committed to storage)
        @return: None
        """
        if item.id is None:
            raise AssertionError("Item not yet committed to storage. Cannot be renamed.")

        session = self.Session()
        item = session.query(SQLAItem).get(item.id)
        item._name = newname
        try:
            session.commit()
        except IntegrityError:
            raise ItemAlreadyExistsError("Rename operation failed. There already is " + \
                                         "an item named '%s'." % newname)
        finally:
            session.close()

    def _commit_item(self, revision):
        """
        Commits the changes that have been done to a given item. That is, after you
        created a revision on that item and filled it with data you still need to
        commit() it. You need to pass the revision you want to commit. The item
        can be looked up by the revisions 'item' property.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to commit to  storage.
        @return: None
        """
        item = revision.item
        session = revision.session

        try:
            # flush item
            if item.id is None:
                session.add(item)
                session.flush()
        except IntegrityError:
            raise ItemAlreadyExistsError("An item with that name already exists.")
        except DataError:
            raise StorageError("The item's name is too long for this backend. It must be less than %s." % NAME_LEN)
        else:
            # Flushing of item succeeded. That means we can try to flush the revision.
            if revision.timestamp is None:
                revision.timestamp = int(time.time())
            revision._data.close()
            session.add(revision)
            try:
                session.flush()
            except IntegrityError:
                raise RevisionAlreadyExistsError("A revision with revno %d already exists on the item." \
                                                  % (revision.revno))
            else:
                # Flushing of revision succeeded as well. All is fine. We can now commit()
                session.commit()
                # After committing, the Item has an id and we can create a metadata lock for it
                self._item_metadata_lock[item.id] = Lock()
        finally:
            session.close()


    def _rollback_item(self, revision):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to roll back.
        @return: None
        """
        session = revision.session
        session.rollback()

    def _change_item_metadata(self, item):
        """
        @see: Backend._change_item_metadata.__doc__
        """
        if item.id is None:
            # If this is the case it means that we operate on an Item that has not been
            # committed yet and thus we should not use a Lock in persistant storage.
            pass
        else:
            self._item_metadata_lock[item.id].acquire()

    def _publish_item_metadata(self, item):
        """
        This method tries to release a lock on the given item and put the newly
        added Metadata of the item to storage.
        You need to call this method after altering the metadata of the item.
        E.g.:   item.change_metadata()
                item["metadata_key"] = "metadata_value"
                item.publish_metadata()  # Invokes this method

        The lock this method releases is acquired by the change_metadata method.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @raise AssertionError: item was not locked
        @return: None
        """
        # XXX This should just be tried and the exception be caught
        if item.id is None and self.has_item(item.name):
            raise ItemAlreadyExistsError("The Item whose metadata you tried to publish already exists.")
        session = self.Session()
        # XXX can item really already be in another session?
        session.add(item)
        session.commit()
        try:
            lock = self._item_metadata_lock[item.id]
        except KeyError:
            # Item hasn't been committed before publish, hence no lock.
            pass
        else:
            lock.release()

    def _get_item_metadata(self, item):
        """
        Load metadata for a given item, return dict.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        # When the item is restored from the db, it's _metadata should already
        # be populated. If not, it means there isn't any.
        return {}


class SQLAItem(Item, Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    _name = Column(Unicode(NAME_LEN), unique=True, index=True)
    _metadata = deferred(Column(PickleType))

    def __init__(self, backend, itemname):
        self._name = itemname
        self.setup(backend)

    def setup(self, backend):
        self._backend = backend
        self._locked = False
        self._read_accessed = False
        self._uncommitted_revision = None
        self.element_attrs = dict(name=self._name)

    def list_revisions(self):
        # XXX Why does this not work?
        # return [rev.revno for rev in self._revisions if rev.id is not None]
        session = self._backend.Session()
        revisions = session.query(SQLARevision).filter(SQLARevision._item_id==self.id).all()
        revnos = [rev.revno for rev in revisions]
        session.close()
        return revnos

    def get_revision(self, revno):
        try:
            session = self._backend.Session()
            if revno == -1:
                revnos = self.list_revisions()
                try:
                    revno = revnos[-1]
                except IndexError:
                    raise NoResultFound
            rev = session.query(SQLARevision).filter(SQLARevision._item_id==self.id).filter(SQLARevision._revno==revno).one()
            rev.setup(self._backend)
            rev.session = session
            rev.session.add(rev)
            return rev
        except NoResultFound:
            raise NoSuchRevisionError("Item %s has no revision %d." % (self.name, revno))

    def destroy(self):
        session = self._backend.Session()
        session.delete(self)
        session.commit()


class Chunk(Base):
    """
    A chunk of data.
    """
    __tablename__ = 'rev_data_chunks'

    id = Column(Integer, primary_key=True)
    chunkno = Column(Integer)
    _container_id = Column(Integer, ForeignKey('rev_data.id'))

    chunksize = 64 * 1024
    _data = Column(Binary(chunksize))

    def __init__(self, chunkno, data=''):
        self.chunkno = chunkno
        assert len(data) <= self.chunksize
        self._data = data

    @property
    def data(self):
        """
        Since we store the chunk's data internally as Binary type, we
        get buffer objects back from the DB. We need to convert them
        to str in order to work with them.
        """
        return str(self._data)

    def write(self, data):
        remaining = self.chunksize - len(self.data)
        write_data = data[:remaining]
        self._data += write_data
        return len(write_data)


class Data(Base):
    """
    Data that is assembled from smaller chunks.
    Bookkeeping is done here.
    """
    __tablename__ = 'rev_data'

    id = Column(Integer, primary_key=True)
    _chunks = relation(Chunk, order_by=Chunk.id, cascade='save-update')
    _revision_id = Column(Integer, ForeignKey('revisions.id'))
    size = Column(Integer)

    def __init__(self):
        self.setup()
        self.size = 0

    # XXX use reconstructor
    def setup(self):
        """
        This is different from __init__ as it may be also invoked explicitly
        when the object is returned from the database. We may as well call
        __init__ directly, but having a separate method for that makes it clearer.
        """
        self.chunkno = 0
        self._last_chunk = Chunk(self.chunkno)
        self.cursor_pos = 0

    def write(self, data):
        """
        The given data is split into chunks and stored in Chunk objects.
        Each chunk is 'filled' until it is full (i.e., Chunk.chunksize == len(Chunk.data)).
        Only the last chunk may not be filled completely.
        This does *only* support sequential writing of data, because otherwise
        we'd need to re-order potentially all chunks after the cursor position.

        @type data: str
        @param data: The data we want to split and write to the DB in chunks.
        """
        # XXX This currently relies on the autoflush feature of the session. It should ideally
        #     flush after every chunk.
        while data:
            written = self._last_chunk.write(data)
            if written:
                self.size += written
                data = data[written:]
            else:
                self.chunkno += 1
                self._chunks.append(self._last_chunk)
                self._last_chunk = Chunk(self.chunkno)

    def read(self, amount=None):
        chunksize = self._last_chunk.chunksize
        # The first chunk that contains the data we want to read
        # Perhaps we have already read a part of the first chunk before. We want to skip that.
        first, skip = divmod(self.cursor_pos, chunksize)

        # No amount given means: Read all that remains (from viewpoint of cursor_pos)
        if amount is None or amount < 0 or amount >= (self.size - self.cursor_pos):
            # From the first chunk we read everything after skip
            try:
                begin = self._chunks[first].data[skip:]
            except IndexError:
                # first depends on cursor_pos which may have been seek()ed to a value far
                # larger than our size. This is allowed, but then read() returns '' (because there's nothing left to read).
                begin = ''

            remaining_chunks = self._chunks[first+1:]
            # We've read to the end, now set the cursor on the last+1
            self.cursor_pos = self.size
            end = "".join([chunk.data for chunk in remaining_chunks])
            return begin + end

        # Otherwise we need all chunks up to last
        last = first + amount / chunksize
        # Get all those chunks
        chunks = self._chunks[first:last+1]
        begin = chunks[0].data[skip:skip+amount]
        # We just concatenate the contents of all but the first and last chunks
        mid = "".join([chunk.data for chunk in chunks[1:-1]])
        # And from the last chunk, we only take what is remaining to get `amount` bytes in total.
        remaining = (amount - len(begin+mid)) % chunksize
        end = chunks[-1].data[:remaining]
        self.cursor_pos += amount
        assert len(begin+mid+end) == amount
        return begin + mid + end

    def seek(self, pos, mode=0):
        if mode == 0:
            self.cursor_pos = pos
        elif mode == 1:
            self.cursor_pos += pos
        elif mode == 2:
            self.cursor_pos = self.size + pos

    def tell(self):
        return self.cursor_pos

    def close(self):
        self._chunks.append(self._last_chunk)


class SQLARevision(NewRevision, Base):
    __tablename__ = 'revisions'
    __table_args__ = (UniqueConstraint('_item_id', '_revno'), {})

    id = Column(Integer, primary_key=True)
    _data = relation(Data, uselist=False, lazy=True)
    _item_id = Column(Integer, ForeignKey('items.id'), index=True)
    _item = relation(SQLAItem, backref=backref('_revisions', cascade='delete, delete-orphan', lazy=True), uselist=False, lazy=True)
    _revno = Column(Integer, index=True)
    _metadata = Column(PickleType)
    _timestamp = Column(Integer)

    def __init__(self, item, revno, timestamp=None):
        self._revno = revno
        self._timestamp = timestamp
        self.element_attrs = dict(revno=str(revno))
        self.setup(item._backend)
        self._item = item

    def __del__(self):
        # XXX XXX XXX DO NOT RELY ON THIS
        try:
            self.session.close()
        except AttributeError:
            pass

    def setup(self, backend):
        if self._data is None:
            self._data = Data()
        if self._metadata is None:
            self._metadata = {}
        self._data.setup()
        self._backend = backend

    def write(self, data):
        self._data.write(data)

    def read(self, amount=None):
        return self._data.read(amount)

    def seek(self, pos, mode=0):
        self._data.seek(pos, mode)

    def tell(self):
        return self._data.tell()

    def close(self):
        self.session.close()

    def __setitem__(self, key, value):
        NewRevision.__setitem__(self, key, value)

    @property
    def size(self):
        return self._data.size

    def destroy(self):
        session = self._backend.Session.object_session(self)
        if session is None:
            session = self._backend.Session()
        session.delete(self)
        session.commit()
