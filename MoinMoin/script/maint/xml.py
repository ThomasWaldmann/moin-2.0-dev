# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - XML (un)serialization of storage contents.

    Using --save you can serialize your storage contents to an xml file.
    Using --load you can load such a file into your storage.

    Note that before unserializing stuff, you should first create an
    appropriate namespace_mapping in your wiki configuration so that the
    items get written to the backend where you want them.

    @copyright: 2009 MoinMoin:ChristopherDenter,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import sys

from MoinMoin.script import MoinScript, fatal
from MoinMoin.wsgiapp import init_unprotected_backends

from MoinMoin.storage.serialization import unserialize, serialize


class PluginScript(MoinScript):
    """XML Load/Save Script"""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-s", "--save", dest="save", action="store_true",
            help="Save (serialize) storage contents to a xml file."
        )
        self.parser.add_option(
            "-l", "--load", dest="load", action="store_true",
            help="Load (unserialize) storage contents from a xml file."
        )
        self.parser.add_option(
            "-f", "--file", dest="xml_file", action="store", type="string",
            help="Filename of xml file to use [Default: use stdin/stdout]."
        )

    def mainloop(self):
        load = self.options.load
        save = self.options.save
        xml_file = self.options.xml_file
        if load == save: # either both True or both False
            fatal("You need to give either --load or --save!")
        if not xml_file:
            if load:
                xml_file = sys.stdin
            elif save:
                xml_file = sys.stdout

        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        storage = request.unprotected_storage

        if load:
            unserialize(storage, xml_file)
        elif save:
            serialize(storage, xml_file)

