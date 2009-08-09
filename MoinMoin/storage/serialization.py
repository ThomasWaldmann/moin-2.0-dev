# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - XML serialization support

    This module contains mixin classes to support xml serialization / unserialization.
    It uses the sax xml parser / xml generator from the stdlib.

    Applications include wiki backup/restore, wiki item packages, ...

    Examples
    --------

    a) serialize all items of a storage backend to a file:
    backend = ... (some storage backend)
    serialize(backend, "items.xml")

    b) unserialize all items from a file to a storage backend:
    backend = ... (some storage backend)
    unserialize(backend, "items.xml")

    c) serialize just some items:
    some_items = [u'FrontPage', u'HelpOnLinking', u'HelpOnMoinWikiSyntax', ]
    serialize(backend, 'some_items.xml', ItemNameList, some_items)

    @copyright: 2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import log
logging = log.getLogger(__name__)

import base64

from xml.sax import parse as xml_parse
from xml.sax.saxutils import XMLGenerator
from xml.sax.handler import ContentHandler

class MoinContentHandler(ContentHandler):
    """
    ContentHandler that handles sax parse events and feeds them into the
    unserializer stack.
    """
    def __init__(self, handler, context):
        ContentHandler.__init__(self)
        self.unserializer = handler.make_unserializer(context)

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


class XMLSelectiveGenerator(XMLGenerator):
    """
    Manage xml output writing (by XMLGenerator base class)
    and selection of output (by shall_serialize method)

    You are expected to subclass this class and overwrite the shall_serialize method.
    """
    def __init__(self, out, encoding='utf-8'):
        # note: we have utf-8 as default, base class has iso-8859-1
        if out is not None and not hasattr(out, 'write'):
            # None is OK (will become stdout by XMLGenerator.__init__)
            # file-like is also OK
            # for everything else (filename?), we try to open it first:
            out = open(out, 'w')
        XMLGenerator.__init__(self, out, encoding)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        # shall be called by serialization code before starting to write
        # the element to decide whether it shall be serialized.
        return True


class NLastRevs(XMLSelectiveGenerator):
    def __init__(self, out, nlast):
        self.nlast = nlast
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        if revno is None:
            return True
        else:
            return revno > current_revno - self.nlast


class ExceptNLastRevs(XMLSelectiveGenerator):
    def __init__(self, out, nlast):
        self.nlast = nlast
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        if revno is None:
            return True
        else:
            return revno <= current_revno - self.nlast


class SinceTime(XMLSelectiveGenerator):
    def __init__(self, out, ts):
        self.ts = ts
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        if rev is None:
            return True
        else:
            return rev.timestamp >= self.ts


class BeforeTime(XMLSelectiveGenerator):
    def __init__(self, out, ts):
        self.ts = ts
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        if rev is None:
            return True
        else:
            return rev.timestamp < self.ts


class ItemNameList(XMLSelectiveGenerator):
    def __init__(self, out, item_names):
        self.item_names = item_names
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        return item is not None and item.name in self.item_names


class TermMatch(XMLSelectiveGenerator):
    def __init__(self, out, term):
        self.term = term  # see MoinMoin.search.term
        XMLSelectiveGenerator.__init__(self, out)

    def shall_serialize(self, item=None, rev=None,
                        revno=None, current_revno=None):
        if item is not None:
            self.term.prepare()
            return self.term.evaluate(item)
        return False


def serialize(obj, xmlfile, xmlgen_cls=XMLSelectiveGenerator, *args, **kwargs):
    """
    Serialize <obj> to <xmlfile>.

    The default value of <xmlgen_cls> will just serialize everything. Alternatively,
    use some of XMLSelectiveGenerator child classes to do selective serialization,
    e.g. of just a list of items or just of items that match some search term.

    @arg obj: object to serialize (must mix in Serializable)
    @arg xmlfile: output file (file-like or filename)
    @arg xmlgen_cls: XMLSelectiveGenerator (sub)class instance (all args/kwargs
                     given after this will be given to xmlgen_cls.__init__()
    """
    xg = xmlgen_cls(xmlfile, *args, **kwargs)
    obj.serialize(xg)


class XMLUnserializationContext(object):
    """
    Provides context information for xml unserialization.
    """
    def __init__(self, xmlfile, encoding='utf-8', revno_mode='next'):
        if xmlfile is not None and not hasattr(xmlfile, 'read'):
            # for everything not file-like (filename?), we try to open it first:
            xmlfile = open(xmlfile, 'r')
        self.xmlfile = xmlfile
        self.revno_mode = revno_mode


def unserialize(obj, xmlfile, context_cls=XMLUnserializationContext, *args, **kwargs):
    """
    Unserialize <xmlfile> to <obj>.

    @arg obj: object to write unserialized data to (must mix in Serializable)
    @arg xmlfile: input file (file-like or filename)
    """
    context = context_cls(xmlfile, *args, **kwargs)
    obj.unserialize(context)


class Serializable(object):
    element_name = None # override with xml element name
    element_attrs = None # override with xml element attributes

    @classmethod
    def _log(cls, text):
        logging.warning(text)

    # serialization support:
    def serialize(self, xmlgen):
        # works for simple elements, please override for complex elements
        # xmlgen.shall_serialize should be called by elements supporting selection
        xmlgen.startElement(self.element_name, self.element_attrs or {})
        self.serialize_value(xmlgen)
        xmlgen.endElement(self.element_name)
        xmlgen.ignorableWhitespace('\n')

    def serialize_value(self, xmlgen):
        # works for simple values, please override for complex values
        xmlgen.characters(str(self.value))

    # unserialization support:
    def get_unserializer(self, context, name, attrs):
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

    def make_unserializer(self, context):
        """
        convenience wrapper that creates the unserializing generator and
        automatically does the first "nop" generator call.
        """
        gen = self._unserialize(context)
        gen.next()
        return gen

    def _unserialize(self, context):
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
                    unserializer_instance = self.get_unserializer(context, name, attrs)
                    if unserializer_instance is not None:
                        unserializer = unserializer_instance.make_unserializer(context)
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

    def unserialize(self, context):
        xml_parse(context.xmlfile, MoinContentHandler(self, context))


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
    elif isinstance(v, long):
        return LongValue(v)
    elif isinstance(v, float):
        return FloatValue(v)
    elif isinstance(v, complex):
        return ComplexValue(v)
    else:
        raise TypeError("unsupported type %r (value: %r)" % (type(v), v))


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

    def serialize_value(self, xmlgen):
        xmlgen.characters(self.element_encode(self.value))

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

class LongValue(Value):
    element_name = 'long'

    def element_decode(self, x):
        return long(x)

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

    def get_unserializer(self, context, name, attrs):
        mapping = {
            'str': StrValue,
            'unicode': UnicodeValue,
            'bool': BoolValue,
            'int': IntValue,
            'long': LongValue,
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

    def serialize_value(self, xmlgen):
        for e in self.value:
            e = create_value_object(e)
            e.serialize(xmlgen)


class Entry(TupleValue):
    element_name = 'entry'

    def __init__(self, key=None, value=None, attrs=None, rev_or_item=None):
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

    def get_unserializer(self, context, name, attrs):
        if name == 'entry':
            return Entry(attrs=attrs, rev_or_item=self.target)

    def serialize_value(self, xmlgen):
        for k in self.target.keys():
            e = Entry(k, self.target[k])
            e.serialize(xmlgen)


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

    def serialize_value(self, xmlgen):
        if self.coding == 'base64':
            data = base64.b64encode(self.value)
            xmlgen.characters(data)


class Data(Serializable):
    element_name = 'data'

    def __init__(self, attrs, read_fn=None, write_fn=None):
        if not attrs.has_key('coding'):
            attrs['coding'] = 'base64'
        self.element_attrs = attrs
        self.read_fn = read_fn
        self.write_fn = write_fn
        self.coding = attrs.get('coding')

    def get_unserializer(self, context, name, attrs):
        if name == 'chunk':
            attrs = dict(attrs)
            if self.coding and 'coding' not in attrs:
                attrs['coding'] = self.coding
            return Chunk(attrs=attrs, setter_fn=self.result_fn)

    def result_fn(self, data):
        self.write_fn(data)

    def serialize_value(self, xmlgen):
        while True:
            data = self.read_fn(Chunk.size)
            if not data:
                break
            ch = Chunk(data)
            ch.serialize(xmlgen)

