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

# exclude some directories from py.test test discovery, pathes relative to this file
collect_ignore = ['support', # do not test 3rd party stuff
                  'static',  # same
                  '../wiki', # no tests there
                  '../instance', # tw likes to use this for wiki data (non-revisioned)
                 ]

import atexit
import os
import sys

import py

rootdir = py.path.local(__file__)
moindir = rootdir.join("..")

from flask import flaskg

from MoinMoin import create_app, protect_backends, before
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


def init_test_app(given_config):
    namespace_mapping, router_index_uri = create_simple_mapping("memory:", given_config.content_acl)
    more_config = dict(
        namespace_mapping=namespace_mapping,
        router_index_uri=router_index_uri,
    )
    app = create_app(flask_config_dict=dict(SECRET_KEY='foo'),
                     moin_config_class=given_config,
                     **more_config)
    ctx = app.test_request_context('/')
    ctx.push()
    before()
    request = flaskg.context
    return app, ctx, request


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
        cls.app, cls.ctx, cls.request = init_test_app(given_config)

        def setup_method(f):
            def wrapper(self, *args, **kwargs):
                self.app, self.ctx, self.request = init_test_app(given_config)
                # Don't forget to call the class' setup_method if it has one.
                return f(self, *args, **kwargs)
            return wrapper

        def teardown_method(f):
            def wrapper(self, *args, **kwargs):
                self.ctx.pop()
                # Don't forget to call the class' teardown_method if it has one.
                return f(self, *args, **kwargs)
            return wrapper

        try:
            # Wrap the actual setup_method in our decorator.
            cls.setup_method = setup_method(cls.setup_method)
        except AttributeError:
            # Perhaps the test class did not define a setup_method.
            def no_setup(self, method):
                self.app, self.ctx, self.request = init_test_app(given_config)
            cls.setup_method = no_setup

        try:
            # Wrap the actual teardown_method in our decorator.
            cls.teardown_method = setup_method(cls.teardown_method)
        except AttributeError:
            # Perhaps the test class did not define a teardown_method.
            def no_teardown(self, method):
                self.ctx.pop()
            cls.teardown_method = no_teardown

        super(MoinClassCollector, self).setup()

    def teardown(self):
        cls = self.obj
        cls.ctx.pop()
        super(MoinClassCollector, self).teardown()


class Module(py.test.collect.Module):
    Class = MoinClassCollector
    Function = MoinTestFunction

    def __init__(self, *args, **kwargs):
        given_config = wikiconfig.Config
        self.app, self.ctx, self.request = init_test_app(given_config)
        # XXX do ctx.pop() in ... (where?)
        super(Module, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        if coverage is not None:
            coverage_modules.update(getattr(self.obj, 'coverage_modules', []))
        return super(Module, self).run(*args, **kwargs)

