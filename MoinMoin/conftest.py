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
import os
import sys

import py

rootdir = py.path.local(__file__)
moindir = rootdir.join("..")

from MoinMoin import support
dirname = os.path.dirname(support.__file__)
dirname = os.path.abspath(dirname)
if not dirname in sys.path:
    sys.path.insert(0, dirname)


from MoinMoin.web.request import TestRequest
from . import app, protect_backends, before, flaskg
from MoinMoin._tests import maketestwiki, wikiconfig
from MoinMoin.storage.backends import create_simple_mapping

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


def init_test_request(given_config):
    with app.test_client() as c:
        rv = c.get('/') #Run a test request in flask
        request = TestRequest() #Same thing for moin
        # XXX: We need a way to merge the two requests
        #      or see which one is the best.
        content_acl = given_config.content_acl
        given_config.namespace_mapping, given_config.router_index_uri = \
            create_simple_mapping("memory:", content_acl)
        app.config['MOINCFG'] = given_config
        before()
        request.cfg = flaskg.context.cfg #XXX: Should not be set up manually normally.
        return request

# py.test customization starts here

# py.test-1.0 provides "funcargs" natively
def pytest_funcarg__request(request):
    # note the naminng clash: py.test's funcarg-request object
    # and the request we provide are totally separate things
    cls = request._pyfuncitem.getparent(py.test.collect.Module)
    return cls.request

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
        cls.request = init_test_request(given_config)
        # XXX: We probably need a cls.client

        # In order to provide fresh backends for each and every testcase,
        # we wrap the setup_method in a decorator that performs the freshening
        # operation. setup_method is invoked by py.test automatically prior to
        # executing any testcase.
        def setup_method(f):
            def wrapper(self, *args, **kwargs):
                self.request = init_test_request(given_config)
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
                self.request = init_test_request(given_config)
            cls.setup_method = no_setup

        super(MoinClassCollector, self).setup()


class Module(py.test.collect.Module):
    Class = MoinClassCollector
    Function = MoinTestFunction

    def __init__(self, *args, **kwargs):
        given_config = wikiconfig.Config
        self.request = init_test_request(given_config)
        super(Module, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)

