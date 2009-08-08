# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Clone Backend From/To Serialized Data

    If you have a serialized xml version of some backend,
    you can invoke this script to pump the data into your
    storage backends.
    Analogously, if you have a backend you would like to
    serialize, you can use this script to get an xml file
    containing the entire data stored in the backend.

    @copyright: 2009 MoinMoin:ChristopherDenter
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.script import MoinScript, fatal
from MoinMoin.wsgiapp import init_unprotected_backends

from MoinMoin.storage.serialization import unserialize, serialize


class PluginScript(MoinScript):
    """XML Load/Save Script"""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-s", "--save", dest="save", action="store_true",
            help="Indicate whether you want to save all your backend data to the xml file specified."
        )
        self.parser.add_option(
            "-l", "--load", dest="load", action="store_true",
            help="Indicate whether you want to load all your backend data from the xml file specified."
        )
        self.parser.add_option(
            "-f", "--file", dest="xml_file", action="store", type="string",
            help="The xml file you want to load the data from/store the data to."
        )

    def mainloop(self):
        load = self.options.load
        save = self.options.save
        xml_file = self.options.xml_file
        if load and save:
            fatal("You cannot load and save at the same time!")
        if not xml_file:
            fatal("You need to specify a file for the load/save operation.")

        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        storage = request.unprotected_storage

        if load:
            unserialize(storage, xml_file)
            print "The contents of %s have been loaded into your backend." % (xml_file)

        elif save:
            serialize(storage, xml_file)
            print "The contents of your backend have been saved to %s." % (xml_file)

        else:
            fatal("You need to specify whether you want to either load or save.")

