"""
MoinMoin - MIME helpers

@copyright: 2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""


class Type(object):
    """
    @ivar type: Type part
    @type type: unicode
    @ivar subtype: Subtype part
    @type subtype: unicode
    @ivar parameters: Parameters part
    @type parameters: dict
    """

    def __init__(self, _type=None, type=None, subtype=None, parameters=None):
        """
        @param _type: Textual type, is split into the parts
        @keyword type: Type part
        @keyword subtype: Subtype part
        @keyword parameters: Parameters part
        """
        self.type = self.subtype = None
        self.parameters = {}

        if _type:
            self._parse(_type)

        if type is not None:
            self.type = type
        if subtype is not None:
            self.subtype = subtype
        if parameters is not None:
            self.parameters.update(parameters)

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.__eq__(self.__class__(other))

        if isinstance(other, Type):
            if self.type != other.type: return False
            if self.subtype != other.subtype: return False
            if self.parameters != other.parameters: return False
            return True

        return NotImplemented

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is NotImplemented:
            return ret
        return not ret

    def __repr__(self):
        return '<%s object: type: %r; subtype: %r; parameters: %r>' % (
                self.__class__.__name__,
                self.type,
                self.subtype,
                self.parameters,
                )

    def __unicode__(self):
        ret = [u'%s/%s' % (self.type, self.subtype)]

        parameters = self.parameters.items()
        parameters.sort()
        for item in parameters:
            # TODO: check if quoting is necessary
            ret.append(u'%s="%s"' % item)

        return u';'.join(ret)

    def _parse(self, type):
        parts = type.split(';')

        self.type, self.subtype = parts[0].strip().lower().split('/', 1)

        for param in parts[1:]:
            key, value = param.strip().split('=', 1)
            # remove quotes
            if value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            self.parameters[key.lower()] = value

    def issupertype(self, other):
        """
        Check if this object is a super type of the other

        A super type is defined as
        - the other type matches this (possibly wildcard) type,
        - the other subtype matches this (possibly wildcard) subtype and
        - the other parameters are a supperset of this one.
        """
        if isinstance(other, Type):
            if self.type and self.type != other.type: return False
            if self.subtype and self.subtype != other.subtype: return False
            self_params = set(self.parameters.iteritems())
            other_params = set(other.parameters.iteritems())
            return self_params <= other_params

        raise ValueError


# Own types, application type
type_moin_document = Type(type='application', subtype='x.moin.document')

# Own types, text type
type_moin_creole = Type(type='text', subtype='x.moin.creole')
type_moin_wiki = Type(type='text', subtype='x.moin.wiki')
