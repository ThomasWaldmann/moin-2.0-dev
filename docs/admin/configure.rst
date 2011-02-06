==================
Wiki Configuration
==================

To change how moin behaves and looks like, you may customize it by editing
its configuration file (often called wikiconfig.py).

When editing the config, please note that this is Python code, so be careful
with indentation, only use multiples of 4 spaces to indent, no tabs!

It is a good idea to start from one of the sample configs provided with moin
and only do small careful changes, then trying it, then doing next change.
If you're not used to Python syntax, backup your last working config so you
can revert to it in case you make some hard to find typo or other error.

Python powered
==============

At first, you might wonder why we use Python code for configuration. It is
simply because it is powerful and we can make use of that power there.

One of Python's powerful features is class inheritance: you can inherit most
settings from a DefaultConfig class (which is defined in the moin code) and
just override the settings you want different from the defaults.

So, a typical wikiconfig.py works like this::

 from MoinMoin.config.default import DefaultConfig

 class Config(DefaultConfig):
     # a comment
     sometext = u'your value'
     somelist = [1, 2, 3]

Let's go through this line-by-line:

1. this gets the DefaultConfig class from the moin code
2. an empty line, for better readability
3. now we define a new class `Config` that inherits most stuff from
   `DefaultConfig`
4. with a `#` character you can write a comment into your config. This line (as
   well as all other following lines with Config settings) is indented by 4
   blanks, because Python defines blocks by indentation.
5. define a Config attribute called `sometext` with value u'your value' -
   the `u'...'` means that this is a unicode string.
6. define a Config attribute called `somelist` with value [1, 2, 3] - this is
   a list with the numbers 1, 2 and 3 as list elements.


Authentication
==============
MoinMoin uses a configurable `auth` list of authenticators, so the admin can
configure whatever he likes to allow for authentication. Moin processes this
list from left to right.

Each authenticator is an instance of some specific class, configuration of
the authenticators usually works by giving them keyword arguments. Most have
reasonable defaults, though.

MoinAuth
--------
This is the default authentication moin uses if you don't configure something
else. The user logs in by filling out the login form with username and
password, moin compares the password hash against the one stored in the user's
profile and if both match, the user is authenticated::

    from MoinMoin.auth import MoinAuth
    auth = [MoinAuth()]  # this is the default!

HTTPAuthMoin
------------
With HTTPAuthMoin moin does http basic auth all by itself (without help of
the web server)::

    from MoinMoin.auth.http import HTTPAuthMoin
    auth = [HTTPAuthMoin(autocreate=True)]

If configured like that, moin will request authentication by emitting a
http header. Browsers then usually show some login dialogue to the user,
asking for username and password. Both then gets transmitted to moin and it
is compared against the password hash stored in the user's profile.

Note: when HTTPAuthMoin is used, the browser will show that login dialogue, so
users must login to use the wiki.

GivenAuth
---------
With GivenAuth moin relies on the webserver doing the authentication and giving
the result to moin (usually via environment variable REMOTE_USER)::

    from MoinMoin.auth import GivenAuth
    auth = [GivenAuth(autocreate=True)]

Using this has some pros and cons:

* you can use lots of authentication extensions available for your web server
* but the only information moin will get (via REMOTE_USER) is the authenticated
  user's name, nothing else. So, e.g. for LDAP/AD, you won't get additional
  stuff stored in the LDAP directory.
* all the stuff you won't get (but you need) will need to be manually stored
  and updated in the user's profile (e.g. the user's email address, etc.)

OpenID
------
With OpenID moin can re-use the authentication done by some OpenID provider
(like Google, Yahoo, Microsoft or others)::

    from MoinMoin.auth.openidrp import OpenIDAuth
    auth = [OpenIDAuth()]

By default OpenID authentication accepts all OpenID providers. If you
like, you can configure what providers to allow (which ones you want to trust)
by adding their URLs to the trusted_providers keyword of OpenIDAuth. If left
empty, moin will allow all providers::

    # Allow google profile OpenIDs only:
    auth = [OpenIDAuth(trusted_providers=['https://www.google.com/accounts/o8/ud?source=profiles'])]

To be able to log in with OpenID, the user needs to have his OpenID stored
in his user profile.

LDAPAuth
--------
With LDAPAuth you can authenticate users against a LDAP directory or MS Active Directory service.

LDAPAuth with single LDAP server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example shows how to use it with a single LDAP/AD server::

    from MoinMoin.auth.ldap_login import LDAPAuth
    ldap_common_arguments = dict(
        # the values shown below are the DEFAULT values (you may remove them if you are happy with them),
        # the examples shown in the comments are typical for Active Directory (AD) or OpenLDAP.
        bind_dn='',  # We can either use some fixed user and password for binding to LDAP.
                     # Be careful if you need a % char in those strings - as they are used as
                     # a format string, you have to write %% to get a single % in the end.
                     #bind_dn = 'binduser@example.org' # (AD)
                     #bind_dn = 'cn=admin,dc=example,dc=org' # (OpenLDAP)
                     #bind_pw = 'secret'
                     # or we can use the username and password we got from the user:
                     #bind_dn = '%(username)s@example.org' # DN we use for first bind (AD)
                     #bind_pw = '%(password)s' # password we use for first bind
                     # or we can bind anonymously (if that is supported by your directory).
                     # In any case, bind_dn and bind_pw must be defined.
        bind_pw='',
        base_dn='',  # base DN we use for searching
                     #base_dn = 'ou=SOMEUNIT,dc=example,dc=org'
        scope=2, # scope of the search we do (2 == ldap.SCOPE_SUBTREE)
        referrals=0, # LDAP REFERRALS (0 needed for AD)
        search_filter='(uid=%(username)s)',  # ldap filter used for searching:
                                             #search_filter = '(sAMAccountName=%(username)s)' # (AD)
                                             #search_filter = '(uid=%(username)s)' # (OpenLDAP)
                                             # you can also do more complex filtering like:
                                             # "(&(cn=%(username)s)(memberOf=CN=WikiUsers,OU=Groups,DC=example,DC=org))"
        # some attribute names we use to extract information from LDAP (if not None,
        # if None, the attribute won't be extracted from LDAP):
        givenname_attribute=None, # often 'givenName' - ldap attribute we get the first name from
        surname_attribute=None, # often 'sn' - ldap attribute we get the family name from
        aliasname_attribute=None, # often 'displayName' - ldap attribute we get the aliasname from
        email_attribute=None, # often 'mail' - ldap attribute we get the email address from
        email_callback=None, # callback function called to make up email address
        coding='utf-8', # coding used for ldap queries and result values
        timeout=10, # how long we wait for the ldap server [s]
        start_tls=0, # usage of Transport Layer Security 0 = No, 1 = Try, 2 = Required
        tls_cacertdir=None,
        tls_cacertfile=None,
        tls_certfile=None,
        tls_keyfile=None,
        tls_require_cert=0, # 0 == ldap.OPT_X_TLS_NEVER (needed for self-signed certs)
        bind_once=False, # set to True to only do one bind - useful if configured to bind as the user on the first attempt
        autocreate=True, # set to True to automatically create/update user profiles
        report_invalid_credentials=True, # whether to emit "invalid username or password" msg at login time or not
    )

    ldap_authenticator1 = LDAPAuth(
        server_uri='ldap://localhost',  # ldap / active directory server URI
                                        # use ldaps://server:636 url for ldaps,
                                        # use  ldap://server for ldap without tls (and set start_tls to 0),
                                        # use  ldap://server for ldap with tls (and set start_tls to 1 or 2).
        name='ldap1',  # unique name for the ldap server, e.g. 'ldap_pdc' and 'ldap_bdc' (or 'ldap1' and 'ldap2')
        **ldap_common_arguments  # expand the common arguments
    )

    auth = [ldap_authenticator1, ] # this is a list, you may have multiple ldap authenticators
                                   # as well as other authenticators

    # customize user preferences (optional, see MoinMoin/config/multiconfig for internal defaults)
    # you maybe want to use user_checkbox_remove, user_checkbox_defaults, user_form_defaults,
    # user_form_disable, user_form_remove.

LDAPAuth with two LDAP servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This example shows how to use it with a two LDAP/AD servers (like e.g. a primary
and backup domain controller)::

    # ... same stuff as for single server (except the line with "auth =") ...
    ldap_authenticator2 = LDAPAuth(
        server_uri='ldap://otherldap',  # ldap / active directory server URI for second server
        name='ldap2',
        **ldap_common_arguments
    )

    auth = [ldap_authenticator1, ldap_authenticator2, ]

AuthLog
-------
AuthLog is no real authenticator in the sense that it authenticates (logs in) or
deauthenticates (logs out) users, it is just passively logging informations for
authentication debugging::

    from MoinMoin.auth import MoinAuth
    from MoinMoin.auth.log import AuthLog
    auth = [MoinAuth(), AuthLog(), ]

Example logging output::

 2011-02-05 16:35:00,229 INFO MoinMoin.auth.log:22 login: user_obj=<MoinMoin.user.User at 0x90a0f0c name:u'ThomasWaldmann' valid:1> kw={'username': u'ThomasWaldmann', 'openid': None, 'attended': True, 'multistage': None, 'login_password': u'secret', 'login_username': u'ThomasWaldmann', 'password': u'secret', 'login_submit': u''}
 2011-02-05 16:35:04,716 INFO MoinMoin.auth.log:22 session: user_obj=<MoinMoin.user.User at 0x90a0f6c name:u'ThomasWaldmann' valid:1> kw={}
 2011-02-05 16:35:06,294 INFO MoinMoin.auth.log:22 logout: user_obj=<MoinMoin.user.User at 0x92b5d4c name:u'ThomasWaldmann' valid:False> kw={}
 2011-02-05 16:35:06,328 INFO MoinMoin.auth.log:22 session: user_obj=None kw={}

Note: there are sensitive informations like usernames and passwords in this
log output. Make sure you only use this for testing and delete the logs when
done.

SMBMount
--------
SMBMount is no real authenticator in the sense that it authenticates (logs in)
or deauthenticates (logs out) users. It just catches the username and password
and uses them to mount a SMB share as this user.

SMBMount is only useful for very special applications, e.g. in combination
with the fileserver storage backend::

    from MoinMoin.auth.smb_mount import SMBMount

    smbmounter = SMBMount(
        # you may remove default values if you are happy with them
        # see man mount.cifs for details
        server='smb.example.org',  # (no default) mount.cifs //server/share
        share='FILESHARE',  # (no default) mount.cifs //server/share
        mountpoint_fn=lambda username: u'/mnt/wiki/%s' % username,  # (no default) function of username to determine the mountpoint
        dir_user='www-data',  # (no default) username to get the uid that is used for mount.cifs -o uid=...
        domain='DOMAIN',  # (no default) mount.cifs -o domain=...
        dir_mode='0700',  # (default) mount.cifs -o dir_mode=...
        file_mode='0600',  # (default) mount.cifs -o file_mode=...
        iocharset='utf-8',  # (default) mount.cifs -o iocharset=... (try 'iso8859-1' if default does not work)
        coding='utf-8',  # (default) encoding used for username/password/cmdline (try 'iso8859-1' if default does not work)
        log='/dev/null',  # (default) logfile for mount.cifs output
    )

    auth = [....., smbmounter]  # you need a real auth object in the list before smbmounter

    smb_display_prefix = u"S:"  # where //server/share is usually mounted for your windows users (display purposes only)

.. todo::

   check if SMBMount still works as documented


Transmission security
=====================
Credentials
-----------
Some of the authentication methods described above will transmit credentials
(like usernames and password) in unencrypted form:

* MoinAuth: when the login form contents are transmitted to moin, they contain
  username and password in cleartext.
* HTTPAuthMoin: your browser will transfer username and password in a encoded
  (but NOT encrypted) form with EVERY request (it uses http basic auth).
* GivenAuth: please check the potential security issues of the authentication
  method used by your web server. For http basic auth please see HTTPAuthMoin.
* OpenID: please check yourself.

Contents
--------
http transmits everything in cleartext (not encrypted).

Encryption
----------
Transmitting unencrypted credentials or contents is a serious issue in many
scenarios.

We recommend you make sure connections are encrypted, like with https or VPN
or an ssh tunnel.

For public wikis with very low security / privacy needs, it might not be needed
to encrypt their content transmissions, but there is still an issue for the
credential transmissions.

When using unencrypted connections, wiki users are advised to make sure they
use unique credentials (== not reusing passwords that are also used for other
stuff).


Password security
=================
Password strength
-----------------
As you might know, many users are bad at choosing reasonable passwords and some
are tempted to use passwords like 123456 everywhere.

To help the users choose reasonable passwords, moin has a simple builtin
password checker that does some sanity checks (the checker is enabled by
default), so users don't choose too short or too easy passwords.

If you don't like this and your site has rather low security requirements,
feel free to DISABLE the checker by::

    password_checker = None # no password checking

Note that the builtin password checker only does a few very fundamental
checks, it e.g. won't forbid using a dictionary word as password.

Password storage
----------------
Moin never stores passwords in cleartext, but always as cryptographic hash
with random salt (currently ssha256 is the default).

Anti-Spam
=========
TextChas
--------

A TextCHA is a pure text alternative to ''CAPTCHAs''. MoinMoin uses it to
prevent wiki spamming and it has proven to be very effective.

Features:

* when registering a user or saving an item, ask a random question
* match the given answer against a regular expression
* q and a can be configured in the wiki config
* multi language support: a user gets a textcha in his language or in
  language_default or in English (depending on availability of questions and
  answers for the language)

TextCha Configuration
~~~~~~~~~~~~~~~~~~~~~

Tips for configuration:

* have 1 word / 1 number answers
* ask questions that normal users of your site are likely to be able to answer
* do not ask too hard questions
* do not ask "computable" questions, like "1+1" or "2*3"
* do not ask too common questions
* do not share your questions with other sites / copy questions from other
  sites (or spammers might try to adapt to this) 
* you should at least give textchas for 'en' (or for your language_default, if
  that is not 'en') as this will be used as fallback if MoinMoin does not find
  a textcha in the user's language

In your wiki config, do something like this::

    textchas_disabled_group = u"TrustedEditorGroup" # members of this don't get textchas
    textchas = {
        'en': { # silly english example textchas (do not use them!)
                u"Enter the first 9 digits of Pi.": ur"3\.14159265",
                u"What is the opposite of 'day'?": ur"(night|nite)",
                # ...
        },
        'de': { # some german textchas
                u"Gib die ersten 9 Stellen von Pi ein.": ur"3\.14159265",
                u"Was ist das Gegenteil von 'Tag'?": ur"nacht",
                # ...
        },
        # you can add more languages if you like
    }


Note that TrustedEditorGroup from above example can have groups as members.


Secrets
=======
Moin uses secrets (just use a long random strings, don't reuse any of your
passwords) to encrypt or cryptographically sign some stuff like:

* textchas
* tickets

Don't use the strings shown below, they are NOT secret as they are part of the
moin documentation - make up your own secrets::

    secrets = {
        'security/textcha': 'kjenrfiefbeiaosx5ianxouanamYrnfeorf',
        'security/ticket': 'asdasdvarebtZertbaoihnownbrrergfqe3r',
    }

If you don't configure these secrets, moin will detect this and reuse Flask's
SECRET_KEY for all secrets it needs.


Groups and Dicts
================
Moin can get group and dictionary information from some supported backends
(like the wiki configuration or wiki items).

A group is just a list of unicode names. It can be used for any application,
one application is defining user groups for usage in ACLs.

A dict is a mapping of unicode keys to unicode values. It can be used for any
application, currently it is not used by moin itself.

Group backend configuration
---------------------------
WikiGroups backend gets groups from wiki items and is used by default::

    def groups(self, request):
        from MoinMoin.datastruct import WikiGroups
        return WikiGroups(request)

ConfigGroups uses groups defined in the configuration file::

    def groups(self, request):
        from MoinMoin.datastruct import ConfigGroups
        # Groups are defined here.
        groups = {u'EditorGroup': [u'AdminGroup', u'John', u'JoeDoe', u'Editor1'],
                  u'AdminGroup': [u'Admin1', u'Admin2', u'John']}
        return ConfigGroups(request, groups)

CompositeGroups to use both ConfigGroups and WikiGroups backends::

    def groups(self, request):
        from MoinMoin.datastruct import ConfigGroups, WikiGroups, CompositeGroups
        groups = {u'EditorGroup': [u'AdminGroup', u'John', u'JoeDoe', u'Editor1'],
                  u'AdminGroup': [u'Admin1', u'Admin2', u'John']}

        # Here ConfigGroups and WikiGroups backends are used.
        # Note that order matters! Since ConfigGroups backend is mentioned first
        # EditorGroup will be retrieved from it, not from WikiGroups.
        return CompositeGroups(request,
                               ConfigGroups(request, groups),
                               WikiGroups(request))


Dict backend configuration
--------------------------

WikiDicts backend gets dicts from wiki items and is used by default::

    def dicts(self, request):
        from MoinMoin.datastruct import WikiDicts
        return WikiDicts(request)

ConfigDicts backend uses dicts defined in the configuration file::

    def dicts(self, request):
        from MoinMoin.datastruct import ConfigDicts
        dicts = {u'OneDict': {u'first_key': u'first item',
                              u'second_key': u'second item'},
                 u'NumbersDict': {u'1': 'One',
                                  u'2': 'Two'}}
        return ConfigDicts(request, dicts)

CompositeDicts to use both ConfigDicts and WikiDicts::

    def dicts(self, request):
        from MoinMoin.datastruct import ConfigDicts, WikiDicts, CompositeDicts
        dicts = {u'OneDict': {u'first_key': u'first item',
                              u'second_key': u'second item'},
                 u'NumbersDict': {u'1': 'One',
                                  u'2': 'Two'}}
        return CompositeDicts(request,
                              ConfigDicts(request, dicts),
                              WikiDicts(request))


Mail configuration
==================

Sending E-Mail
--------------
Moin can optionally send E-Mail, e.g. to:

* send out item change notifications.
* enable users to reset forgotten passwords

You need to configure some stuff before sending E-Mail can be supported::

    # the "from:" address [Unicode]
    mail_from = u"wiki <wiki@example.org>"

    # a) using a SMTP server, e.g. "mail.provider.com" (None to disable mail)
    mail_smarthost = "smtp.example.org"

    # if you need to use SMTP AUTH at your mail_smarthost:
    #mail_login = "smtp_username smtp_password"

    # b) alternatively to using SMTP, you can use the sendmail commandline tool:
    #mail_sendmail = "/usr/sbin/sendmail -t -i"

.. todo::

   mail_login is a bit ugly mixing username and password into one string


.. todo::

   describe more moin configuration


=====================
Logging configuration
=====================

By default, logging is configured to emit output on `stderr`. This will work
OK for the builtin server (will just show on the console) or for e.g. Apache2
(will be put into error.log).

Logging is very configurable and flexible due to the use of the `logging`
module of the Python standard library.

The configuration file format is described there:

http://www.python.org/doc/current/library/logging.html#configuring-logging


There are also some logging configurations in the `examples/` directory.

Logging configuration needs to be done very early, usually it will be done
from your adaptor script (e.g. moin.wsgi)::

    from MoinMoin import log
    log.load_config('wiki/config/logging/logfile')

You have to fix that path to use a logging configuration matching your
needs.

Please note that the logging configuration has to be a separate file (don't
try this in your wiki configuration file)!

