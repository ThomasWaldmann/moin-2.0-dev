# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - simple fixed-length record logging support

    @copyright: 2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

SEEK_SET, SEEK_CUR, SEEK_END = 0, 1, 2

class FixedRecordLogFile(object):
    """Simple fixed-length record logfile storage
       * we only append records at the end of the file
       * a log object is either read XOR write
       * each record is <record_size> length
    """

    def __init__(self, file_name, record_size, field_sizes=None):
        """Initialize a log object

           @param file_name: complete path/file name to the log
           @param record_size: used as (smallest possible) block size for
                               reading and also for checking that the total
                               sum of the field sizes matches the record_size.
                               Maybe you want to use some 2^N value for this.
           @param field_sizes: optional, see set_layout()
                               if you don't use it, only lowlevel functions
                               will work.
        """
        self.file_name = file_name
        self.record_size = record_size
        self.log_file = None
        if field_sizes:
            self.set_layout(field_sizes)

    # lowlevel stuff

    def open(self, mode=None, reverse=True):
        """Open the log file

           @param mode: must be 'rb' (reading) or 'ab' (writing/appending)
           @param reverse: if True (default) begin reading from the last record
                           and proceed in reverse direction towards beginning of
                           the file. Ignored for writing.
        """
        assert mode in ('rb', 'ab')
        if self.log_file is None:
            self.file_mode = mode
            self.log_file = open(self.file_name, self.file_mode) # buffer size makes no speed difference
            if mode == 'ab':
                reverse = False
            if reverse:
                self.increment_record = -1
                self.current_record = self.seek_record(-1, SEEK_END)
            else:
                self.increment_record = 1
                self.current_record = 0
        else:
            raise Exception("Trying to reopen already open log file")

    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def tell_record(self):
        """Return current position in the log file,
           units are records (not bytes)
        """
        pos = self.log_file.tell()
        assert pos % self.record.size == 0
        record = pos / self.record_size
        return record

    def seek_record(self, record_offset, whence=SEEK_SET):
        """Seeks, using records as units (not bytes).

           @return: current, absolute record_number
        """
        self.log_file.seek(record_offset * self.record_size, whence)
        pos = self.log_file.tell() # better check where we got
        if whence == SEEK_END:
            too_far = pos % self.record_size
            if too_far:
                # maybe someone was writing while we did the seek and we
                # didn't seek to a correct record offset because of that.
                self.log_file.seek(-too_far, whence=SEEK_CUR) # fix it
                pos -= too_far
        return pos / self.record_size

    def read_record(self):
        """Read one record (and make sure we got it completely)."""
        data = self.log_file.read(self.record_size)
        if len(data) != self.record_size:
            raise StopIteration
        return data

    def write_record(self, data):
        """Write one record (and make sure data is of record_size),
           flush it to disk.
        """
        assert len(data) == self.record_size
        self.log_file.write(data)
        self.log_file.flush()

    # highlevel stuff

    def set_layout(self, field_sizes):
        """Set record layout (usually called by __init__).

           This MUST be called (e.g. by giving the field_sizes param to the
           constructor) or no highlevel stuff will be possible.

           @param field_sizes: a list of tuples (fieldname, fieldsize) -
                               fields will be stored in that order and
                               the sum of field sizes must match record_size.
        """
        total_size = 0
        self.field_names = []
        self.field_lengths = {}
        for name, field_size in field_sizes:
            total_size += field_size
            self.field_names.append(name)
            self.field_lengths[name] = field_size
        assert self.record_size == total_size

    def make_record(self, **field_values):
        """Make a fixed size record from field_values

           @param field_values: name=value keywords - the names must match
                                those set with set_layout, the values must
                                be str and will be padded with blanks at the
                                right side.
        """
        if not self.field_names:
            raise Exception("You must first call set_layout() or give the layout to the constructor.")
        fields = []
        for name in self.field_names:
            field_length = self.field_lengths[name]
            format = '%-0' + str(field_length) + 's'
            field = format % field_values[name]
            assert len(field) == field_length
            fields.append(field)
        record = ''.join(fields)
        return record

    def parse_record(self, record):
        """Parse a fixed size record.

           @return: a name=value dict, the names as given in set_layout(),
                    values will get stripped at the right side and will be
                    returned as str.
        """
        if not self.field_names:
            raise Exception("You must first call set_layout() or give the layout to the constructor.")
        result = {}
        index = 0
        for name in self.field_names:
            length = self.field_lengths[name]
            result[name] = record[index:index+length].rstrip(' ')
            index += length
        return result

    def read(self):
        """Read one log entry.

           @return: see parse_record() return value
        """
        data = self.read_record()
        data = self.parse_record(data)
        return data

    def write(self, **field_values):
        """Write a new log entry.

           @param field_values: see make_record() param
        """
        record = self.make_record(**field_values)
        self.write_record(record)

    # make self an iterator
    def __iter__(self):
        return self

    def next(self):
        try:
            self.seek_record(self.current_record, SEEK_SET)
            data = self.read()
            self.current_record += self.increment_record
            return data
        except IOError, err:
            raise StopIteration

    # also make some generators
    def traverse(self, reverse):
        try:
            self.open('rb', reverse)
        except IOError, err:
            raise StopIteration
        try:
            while True:
                yield self.next()
        except StopIteration:
            self.close()
            raise

    def forward(self):
        for data in self.traverse(reverse=False):
            yield data

    def reverse(self):
        for data in self.traverse(reverse=True):
            yield data


# testing
if __name__ == '__main__':
    import time

    log = FixedRecordLogFile('test.log',
                             1024, [('timestamp', 8), ('revno', 8), ('itemname', 8), ('bloat', 998), ('magic', 2)])
    # trick: using crlf as magic makes file editable

    #print list(log.forward()) # try this with no log
    print "writing a small log ..."
    log.open('ab')
    for i in range(10):
        log.write(timestamp=str(i), revno=str(2*i), itemname=str(3*i), bloat='', magic='\r\n')
    log.close()

    print "reading forward (generator) ..."
    for data in log.forward():
        assert data['magic'] == '\r\n'
        int(data['timestamp'])
        int(data['revno'])
        int(data['itemname'])
        del data['bloat']
        #print repr(data)

    print "reading reverse (generator) ..."
    for data in log.reverse():
        assert data['magic'] == '\r\n'
        int(data['timestamp'])
        int(data['revno'])
        int(data['itemname'])
        del data['bloat']
        #print repr(data)

    print "making it bigger ..."
    t = time.time()
    log.open('ab')
    for i in xrange(100000):
        log.write(timestamp=str(i), revno=str(2*i), itemname=str(3*i), bloat='', magic='\r\n')
    log.close()
    print time.time() - t

    print "reading forward (generator) ..."
    t = time.time()
    for data in log.forward():
        assert data['magic'] == '\r\n'
        int(data['timestamp'])
        int(data['revno'])
        int(data['itemname'])
        #print repr(data)
    print time.time() - t

    print "reading reverse (generator) ..."
    t = time.time()
    for data in log.reverse():
        assert data['magic'] == '\r\n'
        int(data['timestamp'])
        int(data['revno'])
        int(data['itemname'])
        del data['bloat']
        #print repr(data)
    print time.time() - t

