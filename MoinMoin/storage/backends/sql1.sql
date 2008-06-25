DROP TABLE locks;
DROP TABLE items;
DROP TABLE itemmeta;
DROP TABLE revisions;
DROP TABLE revmeta;
DROP TABLE revdata;

-- locks
CREATE TABLE locks (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    lockname UNIQUE);

-- table of items
CREATE TABLE items (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    itemname UNIQUE);

-- metadata key/value pairs for item metadata
CREATE TABLE itemmeta(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                      itemid INTEGER NOT NULL,
                      metakey NOT NULL,
                      metavalue);

-- table of revisions
CREATE TABLE revisions (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        itemid INTEGER NOT NULL,
                        lastupdate INTEGER NOT NULL,
                        revno INTEGER NOT NULL);

-- actual data for a revision
CREATE TABLE revmeta(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                     revid INTEGER,
                     metakey NOT NULL,
                     metavalue);
CREATE TABLE revdata(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                     revid INTEGER,
                     data);
