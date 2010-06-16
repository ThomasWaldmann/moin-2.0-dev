# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - stuff left over from removed Package Installer

    @copyright: 2005 MoinMoin:AlexanderSchremmer,
                2007-2009 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

# Parsing and (un)quoting for script files
def packLine(items, separator="|"):
    """ Packs a list of items into a string that is separated by `separator`. """
    return '|'.join([item.replace('\\', '\\\\').replace(separator, '\\' + separator) for item in items])

def unpackLine(string, separator="|"):
    """ Unpacks a string that was packed by packLine. """
    result = []
    token = None
    escaped = False
    for char in string:
        if token is None:
            token = ""
        if escaped and char in ('\\', separator):
            token += char
            escaped = False
            continue
        escaped = (char == '\\')
        if escaped:
            continue
        if char == separator:
            result.append(token)
            token = ""
        else:
            token += char
    if token is not None:
        result.append(token)
    return result

