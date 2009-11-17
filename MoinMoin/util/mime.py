"""
MoinMoin - MIME helpers

@copyright: 2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""


class Type(object):
    def __init__(self, _type=None, type=None, subtype=None, parameters=None):
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
        - the parameters are a subset of the others.
        """
        if isinstance(other, Type):
            if self.type and self.type != other.type: return False
            if self.subtype and self.subtype != other.subtype: return False
            self_set = set(self.parameters.iteritems())
            other_set = set(other.parameters.iteritems())
            return self_set <= other_set

        raise ValueError


# Own types, application type
type_moin_document = Type(type='application', subtype='x.moin.document')

# Own types, text type
type_moin_creole = Type(type='text', subtype='x.moin.creole')
type_moin_wiki = Type(type='text', subtype='x.moin.wiki')
