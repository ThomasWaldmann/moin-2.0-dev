# -*- coding: utf-8 -*-
"""
    MoinMoin - basic tests for frontend

    @copyright: 2010 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""
from MoinMoin.apps.frontend import views
from werkzeug import ImmutableMultiDict
from flask import flaskg
from MoinMoin import user

class TestFrontend(object):
    def test_root(self):
        with self.app.test_client() as c:
            rv = c.get('/') # / redirects to front page
            assert rv.status == '302 FOUND'

    def test_robots(self):
        with self.app.test_client() as c:
            rv = c.get('/robots.txt')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/plain; charset=utf-8'
            assert 'Disallow:' in rv.data

    def stest_favicon(self):
        with self.app.test_client() as c:
            rv = c.get('/favicon.ico')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'image/x-icon'
            assert rv.data.startswith('\x00\x00') # "reserved word, should always be 0"

    def test_404(self):
        with self.app.test_client() as c:
            rv = c.get('/DoesntExist')
            assert rv.status == '404 NOT FOUND'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data

    def test_global_index(self):
        with self.app.test_client() as c:
            rv = c.get('/+index')
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<html>' in rv.data
            assert '</html>' in rv.data

class TestUsersettings(object):
    def setup_method(self, method):
        # Save original user
        self.saved_user = flaskg.user

        # Create anon user for the tests
        flaskg.user = user.User()

        self.user = None

    def teardown_method(self, method):
        """ Run after each test

        Remove user and reset user listing cache.
        """
        # Remove user file and user
        if self.user is not None:
            del self.user

        # Restore original user
        flaskg.user = self.saved_user

    def test_user_password_change(self):
        self.createUser('moin', '12345')
        flaskg.user = user.User(name='moin', password='12345')

        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password1', u'123'),
              ('usersettings_password_submit', u'Save'),
              ('usersettings_password_password_current', u'12345'),
              ('usersettings_password_password2', u'123')
           ]
        )
        form = FormClass.from_flat(request_form)
        valid = form.validate()
        assert valid # form data is valid

    def test_user_unicode_password_change(self):
        name = u'__שם משתמש לא קיים__' # Hebrew
        password = name

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)

        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password1', u'123'),
              ('usersettings_password_submit', u'Save'),
              ('usersettings_password_password_current', password),
              ('usersettings_password_password2', u'123')
           ]
        )
        form = FormClass.from_flat(request_form)
        valid = form.validate()
        assert valid # form data is valid

    def test_user_password_change_to_unicode_pw(self):
        name = 'moin'
        password = '12345'
        new_password = u'__שם משתמש לא קיים__' # Hebrew

        self.createUser(name, password)
        flaskg.user = user.User(name=name, password=password)

        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password1', new_password),
              ('usersettings_password_submit', u'Save'),
              ('usersettings_password_password_current', password),
              ('usersettings_password_password2', new_password)
           ]
        )
        form = FormClass.from_flat(request_form)
        valid = form.validate()
        assert valid # form data is valid

    def test_faul_user_password_change_pw_mismatch(self):
        self.createUser('moin', '12345')
        flaskg.user = user.User(name='moin', password='12345')

        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password1', u'1234'),
              ('usersettings_password_submit', u'Save'),
              ('usersettings_password_password_current', u'12345'),
              ('usersettings_password_password2', u'123')
           ]
        )
        form = FormClass.from_flat(request_form)
        valid = form.validate()
        # form data is invalid because password1 != password2
        assert not valid

    def test_fail_password_change(self):
        self.createUser('moin', '12345')
        flaskg.user = user.User(name='moin', password='12345')

        FormClass = views.UserSettingsPasswordForm
        request_form = ImmutableMultiDict(
           [
              ('usersettings_password_password1', u'123'),
              ('usersettings_password_submit', u'Save'),
              ('usersettings_password_password_current', u'54321'),
              ('usersettings_password_password2', u'123')
           ]
        )
        form = FormClass.from_flat(request_form)
        valid = form.validate()
        # form data is invalid because password_current != user.password
        assert not valid

    # Helpers ---------------------------------------------------------

    def createUser(self, name, password, pwencoded=False, email=None):
        """ helper to create test user
        """
        # Create user
        self.user = user.User()
        self.user.name = name
        self.user.email = email
        if not pwencoded:
            password = user.encodePassword(password)
        self.user.enc_password = password

        # Validate that we are not modifying existing user data file!
        if self.user.exists():
            self.user = None
            py.test.skip("Test user exists, will not override existing user data file!")

        # Save test user
        self.user.save()

        # Validate user creation
        if not self.user.exists():
            self.user = None
            py.test.skip("Can't create test user")
