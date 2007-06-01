"""
    MoinMoin external interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import UserDict

from MoinMoin.storage.interfaces import DataBackend
from MoinMoin.storage.error import StorageError


class ItemCollection(UserDict.DictMixin):
    """
    The ItemCollection class realizes the access to the stored Items via the
    correct backend and maybe caching.
    """

    backend = None
    userobj = None

    def __init__(self, backend, userobj):
        """
        Initializes the proper StorageBackend. 
        """
        self.backend = backend
        self.userobj = userobj

    def __contains__(self, name):
        """
        Checks if an Item exists.
        """
        return self.backend.has_item(name)

    def __getitem__(self, name):
        """
        Loads an Item.
        """
        if self.backend.has_item(name):
            item = Item(name, self.backend, self.userobj)
            return item
        else:
            raise KeyError("No such item '%s'" % name)

    def __delitem__(self, name):
        """
        Deletes an Item.
        """
        self.backend.remove_item(name)

    def keys(self, filters=None):
        """
        Returns a list of all item names. With filters you can add
        filtering stuff which is described more detailed in
        StorageBackend.list_items(...).
        """
        return self.backend.list_items(filters)

    def new_item(self, name):
        """
        Returns a new Item with the given name.
        """
        if self.backend.has_item(name):
            raise StorageError("Item '%s' already exists." % name)
        
        item = Item(name, self.backend, self.userobj)
        item.new = True
        return item

class Item(UserDict.DictMixin):
    """
    The Item class represents a StorageItem. This Item has a name and revisions.
    An Item can be anything MoinMoin must save, e.g. Pages, Attachements or
    Users. A list of revision-numbers is only loaded on access. Via Item[0]
    you can access the last revision. The specified Revision is only loaded on
    access as well. On every access the ACLs will be checked.
    """

    new = False
    changed = {'added' : [], 'removed': []}   # a dict of changed revisions

    metadata = None
    name = None
    
    userobj = None
    backend = None
    
    def __init__(self, name, backend, userobj):
        """
        Initializes the Item with the required parameters.
        """
        self.metadata = Metadata(Revision(-1, self))
        self.name = name
        self.backend = backend
        self.userobj = userobj
        
        self.__revisions = None
        self.__current = None

    def __contains__(self, revno):
        """
        Checks if a Revision with the given revision-number exists.
        """
        return revno in self.revisions

    def __getitem__(self, revno):
        """
        Returns the revision specified by a revision-number (LazyLoaded). 
        """
        if revno in self:
            return Revision(revno, self)
        else:
            raise KeyError("No such revision.")

    def __delitem__(self, revno):
        """
        Deletes the Revision specified by the given revision-number.
        """
        self.revisions.remove(revno)

    def keys(self):
        """
        Returns a sorted (highest first) list of all real revision-numbers.
        """
        return self.revisions

    def new_revision(self, revno=None):
        """
        Creates and returns a new revision with the given revision-number.
        If the revision number is None the next possible number will be used. 
        """
        if revno == None:
            self.revisions = self.revisions + [self.current + 1]
        elif revno not in self:
            self.revisions = self.revisions + [revno]
    
    def get_revisions(self):
        """
        Lazy load revision list.
        """
        if self.__revisions == None:
            self.__revisions = self.backend.list_revisions(self.name)
        return self.__revisions

    revisions = property(get_revisions)

    def get_current(self):
        """
        Lazy load current revision nr.
        """
        return self.__revisions[-1]

    current = property(get_current)

    def save(self):
        """
        Saves the whole item. It checks if the Item must be created, which Revision was
        added/removed, if the data was changed and what metadata keys were changed and
        saves the changes then.
        
        TODO: implement it
        """
        pass


class Revision(object):
    """
    A Revision contains the data and metadata for one revision of the Item. The
    Metadata and Data classes will be created when the revision is created, but
    they take care that their content is loaded lazily. On every access the ACLs
    will be checked.
    """

    data = None
    metadata = None
    
    revno = None
    item = None

    # The following properties provide access to the corresponding metadata keys:
    mtime = None
    author = None
    ip = None
    hostname = None
    size = None
    comment = None
    mime_type = None
    acl = None
    action = None

    def __init__(self, revno, item):
        """
        Initalizes the Revision with the required parameters.
        """
        self.data = Data(self)
        self.metadata = Metadata(self)
        
        self.revno = revno
        self.item = item


class Metadata(UserDict.DictMixin):
    """ 
    The metadata of an Item. Access will be via a dict like interface.
    All metadata will be loaded on the first access to one key.
    On every access the ACLs will be checked.
    """

    changed = {'added' : [], 'removed': [], 'changed': []}   # a dict of changed keys

    revision = None
    
    metadata = None

    def __init__(self, revision):
        """"
        Initializes the metadata object with the required parameters.
        """
        self.revision = revision

    def __contains__(self, name):
        """
        Checks if a key exists.
        """
        self.lazy_load()
        return name in self.metadata

    def __getitem__(self, name):
        """
        Returns a specified value.
        """
        self.lazy_load()
        return self.metadata[name]

    def __setitem__(self, name, value):
        """
        Adds a value.
        """
        self.lazy_load()
        self.metadata[name] = value

    def __delitem__(self, name):
        """
        Deletes a value.
        """
        self.lazy_load()
        del self.metadata[name]

    def keys(self):
        """
        Return sa list of all metadata keys.
        """
        self.lazy_load()
        return self.metadata.keys()
    
    def lazy_load(self):
        """
        Lazy load the metadata.
        """
        if self.metadata == None:
            self.metadata = self.revision.item.backend.get_metadata(self.revision.item.name, self.revision.revno)

class Data(DataBackend):
    """
    Data offers a read and write Proxy to the DataBackend. Changes are only
    written on close() or save(). Reading always occurs on the data in the backend,
    not on the data written by write(). On every access the ACLs will be checked.
    """

    changed = False

    def __init__(self, revision):
        """
        Initializes the Data object with the required parameters.
        """
        pass