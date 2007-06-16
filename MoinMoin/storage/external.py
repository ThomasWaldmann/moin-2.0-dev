"""
    MoinMoin external interfaces

    @copyright: 2007 MoinMoin:HeinrichWendel
    @license: GNU GPL, see COPYING for details.
"""

import UserDict

from MoinMoin.storage.error import ItemNotExistsError, RevisionNotExistsError

class ItemCollection(UserDict.DictMixin, object):
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
        
        self.__items = None

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
            return Item(name, self.backend, self.userobj)
        else:
            raise ItemNotExistsError("No such item %r." % name)

    def __delitem__(self, name):
        """
        Deletes an Item.
        """
        self.backend.remove_item(name)
        self.__items = None

    def keys(self, filters=None):
        """
        Returns a list of all item names. With filters you can add
        filtering stuff which is described more detailed in
        StorageBackend.list_items(...).
        """
        if filters is None:
            return self.items
        else:
            return self.backend.list_items(filters)

    def new_item(self, name):
        """
        Returns a new Item with the given name.
        """
        self.backend.create_item(name)
        self.__items = None
        return Item(name, self.backend, self.userobj)

    def get_items(self):
        """
        Lazy load items.
        """
        if self.__items is None:
            self.__items = self.backend.list_items()
        return self.__items

    items = property(get_items)


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
        self.name = name
        self.backend = backend
        self.userobj = userobj
        
        self.__metadata = None
        
        self.__revisions = None
        self.__current = None
        self.__revision_objects = dict()
    
    def __contains__(self, revno):
        """
        Checks if a Revision with the given revision-number exists.
        """
        return self.backend.has_revision(self.name, revno)

    def __getitem__(self, revno):
        """
        Returns the revision specified by a revision-number (LazyLoaded). 
        """
        try:
            return self.__revision_objects[revno]
        except KeyError:
            if self.backend.has_revision(self.name, revno):
                self.__revision_objects[revno] = Revision(revno, self)
                return self.__revision_objects[revno]
            else:
                raise RevisionNotExistsError("Revision %r of item %r does not exist." % (revno, self.name))

    def __delitem__(self, revno):
        """
        Deletes the Revision specified by the given revision-number.
        """
        self.backend.remove_revision(self.name, revno)
        try:
            del self.__revision_objects[revno]
        except KeyError:
            pass

    def keys(self):
        """
        Returns a sorted (highest first) list of all real revision-numbers.
        """
        return self.revisions

    def new_revision(self, revno=0):
        """
        Creates and returns a new revision with the given revision-number.
        If the revision number is None the next possible number will be used. 
        """
        self.backend.create_revision(self.name, revno)
        self.__revisions = None
    
    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self.__metadata is None:
            self.__metadata = Revision(-1, self).metadata
        return self.__metadata
    
    metadata = property(get_metadata)
    
    def get_revisions(self):
        """
        Lazy load the revisions.
        """
        if self.__revisions is None:
            self.__revisions = self.backend.list_revisions(self.name)
        return self.__revisions
    
    revisions = property(get_revisions)
    
    def get_current(self):
        """
        Lazy load the current revision no.
        """
        if self.__current is None:
            self.__current = self.backend.current_revision(self.name)
        return self.__current
    
    current = property(get_current)
    

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
        self.revno = revno
        self.item = item
        
        self.__data = None
        self.__metadata  = None
    
    def get_metadata(self):
        """
        Lazy load metadata.
        """
        if self.__metadata is None:
            self.__metadata = Metadata(self)
        return self.__metadata
    
    metadata = property(get_metadata)
    
    def get_data(self):
        """
        Lazy load metadata.
        """
        if self.__data is None:
            self.__data = self.item.backend.get_data_backend(self.item.name, self.revno)
        return self.__data
    
    data = property(get_data)
            

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
        self.metadata = revision.item.backend.get_metadata(self.revision.item.name, self.revision.revno)
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
            
        self.metadata[key] = value

    def __delitem__(self, key):
        """
        Deletes a value.
        """
        if key in self.changed and self.changed[key] == "add":
            del self.changed[key]
        else:
            self.changed[key] = 'remove'
        
        del self.metadata[key]

    def keys(self):
        """
        Return sa list of all metadata keys.
        """
        return self.metadata.keys()
            
    def save(self):
        """
        Saves the metadata.
        """
        add = {}
        remove = []
        for key, value in self.changed.iteritems():
            if value == "add" or value == "set":
                add[key] = self.metadata[key]
            elif value == "remove":
                remove.append(key)
        if add:
            self.revision.item.backend.set_metadata(self.revision.item.name, self.revision.revno, add)
        if remove:
            self.revision.item.backend.remove_metadata(self.revision.item.name, self.revision.renvo, remove)
