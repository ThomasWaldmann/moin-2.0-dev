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


class Item(UserDict.DictMixin, object):
    """
    The Item class represents a StorageItem. This Item has a name and revisions.
    An Item can be anything MoinMoin must save, e.g. Pages, Attachements or
    Users. A list of revision-numbers is only loaded on access. Via Item[0]
    you can access the last revision. The specified Revision is only loaded on
    access as well. On every access the ACLs will be checked.
    """
    
    def __init__(self, name, backend, userobj):
        """
        Initializes the Item with the required parameters.
        """
        self.metadata = Metadata(Revision(-1, self))
        self.name = name
        self.backend = backend
        self.userobj = userobj
        
        self.new = False
        self.changed = []
        
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
        if not self.revisions[revno]:
            self.revisions[revno] = Revision(revno, self)
        return self.revisions[revno]

    def __delitem__(self, revno):
        """
        Deletes the Revision specified by the given revision-number.
        """
        del self.revisions[revno]
        
        self.changed.append(['remove', revno])

    def keys(self):
        """
        Returns a sorted (highest first) list of all real revision-numbers.
        """
        return self.revisions.keys()

    def new_revision(self, revno=None):
        """
        Creates and returns a new revision with the given revision-number.
        If the revision number is None the next possible number will be used. 
        """
        if not revno:
            revno = self.current + 1
        elif revno in self.revisions:
            raise StorageError("Revision %s already exists." % revno)
        
        self.revisions[revno] = None
        
        self.changed.append(['add', revno])
    
    def get_revisions(self):
        """
        Lazy load the revisions.
        """
        if not self.__revisions:
            self.__revisions = {}
            revs = self.backend.list_revisions(self.name)
            for revno in revs:
                self.__revisions[revno] = None
        return self.__revisions
    
    revisions = property(get_revisions)
    
    def get_current(self):
        """
        Lazy load the current revision nr.
        
        TODO: optimize this
        """
        if not self.__current:
            revs = self.backend.list_revisions(self.name)
            self.__current = revs[-1]
        return self.__current
    
    current = property(get_current)
            
    def save(self):
        """
        Saves the whole item. It checks if the Item must be created, which Revision was
        added/removed, if the data was changed and what metadata keys were changed and
        saves the changes then.
        """
        if self.new:
            self.backend.create_item(self.name)
            
        for item in self.changed:
            if item[0] == "add":
                self.backend.create_revision(self.name, item[1])
            elif item[0] == "remove":
                self.backend.remove_revision(self.name, item[1])
            elif item[0] == "change":
                add = {}
                remove = []
                for key, value in item[1].metadata.changed.iteritems():
                    if value == "add" or value == "set":
                        add[key] = item[1].metadata[key]
                    elif value == "remove":
                        remove.append(key)
                if add:
                    self.backend.set_metadata(self.name, item[1].revno, add)
                if remove:
                    self.backend.remove_metadata(self.name, item[1].revno, remove)


class Revision(object):
    """
    A Revision contains the data and metadata for one revision of the Item. The
    Metadata and Data classes will be created when the revision is created, but
    they take care that their content is loaded lazily. On every access the ACLs
    will be checked.
    """

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


class Metadata(UserDict.DictMixin, object):
    """ 
    The metadata of an Item. Access will be via a dict like interface.
    All metadata will be loaded on the first access to one key.
    On every access the ACLs will be checked.
    """

    def __init__(self, revision):
        """"
        Initializes the metadata object with the required parameters.
        """
        self.revision = revision
        self.__metadata = None
        self.changed = {}

    def __contains__(self, key):
        """
        Checks if a key exists.
        """
        return key in self.metadata

    def __getitem__(self, key):
        """
        Returns a specified value.
        """
        return self.metadata[key]

    def __setitem__(self, key, value):
        """
        Adds a value.
        """
        if not key in self.metadata:
            self.changed[key] = 'add'
        else:
            self.changed[key] = 'set'  
        
        if not ['change', self.revision] in self.revision.item.changed:
            self.revision.item.changed.append(['change', self.revision])
            
        self.metadata[key] = value

    def __delitem__(self, key):
        """
        Deletes a value.
        """
        if key in self.changed and self.changed[key] == "add":
            del self.changed[key]
        else:
            self.changed[key] = 'remove'
        
        if not ['change', self.revision] in self.revision.item.changed:
            self.revision.item.changed.append(['change', self.revision])
        
        del self.metadata[key]

    def keys(self):
        """
        Return sa list of all metadata keys.
        """
        return self.metadata.keys()
    
    def get_metadata(self):
        """
        Lazy load the metadata.
        """
        if not self.__metadata:
            self.__metadata = self.revision.item.backend.get_metadata(self.revision.item.name, self.revision.revno)
        return self.__metadata
    
    metadata = property(get_metadata)


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
    