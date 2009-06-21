"""
MoinMoin - Arguments support for wiki formats

@copyright: 2009 MoinMoin:BastianBlank
@license: GNU GPL, see COPYING for details.
"""

from __future__ import absolute_import

import re

from ._args import Arguments

_parse_rules = r'''
(?:
    (\w+)
    =
)?
(?:
    (\w+)
    |
    "
    (.*?)
    (?<!\\)"
    |
    '
    (.*?)
    (?<!\\)'
)
'''
_parse_re = re.compile(_parse_rules, re.X)

def parse(input):
    ret = Arguments()

    for match in _parse_re.finditer(input):
        key = match.group(1)
        value = (match.group(2) or match.group(3) or match.group(4)).decode('unicode-escape')

        if key:
            ret.keyword[key] = value
        else:
            ret.positional.append(value)

    return ret

_unparse_rules = r'''^\w+$'''
_unparse_re = re.compile(_unparse_rules, re.X)

def unparse(args):
    ret = []

    for value in args.positional:
        if not _unparse_re.match(value):
            value = u'"' + value.encode('unicode-escape') + u'"'
        ret.append(value)

    keywords = args.keyword.items()
    keywords.sort(key=lambda a: a[0])
    for key, value in keywords:
        if not _unparse_re.match(key):
            raise RuntimeError(u"Can't argue with finger")
        if not _unparse_re.match(value):
            value = u'"' + value.encode('unicode-escape') + u'"'
        ret.append(key + u'=' + value)

    return u' '.join(ret)
