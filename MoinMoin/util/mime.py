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

        self.type, self.subtype = parts[0].strip().split('/', 1)

        for param in parts[1:]:
            key, value = param.strip().split('=', 1)
            # remove quotes
            if value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            self.parameters[key.lower()] = value
