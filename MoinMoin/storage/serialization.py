# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - XML serialization support

    This module contains mixin classes to support xml serialization / unserialization.
    It uses the sax xml parser / xml generator from the stdlib.

    Applications:
    * wiki backup / restore
    * wiki item packages

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import base64

from xml.sax import parse as xml_parse
from xml.sax.saxutils import XMLGenerator
from xml.sax.handler import ContentHandler

class MoinContentHandler(ContentHandler):
    """
    ContentHandler that handles sax parse events and feeds them into the
    unserializer stack.
    """
    def __init__(self, handler):
        ContentHandler.__init__(self)
        self.unserializer = handler.make_unserializer()

    def unserialize(self, *args):
        try:
            self.unserializer.send(args)
        except StopIteration:
            pass

    def startElement(self, name, attrs):
        self.unserialize('startElement', name, attrs)

    def endElement(self, name):
        self.unserialize('endElement', name)

    def characters(self, data):
        self.unserialize('characters', data)


class Serializable(object):
    element_name = None # override with xml element name
    element_attrs = None # override with xml element attributes

    @classmethod
    def _log(cls, text):
        logging.warning(text)

    # serialization support:
    def serialize(self, xmlfile):
        # works for simple elements, please override for complex elements
        xg = XMLGenerator(xmlfile, 'utf-8')
        xg.startElement(self.element_name, self.element_attrs or {})
        self.serialize_value(xmlfile)
        xg.endElement(self.element_name)

    def serialize_value(self, xmlfile):
        # works for simple values, please override for complex values
        xg = XMLGenerator(xmlfile, 'utf-8')
        xg.characters(str(self.value))

    # unserialization support:
    def get_unserializer(self, name, attrs):
        """
        returns a unserializer instance for child element <name>, usually
        a instance of some other class derived from UnserializerBase
        """
        raise NotImplementedError()

    def startElement(self, attrs):
        """ called when this element is opened """

    def characters(self, data):
        """ called for character data within this element """

    def endElement(self):
        """ called when this element is closed """

    def noHandler(self, name):
        self._log("No unserializer for element name: %s, not handled by %s" % (
                  name, self.__class__))

    def unexpectedEnd(self, name):
        self._log("Unexpected end element: %s (expected: %s)" % (
                  name, self.element_name))

    def make_unserializer(self):
        """
        convenience wrapper that creates the unserializing generator and
        automatically does the first "nop" generator call.
        """
        gen = self._unserialize()
        gen.next()
        return gen

    def _unserialize(self):
        """
        Generator that gets fed with event data from the sax parser, e.g.:
            ('startElement', name, attrs)
            ('endElement', name)
            ('characters', data)

        It only handles stuff for name == self.element_name, everything else gets
        delegated to a lower level generator, that is found by self.get_unserializer().
        """
        while True:
            d = yield
            fn = d[0]
            if fn == 'startElement':
                name, attrs = d[1:]
                if name == self.element_name:
                    self.startElement(attrs)
                else:
                    unserializer_instance = self.get_unserializer(name, attrs)
                    if unserializer_instance is not None:
                        unserializer = unserializer_instance.make_unserializer()
                        try:
                            while True:
                                d = yield unserializer.send(d)
                        except StopIteration:
                            pass
                    else:
                        self.noHandler(name)

            elif fn == 'endElement':
                name = d[1]
                if name == self.element_name:
                    self.endElement()
                    return # end generator
                else:
                    self.unexpectedEnd(name)

            elif fn == 'characters':
                self.characters(d[1])

    def unserialize(self, xmlfile):
        xml_parse(xmlfile, MoinContentHandler(self))


def create_value_object(v):
    if isinstance(v, tuple):
        return TupleValue(v)
    elif isinstance(v, unicode):
        return UnicodeValue(v)
    elif isinstance(v, str):
        return StrValue(v)
    elif isinstance(v, bool):
        return BoolValue(v)
    elif isinstance(v, int):
        return IntValue(v)
    elif isinstance(v, float):
        return FloatValue(v)
    elif isinstance(v, complex):
        return ComplexValue(v)
    else:
        raise TypeError("unsupported type %r", type(v))


class Value(Serializable):
    element_name = None # override in child class

    def __init__(self, value=None, attrs=None, setter_fn=None):
        self.value = value
        self.element_attrs = attrs
        self.setter_fn = setter_fn
        self.data = u''

    def characters(self, data):
        self.data += data

    def endElement(self):
        value = self.element_decode(self.data)
        self.setter_fn(value)

    def serialize_value(self, xmlfile):
        xg = XMLGenerator(xmlfile, 'utf-8')
        xg.characters(self.element_encode(self.value))

    def element_decode(self, x):
        return x # override in child class

    def element_encode(self, x):
        return x # override in child class

class UnicodeValue(Value):
    element_name = 'unicode'

class StrValue(Value):
    element_name = 'str'

    def element_decode(self, x):
        return x.encode('utf-8')

    def element_encode(self, x):
        return x.decode('utf-8')

class IntValue(Value):
    element_name = 'int'

    def element_decode(self, x):
        return int(x)

    def element_encode(self, x):
        return str(x)

class FloatValue(Value):
    element_name = 'float'

    def element_decode(self, x):
        return float(x)

    def element_encode(self, x):
        return str(x)

class ComplexValue(Value):
    element_name = 'complex'

    def element_decode(self, x):
        return complex(x)

    def element_encode(self, x):
        return str(x)

class BoolValue(Value):
    element_name = 'bool'

    def element_decode(self, x):
        if x == 'False':
            return False
        if x == 'True':
            return True
        raise ValueError("boolean serialization must be 'True' or 'False', no %r" % x)

    def element_encode(self, x):
        return str(x)

class TupleValue(Serializable):
    element_name = 'tuple'

    def __init__(self, value=None, attrs=None, setter_fn=None):
        self.value = value
        self.element_attrs = attrs
        self._result_fn = setter_fn
        self._data = []

    def get_unserializer(self, name, attrs):
        mapping = {
            'str': StrValue,
            'unicode': UnicodeValue,
            'bool': BoolValue,
            'int': IntValue,
            'float': FloatValue,
            'complex': ComplexValue,
            'tuple': TupleValue,
        }
        cls = mapping.get(name)
        if cls:
            return cls(attrs=attrs, setter_fn=self.setter_fn)
        else:
            raise TypeError("unsupported element: %s", name)

    def setter_fn(self, value):
        self._data.append(value)

    def endElement(self):
        value = tuple(self._data)
        self._result_fn(value)

    def serialize_value(self, xmlfile):
        for e in self.value:
            e = create_value_object(e)
            e.serialize(xmlfile)


class Entry(TupleValue):
    element_name = 'entry'

    def __init__(self, key=None, value=None, attrs=None, rev_or_item=None):
        if key == 'acl': # XXX avoid acl problems for now XXX
            key = 'noacl'
        self.key = key
        if value is not None:
            value = (value, ) # use a 1-tuple
        if attrs is None and key is not None:
            attrs = dict(key=key)
        self.target = rev_or_item
        TupleValue.__init__(self, value=value, attrs=attrs, setter_fn=self.result_fn)

    def result_fn(self, value):
        assert len(value) == 1 # entry is like a 1-tuple
        key = self.element_attrs.get('key')
        self.target[key] = value[0]


class Meta(Serializable):
    element_name = 'meta'

    def __init__(self, attrs, rev_or_item):
        self.element_attrs = attrs
        self.target = rev_or_item

    def get_unserializer(self, name, attrs):
        if name == 'entry':
            return Entry(attrs=attrs, rev_or_item=self.target)

    def serialize_value(self, xmlfile):
        for k in self.target.keys():
            e = Entry(k, self.target[k])
            e.serialize(xmlfile)


class ItemMeta(Meta):
    def startElement(self, attrs):
        self.target.change_metadata()

    def endElement(self):
        self.target.publish_metadata()


class Chunk(Serializable):
    element_name = 'chunk'
    size = 4096

    def __init__(self, value=None, attrs=None, setter_fn=None):
        self.value = value
        self.element_attrs = attrs
        coding = attrs and attrs.get('coding')
        coding = coding or 'base64'
        self.coding = coding
        self.setter_fn = setter_fn
        self.data = ''

    def characters(self, data):
        self.data += data

    def endElement(self):
        if self.coding == 'base64':
            data = base64.b64decode(self.data)
            self.setter_fn(data)

    def serialize_value(self, xmlfile):
        xg = XMLGenerator(xmlfile, 'utf-8')
        if self.coding == 'base64':
            data = base64.b64encode(self.value)
            xg.characters(data)


class Data(Serializable):
    element_name = 'data'

    def __init__(self, attrs, read_fn=None, write_fn=None):
        if 'coding' not in attrs:
            attrs['coding'] = 'base64'
        self.element_attrs = attrs
        self.read_fn = read_fn
        self.write_fn = write_fn
        self.coding = attrs.get('coding')

    def get_unserializer(self, name, attrs):
        if name == 'chunk':
            attrs = dict(attrs)
            if self.coding and 'coding' not in attrs:
                attrs['coding'] = self.coding
            return Chunk(attrs=attrs, setter_fn=self.result_fn)

    def result_fn(self, data):
        self.write_fn(data)

    def serialize_value(self, xmlfile):
        while True:
            data = self.read_fn(Chunk.size)
            if not data:
                break
            ch = Chunk(data)
            ch.serialize(xmlfile)

