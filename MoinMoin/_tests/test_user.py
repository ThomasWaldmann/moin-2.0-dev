# -*- coding: utf-8 -*-
"""
    MoinMoin - MoinMoin.user Tests

    @copyright: 2003-2004 by Juergen Hermann <jh@web.de>
                2009 by ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import py

from flask import current_app as app
from flask import flaskg

from MoinMoin import user


class TestEncodePassword(object):
    """user: encode passwords tests"""

    def testAscii(self):
        """user: encode ascii password"""
        # u'MoinMoin' and 'MoinMoin' should be encoded to same result
        expected = "{SSHA}xkDIIx1I7A4gC98Vt/+UelIkTDYxMjM0NQ=="

        result = user.encodePassword("MoinMoin", salt='12345')
        assert result == expected
        result = user.encodePassword(u"MoinMoin", salt='12345')
        assert result == expected

    def testUnicode(self):
        """ user: encode unicode password """
        result = user.encodePassword(u'סיסמה סודית בהחלט', salt='12345') # Hebrew
        expected = "{SSHA}YiwfeVWdVW9luqyVn8t2JivlzmUxMjM0NQ=="
        assert result == expected


class TestLoginWithPassword(object):
    """user: login tests"""

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

    def testAsciiPassword(self):
        """ user: login with ascii password """
        # Create test user
        name = u'__Non Existent User Name__'
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def testUnicodePassword(self):
        """ user: login with non-ascii password """
        # Create test user
        name = u'__שם משתמש לא קיים__' # Hebrew
        password = name
        self.createUser(name, password)

        # Try to "login"
        theUser = user.User(name=name, password=password)
        assert theUser.valid

    def test_auth_with_apr1_stored_password(self):
        """
        Create user with {APR1} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbm blaze 12345"
        password = '{APR1}$apr1$NG3VoiU5$PSpHT6tV0ZMKkSZ71E3qg.' # 12345
        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_auth_with_md5_stored_password(self):
        """
        Create user with {MD5} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        password = '{MD5}$1$salt$etVYf53ma13QCiRbQOuRk/' # 12345
        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def test_auth_with_des_stored_password(self):
        """
        Create user with {DES} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbd blaze 12345"
        password = '{DES}gArsfn7O5Yqfo' # 12345
        self.createUser(name, password, True)

        try:
            import crypt
            # Try to "login"
            theuser = user.User(name=name, password='12345')
            assert theuser.valid
        except ImportError:
            py.test.skip("Platform does not provide crypt module!")

    def test_auth_with_ssha256_stored_password(self):
        """
        Create user with {SSHA256} password and check that user can login.
        """
        # Create test user
        name = u'Test User'
        # generated with online sha256 tool
        # pass: 12345
        # salt: salt
        # base64 encoded
        password = '{SSHA256}r4ONZUfEyn9MUkcyDQkQ5MBNpdIerM24MasxFpuQBaFzYWx0'

        self.createUser(name, password, True)

        # Try to "login"
        theuser = user.User(name=name, password='12345')
        assert theuser.valid

    def testSubscriptionSubscribedPage(self):
        """ user: tests isSubscribedTo  """
        pagename = u'HelpMiscellaneous'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert theUser.isSubscribedTo([pagename]) # list(!) of pages to check

    def testSubscriptionSubPage(self):
        """ user: tests isSubscribedTo on a subpage """
        pagename = u'HelpMiscellaneous'
        testPagename = u'HelpMiscellaneous/FrequentlyAskedQuestions'
        name = u'__Jürgen Herman__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name, password=password)
        theUser.subscribe(pagename)
        assert not theUser.isSubscribedTo([testPagename]) # list(!) of pages to check

    def testRenameUser(self):
        """ create user and then rename user and check if it still
        exists under old name
        """
        # Create test user
        name = u'__Some Name__'
        password = name
        self.createUser(name, password)
        # Login - this should replace the old password in the user file
        theUser = user.User(name=name)
        # Rename user
        theUser.name = u'__SomeName__'
        theUser.save()
        theUser = user.User(name=name, password=password)

        assert not theUser.exists()

    def test_upgrade_password_from_sha_to_ssha(self):
        """
        Create user with {SHA} password and check that logging in
        upgrades to {SSHA}.
        """
        name = u'/no such user/'
        password = '{SHA}jLIjfQZ5yojbZGTqxg2pY0VROWQ=' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:6] == '{SSHA}'

    def test_upgrade_password_from_apr1_to_ssha(self):
        """
        Create user with {APR1} password and check that logging in
        upgrades to {SSHA}.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbm blaze 12345"
        password = '{APR1}$apr1$NG3VoiU5$PSpHT6tV0ZMKkSZ71E3qg.' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:6] == '{SSHA}'

    def test_upgrade_password_from_md5_to_ssha(self):
        """
        Create user with {MD5} password and check that logging in
        upgrades to {SSHA}.
        """
        # Create test user
        name = u'Test User'
        password = '{MD5}$1$salt$etVYf53ma13QCiRbQOuRk/' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:6] == '{SSHA}'

    def test_upgrade_password_from_des_to_ssha(self):
        """
        Create user with {DES} password and check that logging in
        upgrades to {SSHA}.
        """
        # Create test user
        name = u'Test User'
        # generated with "htpasswd -nbd blaze 12345"
        password = '{DES}gArsfn7O5Yqfo' # 12345
        self.createUser(name, password, True)

        # User is not required to be valid
        theuser = user.User(name=name, password='12345')
        assert theuser.enc_password[:6] == '{SSHA}'

    def test_for_email_attribute_by_name(self):
        """
        checks for no access to the email attribute by getting the user object from name
        """
        name = u"__TestUser__"
        password = u"ekfdweurwerh"
        email = "__TestUser__@moinhost"
        self.createUser(name, password, email=email)
        theuser = user.User(name=name)
        assert theuser.email is None

    def test_for_email_attribut_by_uid(self):
        """
        checks access to the email attribute by getting the user object from the uid
        """
        name = u"__TestUser2__"
        password = u"ekERErwerwerh"
        email = "__TestUser2__@moinhost"
        self.createUser(name, password, email=email)
        uid = user.getUserId(name)
        theuser = user.User(uid)
        assert theuser.email == email

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


class TestGroupName(object):

    def testGroupNames(self):
        """ user: isValidName: reject group names """
        test = u'AdminGroup'
        assert not user.isValidName(test)


class TestIsValidName(object):

    def testNonAlnumCharacters(self):
        """ user: isValidName: reject unicode non alpha numeric characters

        : and , used in acl rules, we might add more characters to the syntax.
        """
        invalid = u'! # $ % ^ & * ( ) = + , : ; " | ~ / \\ \u0000 \u202a'.split()
        base = u'User%sName'
        for c in invalid:
            name = base % c
            assert not user.isValidName(name)

    def testWhitespace(self):
        """ user: isValidName: reject leading, trailing or multiple whitespace """
        cases = (
            u' User Name',
            u'User Name ',
            u'User   Name',
            )
        for test in cases:
            assert not user.isValidName(test)

    def testValid(self):
        """ user: isValidName: accept names in any language, with spaces """
        cases = (
            u'Jürgen Hermann', # German
            u'ניר סופר', # Hebrew
            u'CamelCase', # Good old camel case
            u'가각간갇갈 갉갊감 갬갯걀갼' # Hangul (gibberish)
            )
        for test in cases:
            assert user.isValidName(test)


coverage_modules = ['MoinMoin.user']

