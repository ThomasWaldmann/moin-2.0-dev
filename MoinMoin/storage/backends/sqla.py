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
            item.__init__(self, itemname)
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

        session = Session()
        found = session.query(SQLAItem).filter_by(_name=itemname).all()
        if found:
            raise ItemAlreadyExistsError("An item with the name %s already exists." % itemname)
        item = SQLAItem(self, itemname)
        session.add(item)
        session.commit()
        return item

    def iteritems(self):
        """
        Returns an iterator over all items available in this backend.
        (Like the dict method).

        @rtype: iterator of item objects
        """
        session = Session()
        return session.query(SQLAItem).all()

    def _get_revision(self, item, revno):
        """
        For a given item and revision number, return the corresponding revision
        of that item.
        Note: If you pass -1 as revno, this shall return the latest revision of the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @type revno: int
        @param revno: Indicate which revision is wanted precisely. If revno is
        -1, return the most recent revision.
        @rtype: Object of class Revision
        @raise NoSuchRevisionError: No revision with that revno was found on item.
        """
        raise NotImplementedError()

    def _list_revisions(self, item):
        """
        For a given item, return a list containing all revision numbers (as ints)
        of the revisions the item has. The list must be ordered, starting with
        the oldest revision-number.
        (One may decide to delete certain revisions completely at one point. For
        that case, list_revisions does not need to return subsequent revision
        numbers. _create_revision() on the other hand must only create
        subsequent revision numbers.)

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @return: list of ints (possibly empty)
        """
        return [rev.revno for rev in item._revisions.all()]

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
        rev = SQLANewRevision(item, revno)
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
        session = Session()
        session.add(revision)
        session.commit()

    def _rollback_item(self, revision):
        """
        This method is invoked when external events happen that cannot be handled in a
        sane way and thus the changes that have been made must be rolled back.

        @type revision: Object of class NewRevision.
        @param revision: The revision we want to roll back.
        @return: None
        """
        raise NotImplementedError()

    def _change_item_metadata(self, item):
        """
        This method is used to acquire a lock on an item. This is necessary to prevent
        side-effects caused by concurrency.
        You need to call this method before altering the metadata of the item.
        E.g.:   item.change_metadata()  # Invokes this method
                item["metadata_key"] = "metadata_value"
                item.publish_metadata()

        As you can see, the lock acquired by this method is released by calling
        the publish_metadata() method on the item.

        @type item: Object of class Item.
        @param item: The Item on which we want to operate.
        @precondition: item not already locked
        @return: None
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    def _read_revision_data(self, revision, chunksize):
        """
        Called to read a given amount of bytes of a revisions data. By default, all
        data is read.

        @type revision: Object of class StoredRevision.
        @param revision: The revision on which we want to operate.
        @type chunksize: int
        @param chunksize: amount of bytes to be read at a time
        @return: string
        """
        return revision._data.read(chunksize)

    def _write_revision_data(self, revision, data):
        """
        When this method is called, the passed data is written to the revisions data.

        @type revision: Object of class NewRevision.
        @param revision: The revision on which we want to operate.
        @type data: str
        @param data: The data to be written on the revision.
        @return: None
        """
        # XXX remove this hack
        data = StringIO(data)
        revision._data.write(data)

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

    def _seek_revision_data(self, revision, position, mode):
        """
        Set the revisions cursor on the revisions data.

        @type revision: Object of StoredRevision.
        @param revision: The revision on which we want to operate.
        @type position: int
        @param position: Indicates where to position the cursor
        @type mode: int
        @param mode: 0 for 'absolute positioning', 1 to seek 'relatively to the
        current position', 2 to seek 'relative to the files end'.
        @return: None
        """
        raise NotImplementedError()


class SQLAItem(Item, Base):
    __tablename__ = 'items'

    _id = Column(Integer, primary_key=True)
    _name = Column(String)
    _metadata = Column(PickleType)

    def get_revision(self, revno):
        try:
            session = Session()
            rev = session.query(SQLAStoredRevision).filter(SQLARevision._revno==revno).one()
            rev.__init__(self, revno)
            return rev
        except NoResultFound:
            raise NoSuchRevisionError("Item %s has no revision %d." % (self.name, revno))
        finally:
            session.close()


class SQLARevision(Revision, Base):
    __tablename__ = 'revisions'

    _id = Column(Integer, primary_key=True)
    _item_id = Column(Integer, ForeignKey('items._id'))
    _item = relation(SQLAItem, backref=backref('_revisions', order_by=_id, lazy='dynamic', cascade=''), cascade='')
    _revno = Column(Integer)
    _metadata = Column(PickleType)
    _timestamp = Column(Integer)
    # TODO Find correct type for _data
    _data = Column(String)


class SQLAStoredRevision(SQLARevision, StoredRevision):
    # XXX
    def __init__(self, item, revno, timestamp=None, size=None):
        SQLARevision.__init__(self, item, revno, timestamp)
        self._size = size


class SQLANewRevision(SQLARevision, NewRevision):
    # XXX
    def __init__(self, item, revno):
        SQLARevision.__init__(self, item, revno, None)
        self._metadata = {}
        self._size = 0

