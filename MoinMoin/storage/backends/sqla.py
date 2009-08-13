# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Backends - SQLAlchemy Backend

    This backend utilizes the power of SQLAlchemy.
    You can use it to store your wiki contents using any database supported by
    SQLAlchemy. This includes SQLite, Postgres and MySQL.

    @copyright: 2009 MoinMoin:ChristopherDenter,
    @license: GNU GPL, see COPYING for details.
"""
from StringIO import StringIO
from threading import Lock

from sqlalchemy import create_engine, Column, Integer, Binary, String, PickleType, ForeignKey
from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base

from MoinMoin.storage import Backend, Item, Revision, NewRevision, StoredRevision
from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError, NoSuchRevisionError


Base = declarative_base()
# Our factory for sessions:
Session = sessionmaker()


class SQLAlchemyBackend(Backend):
    """
    The actual SQLAlchemyBackend.
    """
    def __init__(self, db_uri='sqlite:///:memory:', verbose=False):

        ## TODO DEVELOPMENT SETTINGS --- Remove when in-memory sqlite database is not needed anymore
        from sqlalchemy.pool import StaticPool
        self.engine = create_engine('sqlite:///:memory:', poolclass=StaticPool, connect_args={'check_same_thread': False})
        ## TODO </development settings>

        # Create the database schema
        SQLAItem.metadata.bind = self.engine
        SQLAItem.metadata.create_all()

        self._item_metadata_lock = {}       # {id : Lockobject}

    def has_item(self, itemname):
        try:
            session = Session()
            session.query(SQLAItem).filter_by(_name=itemname).one()
            return True
        except NoResultFound:
            return False

    def get_item(self, itemname):
        """
        Returns item object or raises Exception if that item does not exist.

        @type itemname: unicode
        @param itemname: The name of the item we want to get.
        @rtype: item object
        @raise NoSuchItemError: No item with name 'itemname' is known to this backend.
        """
        session = Session()
        # The following fails if not EXACTLY one column is found, i.e., it also fails
        # if MORE than one item is found, which should not happen since names should be
        # unique
        try:
            item = session.query(SQLAItem).filter_by(_name=itemname).one()
            # XXX Can you make this more beautiful?
            # The _backend attribute is not stored in the database. Restore it manually.
            #
            # SQLA doesn't call __init__, so we need to take care of that.
            item.__init__(self, itemname, session)
            return item
        except NoResultFound:
            raise NoSuchItemError("The item '%s' could not be found." % itemname)

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
        # Maybe somebody already got an instance of this Item and thus there already is a Lock for that Item.
        if not item.id in self._item_metadata_lock:
            self._item_metadata_lock[item.id] = Lock()
        return item

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).

        @rtype: iterator of item objects
        """
        session = Session()
        return session.query(SQLAItem).all()
        session.close()

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
        session = Session()
        itemname = item.name
        try:
            item = session.query(SQLAItem).filter_by(_name=itemname).one()
        except NoResultFound:
            raise NoSuchItemError("There is no item %s." % item.name)
        try:
            new_item = session.query(SQLAItem).filter_by(_name=newname).one()
        except NoResultFound:
            # Target item should not already exist.
            pass
        else:
            raise ItemAlreadyExistsError("There already is an item with the name %s." % newname)

        item._name = newname
        # not necessary? session.add(item)
        session.commit()

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
        self._item_metadata_lock[revision.item.id] = Lock()
        revision.session.commit()

    def _rollback_item(self, revision):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to roll back.
        @return: None
        """
        revision.session.rollback()

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
        if item.id is None and self.has_item(item.name):
            raise  ItemAlreadyExistsError, "The Item whose metadata you tried to publish already exists."
        item.session.commit()
        try:
            self._item_metadata_lock[item.id].release()
        except KeyError:
            # Item hasn't been committed before publish, hence no lock.
            pass

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

    def _get_revision_metadata(self, revision):
        """
        Load metadata for a given revision, returns dict.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: dict of metadata key / value pairs.
        """
        raise NotImplementedError()

    def _get_revision_timestamp(self, revision):
        """
        Lazily load the revision's timestamp. If accessing it
        is cheap, it can be given as a parameter to StoredRevision
        instantiation instead.
        Return the timestamp (a long).

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: long
        """
        raise NotImplementedError()

    def _get_revision_size(self, revision):
        """
        Lazily access the revision's data size. This needs not be
        implemented if all StoredRevision objects are instantiated
        with the size= keyword parameter.

        @type revision: Object of a subclass of Revision.
        @param revision: The revision on which we want to operate.
        @return: int
        """
        raise NotImplementedError()


class SQLAItem(Item, Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    _name = Column(String)
    _metadata = Column(PickleType)

    def __init__(self, backend, itemname, session=None):
        self._backend = backend
        self._name = itemname
        self._locked = False
        self._read_accessed = False
        self._uncommitted_revision = None
        self.element_attrs = dict(name=itemname)
        if session is None:
            session = Session()
        self.session = session
        self.session.add(self)

    def list_revisions(self):
        return [rev.revno for rev in self._revisions.all() if rev.id is not None]

    def get_revision(self, revno):
        try:
            session = Session()
            if revno == -1:
                revno = self.list_revisions()[-1]
            rev = session.query(SQLARevision).filter(SQLARevision._item_id==self.id).filter(SQLARevision._revno==revno).one()
            rev.__init__(self, revno)
            return rev
        except (NoResultFound, IndexError):
            raise NoSuchRevisionError("Item %s has no revision %d." % (self.name, revno))
        finally:
            session.close()


class Chunk(Base):
    """
    A chunk of data.
    """
    __tablename__ = 'rev_data_chunks'

    id = Column(Integer, primary_key=True)
    chunkno = Column(Integer)
    data = Column(String)
    _container_id = Column(Integer, ForeignKey('rev_data.id'))

    def __init__(self, chunkno):
        self.chunkno = chunkno
        self.data = ""


class Data(Base):
    """
    Data that is assembled from smaller chunks.
    Bookkeeping is done here.
    """
    __tablename__ = 'rev_data'

    id = Column(Integer, primary_key=True)
    _chunks = relation(Chunk, order_by=Chunk.id)
    _revision_id = Column(Integer, ForeignKey('revisions.id'))
    size = Column(Integer)

    chunksize = 4

    def __init__(self, session):
        self.chunkno = 0
        self._last_chunk = Chunk(self.chunkno)
        self.cursor_pos = 0
        self.size = 0
        self.session = session
        self.session.add(self)

    def write(self, data):
        while data:
            # How much space is left in the current chunk?
            chunk_space_left = self.chunksize - len(self._last_chunk.data)
            # If there's no space left, create a new chunk
            if chunk_space_left == 0:
                self._last_chunk = Chunk(self.chunkno)
                chunk_space_left = self.chunksize
            data_chunk = data[:chunk_space_left]
            self.size += len(data_chunk)
            self._last_chunk.data += data_chunk
            self._chunks.append(self._last_chunk)
            self.session.add(self._last_chunk)
            self.session.commit()
            self.chunkno += 1
            data = data[chunk_space_left:]

    def tell(self):
        return self.cursor_pos

    def seek(self, pos, mode=0):
        if mode == 0:
            self.cursor_pos = pos
        elif mode == 1:
            self.cursor_pos += pos
        elif mode == 2:
            self.cursor_pos = self.size + pos

    def read(self, amount=None):
        # The first chunk that contains the data we want to read
        # Perhaps we have already read a part of the first chunk before. We want to skip that.
        first, skip = divmod(self.cursor_pos, self.chunksize)

        # No amount given means: Read all that remains (from viewpoint of cursor_pos)
        if amount is None or amount > self.size:
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
        last = first + amount / self.chunksize
        # Get all those chunks
        chunks = self._chunks[first:last+1]
        begin = chunks[0].data[skip:skip+amount]
        # We just concatenate the contents of all but the first and last chunks
        mid = "".join([chunk.data for chunk in chunks[1:-1]])
        # And from the last chunk, we only take what is remaining to get `amount` bytes in total.
        remaining = (amount - len(begin+mid)) % self.chunksize
        end = chunks[-1].data[:remaining]
        self.cursor_pos += amount
        assert len(begin+mid+end) == amount
        return begin + mid + end


class SQLARevision(Revision, Base):
    __tablename__ = 'revisions'

    id = Column(Integer, primary_key=True)
    _data = relation(Data, uselist=False)
    _item_id = Column(Integer, ForeignKey('items.id'))
    _item = relation(SQLAItem, backref=backref('_revisions', order_by=id, lazy='dynamic', cascade=''), cascade='', uselist=False)
    _revno = Column(Integer)
    _metadata = Column(PickleType)
    _timestamp = Column(Integer)

    def __init__(self, item, revno, timestamp=None):
        self._revno = revno
        self._item = item
        self._backend = item._backend
        self._timestamp = timestamp
        self.element_attrs = dict(revno=str(revno))
        self.session = item.session
        self.session.add(self)

    def write(self, data):
        if self._data is None:
            self._data = Data(self.session)
        self._data.write(data)

    def read(self, amount=None):
        return self._data.read(amount)

    def seek(self, pos, mode=0):
        self._data.seek(pos, mode)

    def tell(self):
        return self._data.tell()

