# -*- coding: iso-8859-1 -*-
"""
MoinMoin Testing Framework
--------------------------

All test modules must be named test_modulename to be included in the
test suite. If you are testing a package, name the test module
test_package_module.

Tests that need the current request, for example to create a page
instance, can refer to self.request. It is injected into all test case
classes by the framework.

Tests that require a certain configuration, like section_numbers = 1, must
use a Config class to define the required configuration within the test class.

@copyright: 2005 MoinMoin:NirSoffer,
            2007 MoinMoin:AlexanderSchremmer,
            2008 MoinMoin:ThomasWaldmann
@license: GNU GPL, see COPYING for details.
"""

import atexit
import sys

import py

rootdir = py.magic.autopath().dirpath()
moindir = rootdir.join("..")
sys.path.insert(0, str(moindir))

from MoinMoin.support.python_compatibility import set
from MoinMoin.web.request import TestRequest, Client
from MoinMoin.wsgiapp import Application, init, init_unprotected_backends, protect_backends
from MoinMoin._tests import maketestwiki, wikiconfig

coverage_modules = set()

try:
    """
    This code adds support for coverage.py (see
    http://nedbatchelder.com/code/modules/coverage.html).
    It prints a coverage report for the modules specified in all
    module globals (of the test modules) named "coverage_modules".
    """

    import coverage

    def report_coverage():
        coverage.stop()
        module_list = [sys.modules[mod] for mod in coverage_modules]
        module_list.sort()
        coverage.report(module_list)

    def callback(option, opt_str, value, parser):
        atexit.register(report_coverage)
        coverage.erase()
        coverage.start()

    py.test.config.addoptions('MoinMoin options', py.test.config.Option('-C',
        '--coverage', action='callback', callback=callback,
        help='Output information about code coverage (slow!)'))

except ImportError:
    coverage = None


def init_test_request(given_config=None, static_state=[False]):
    request = TestRequest()
    request.given_config = given_config
    request = init(request)
    protect_backends(request)

    return request


def dirties_backend(func):
    """ Decorator for methods that dirty the current backend and
        require a fresh one after execution. """
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        finally:
            args[0].request.cfg.provide_fresh_backends()
    return wrapper


# py.test customization starts here

class MoinTestFunction(py.test.collect.Function):
    def execute(self, target, *args):
        request = self.parent.request
        co = target.func_code
        if 'request' in co.co_varnames[:co.co_argcount]:
            target(request, *args)
        else:
            target(*args)


class MoinClassCollector(py.test.collect.Class):
    Function = MoinTestFunction

    def setup(self):
        cls = self.obj
        if hasattr(cls, 'Config'):
            given_config = cls.Config
        else:
            given_config = wikiconfig.Config
        cls.request = init_test_request(given_config=given_config)
        cls.client = Client(Application(given_config))

        # In order to provide fresh backends for each and every testcase,
        # we wrap the setup_method in a decorator that performs the freshening
        # operation. setup_method is invoked by py.test automatically prior to
        # executing any testcase.
        def setup_method(f):
            def wrapper(self, *args, **kwargs):
                self.request = init_test_request(given_config=given_config)
                # Don't forget to call the class' setup_method if it has one.
                return f(self, *args, **kwargs)
            return wrapper

        try:
            # Wrap the actual setup_method in our refresher-decorator.
            cls.setup_method = setup_method(cls.setup_method)
        except AttributeError:
            # Perhaps the test class did not define a setup_method.
            # We want to provide fresh backends nevertheless, so we
            # provide a setup_method ourselves.
            def no_setup(self, method):
                self.request = init_test_request(given_config=given_config)
            cls.setup_method = no_setup

        super(MoinClassCollector, self).setup()


class Module(py.test.collect.Module):
    Class = MoinClassCollector
    Function = MoinTestFunction

    def __init__(self, *args, **kwargs):
        given_config = wikiconfig.Config
        self.request = init_test_request(given_config=given_config)
        super(Module, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)

