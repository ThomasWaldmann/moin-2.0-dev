MoinMoin Version History
========================

Please note: Starting from the MoinMoin version you used previously, you
should read all more recent entries (or at least everything marked with HINT).

This release has known bugs (see MoinMoin:MoinMoinBugs), but we think it is
already better than the previous stable release. Our release policy is not
trying to make a "perfect release" (as that release might NEVER get released),
but to make progress and don't delay releases too much.

Known main issues:

  * The GUI WYSIWYG editor has still some issues and limitations.
    If you can't live with those, you can simply switch it off by using:
    editor_force = True
    editor_default = 'text'  # internal default, just for completeness

Version 1.9.3:
  Fixes:
  * Fix XSS in Despam action (CVE-2010-0828).
  * Fix XSS issues (see MoinMoinBugs/1.9.2UnescapedInputForThemeAddMsg):
    * by escaping template name in messages
    * by fixing other places that had similar issues
  * Make moin compatible to werkzeug 0.5 .. 0.6.2 (1.9.2 had issues
    with xmlrpc when used with werkzeug 0.6.x).
  * MoinMoin.util.filesys: disable usage of dircache, deprecate dc* functions,
    because the dircache stdlib module can't work correctly for fast updates of
    directories.
  * rss_rc and sisterpages actions: fix Content-Type header (mimetype)
  * Fix associating OpenID identity with user, wasn't adapted to werkzeug yet.
  * openidrp auth: fix undefined _ (gettext)
  * Fix auth.cas and userprefs.oidserv request object usage.
  * highlight parser: fixed MoinMoinBugs/LineNumberSpansForProcessInstructionsMissed
  * Pygments syntax highlighting: add missing code files
  * Notifications: use same email subject format for every notification
  * Fix docbook formatter crashing, see MoinMoinPatch/IncludeMacroWithDocBookFormatter
  * Fix regex content search for xapian search.
  * Get rid of the empty line at the end of code highlights.
  * GUI editor: compute editor height like the text editor does.
  * Added help texts for: standalone server and moin migration.
  * script.maint.cleancache: clean also i18n cache files
  * Improved formatter.text_plain, see FeatureRequests/TextPlainFormatterRewrite
    (fixes many issues of this formatter).
  * text_html_text_moin_wiki: fixed index error for width="", see also:
    MoinMoinBugs/GUI_convertor_list_index_out_of_range
  * xmlrpc: disable editor backup for putPage, renamePage and revertPage
    because if pages get uploaded by xmlrpc then the draft cache file can
    rapidly increase in size, causing high memory usage because it needs to
    get loaded into memory for updating/processing.
  * Emit Content-Type header (with charset) for SlideShow action and many other
    actions that just call send_title().
  * ActionBase: better compatibility to moin 1.8, use request.values by
    default, optionally use request.form data only

  New features:
  * RenamePage action: added ability to create redirect pages when renaming
    (turned off by default, see show_rename_redirect config option).
  * formatter/text_html: Added line number links to code blocks.
  * diff action:
    * Fixed whitespace in generated (html) diff view table so white-space: pre
      can be used (and whitespace in diffs preserved).
    * Added links to first/last revision.
  * MoinMoin.widget.browser: introduced feature for sorting tables, see:
    http://moinmo.in/FeatureRequests/SortableTables
  * SystemAdmin user and attachment browsers: sorting feature used there now
  * Scrolling the text editor to the double clicked line.
  * Enable double-click-editing by default.
  * WikiConfigHelp macro: make heading and description display optional,
    heading level as a parameter (default 2)
  * If edit ticket check fails, send the editor with the current content.
  * moin import wikipage - use this script to import local files as a wiki page

  Other changes:
  * upgraded pygments from 1.2.2 to 1.3.1
  * upgraded FCKeditor from 2.6.4.1 to 2.6.6
  * added configuration snippet for ldap authentication against 2 servers
  * improved script help output

Version 1.9.2:
  Fixes:
  * Fixed CVE-2010-0668: major security issues were discovered in misc. parts
    of moin.
    HINT: if you have removed superuser configuration to workaround the issue
    (following our security advisory), you may re-add it after installing this
    moin release. If you don't need superuser capabilities often, it might be
    wise to not have superusers configured all the time, though.
  * Fixed CVE-2010-0669: potential security issue due to incomplete user profile
    input sanitizing.
  * Improved package security: cfg.packagepages_actions_excluded excludes
    unsafe or otherwise questionable package actions by default now.
  * wiki parser: fixed transclusion of (e.g. video) attachments from other
    pages.
  * Fixed edit locking for non-logged in editors and cfg.log_remote_addr=False.
  * mailimport: fix missing wikiutil import for normalize_pagename
  * SubProcess: fix "timeout" AttributeError
  * "standalone" wikiserver.py: fixed calling non-existing os.getuid on win32
  * HTTPAuth deprecation warning moved from class level to __init__
  * Fixed MoinMoinBugs/1.9DiffActionThrowsException.
  * Fixed misc. session related problems, avoid unneccessary session file
    updates.
  * Fix/improve rename-related problems on Win32 (depending on Windows version).
  * Fixed spider / user agent detection.
  * Make sure to use language_default when language_ignore_browser is set.
  * diff action: fix for case when user can't revert page.
  * Fix trail size (was off by one).
  * Updated bundled flup middleware (upstream repo checkout), avoids
    socket.fromfd AttributeError on win32 if cgi is forced, gives helpful
    exception msg.
  * wikiutil: Fixed required_arg handling (no exception when trying to raise
    exception that choice is wrong).
  * Do not use MoinMoin.support.* to import 3rd party code, give dist packages
    a chance.
  * wikiutil.clean_input: avoid crash if it gets str type
  * request: fixed for werkzeug 0.6 and 0.5.1 compatibility. Please note that
    we didn't do much testing with 0.6 yet. So, if you use 0.6, please do some
    testing and provide feedback to us.
  * AttachFile._build_filelist: verifies readonly flag for unzip file link
  * attachUrl: fix wrongly generated tickets (e.g. for AttachList macro)
  * http headers: fix duplicated http headers (e.g. content-type)

  New features:
  * info action: added pagination ability to revision history viewer.
    Use cfg.history_paging = True [default] / False to enable/disable it.
  * ldap_login auth: add report_invalid_credentials param to control wrong
    credentials error message (this is typically used when using multiple
    ldap authenticators).
  * Add RenderAsDocbook to actions_excluded if we have no python-xml.
  * Upgraded pygments to 1.2.2 (some fixes, some new lexers).
  * Text editor: if edit_rows==0 (user profile or config), we dynamically size
    the text editor height. This avoids double sliders for the editor page
    in most cases.

  Other changes:
  * New docs/REQUIREMENTS.
  * Added a less magic cgi/fcgi driver (moin.fcgi), added fixer middleware
    for apache2/win32 to it.


Version 1.9.1:
  Bug fixes:
  * Fixed CVE-2010-0667: sys.argv security issue.
  * Fixed FileSessionService - use session_dir from CURRENT request.cfg (it
    mixed up session_dirs in farm setups).
    HINT: if you added the hotfix to your wikiconfig, please remove it now.
  * Fixed creation of lots of session files (if anon session were enabled and
    user agent did not support cookies).
  * Fixed session file storage for a non-ascii base path.
  * Fixed session cookie confusion for nested URL paths (like path=/ and
    path=/mywiki - for more info, see also "New features").
  * Handle cookie_lifetime / anonymous_session_lifetime upgrade issue
    gracefully: emit errors/warnings to log, use old settings to create
    cfg.cookie_lifetime as expected by moin 1.9.
  * flup based frontends: fixed SCGI and AJP (didn't work).
  * farmconfig example: remove wrong comment, add sample http/https entry.
  * Fixed password reset url (email content needs full URL).
  * Page: fixed adding of page contents (only data added now, without metadata) -
    fixes MoinMoinBugs/DeprecatedPageInclusionErrornousPageInstructionsProcessing
  * xmlrpc:
    * Process attachname in get/putAttachment similarly.
    * revertPage: convert pagename to internal representation.
    * Fixed auth calls used by jabberbot (needs more work).
  * Added missing config.umask support code (setting was not used), fixed
    config.umask usage for page packages.
  * Fixed browser language detection.
  * Fixed language pack generation/installation for pt-br, zh, zh-tw.
  * Fixed caching of formatted msgs, see MoinMoinBugs/1.9EditPageHelpLinksBroken.
  * Fixed usage of i18n.wikiLanguages() on class level (moved to method), failed
    when tools import the module (e.g. pydoc -k foo).
  * highlight parser:
    * fixed caching issue for "toggle line numbers" link.
    * added missing support for console/bash session
  * Fixed precedence of parsers: more special parsers now have precedence
    before moin falls back to using the HighlightParser (syntax highlighting).
  * Added extensions to the rst, moin and creole parser (example.rst, example.moin and
    example.creole attachments are rendered now when viewed).
  * Fixed MoinMoinBugs/LineNumberSpansForProcessInstructionsMissed for
    moin_wiki, highlight and plain parser.
  * Fixed MoinMoinBugs/LineNumberAnchorsInPreformattedText for highlight and
    plain parser.
  * Fixed MoinMoinBugs/TableOfContentsBrokenForIncludedPages.
  * Exception raised on calling add_msg() after send_title(), which leads to 
    Internal Server Error on calling several actions (diff, preview) for 
    deprecated pages, is replaced with warning and call stack information in 
    the log.
  * AttachFile.move_file: send events (so e.g. xapian index update happens)
  * SubProcess: fixed win32-specific parts, fixed imports (fixes calling of
    external xapian index filters)
  * Fixed auth methods that use redirects (like OpenID).
  * OpenID client:
    * Add setting cfg.openidrp_allowed_op, default is [].
    * Fixed logging in with openid and associating with an existing account.
    * openidrp_sreg extension: handle UnknownTimeZoneError gracefully
  * OpenID server:
    * Fixed TypeError.
    * Fixed processing POSTed form data AND URL args.

  New features:
  * diff: Added displaying of information about revisions (editor, size, 
    timestamp, comment), added revision navigation.
  * text editor: added @TIMESTAMP@ variable for adding a raw time stamp
  * xmlrpc: added renamePage and deleteAttachment methods.
  * Accept "rel" attribute for links (moin wiki parser).
  * Generate session cookie names to fix cookie path confusion and enable port-
    based wiki farming.

    HINT: New setting cfg.cookie_name:

    None (default): use MOIN_SESSION_<PORT>_<PATH> as session cookie name. This
                    should work out-of-the-box for most setups.

    'siteidmagic': use MOIN_SESSION_<SITEID>, which is unique within a wiki farm
                   created by a single farmconfig (currently, cfg.siteid is just
                   the name of the wiki configuration module).

    'other_value': use MOIN_SESSION_other_value - this gives YOU control. Just
                   use same value to share the session between wikis and use a
                   different value, if you want a separate session.

    HINT: Please do not use cfg.cookie_path any more - it usually should not be
    needed any more, as we now always put path=/ into the cookie except if you
    explicitly configure something else (only do that if you know exactly what
    you're doing and if the default does not work for you).

    HINT: see also the HelpOnSessions page which shows some typical configs.
  * Store expiry into sessions, use moin maint cleansessions script to clean up.
    HINT: use moin ... maint cleansessions --all once after upgrading.
    HINT: you may want to add a cron job calling moin ... maint cleansessions
          to regularly cleanup expired sessions (it won't remove not expired
          sessions).

  Other changes:
  * Added rtsp, rtp, rtcp protocols to url_schemas.
  * Added more info about index building to xapian wikiconfig snippet.
  * Updated the wikicreole parser to version 1.1.


Version 1.9.0:
  Note: This is a reduced CHANGES, ommitting details from rc/beta test and
        also less interesting minor changes and fixes. It shows changes
        relative to 1.8.6 release.
        If you want to see full detail, read it there:
        http://hg.moinmo.in/moin/1.9/file/b290d938be63/docs/CHANGES

  New features: ==============================================================
  * HINT: MoinMoin requires Python 2.4 now. If you only have Python 2.3 and
    you don't want to upgrade it, please use MoinMoin 1.8.x.
  * HINT: MoinMoin is now a WSGI application.
    Please read the new install docs about how to use it, see:
    http://master19.moinmo.in/InstallDocs
    You also have a local copy of that page as docs/INSTALL.html.
  * HINT: due to big changes in the request processing and the request
    object (related to the WSGI refactoring), many 3rd party plugins might
    need code updates to work with moin 1.9.
  * HINT: We now offer different sized sets of system/help pages and the default
    underlay just contains a single page: LanguageSetup. You need to be
    superuser, visit that page and then install the language packs you like
    (minimum is the essential set for English).
  * HINT: LanguageSetup is the default page_front_page, you need to change that
    after installing language packs (see above).

  * New modular group and dict data access, you can use group and dict 
    backend modules to access group and dict data stored anywhere you like.
    Currently we provide these backends:
      * WikiGroups and WikiDicts backends get data from wikipages. They work
        similar to old wikidicts code (but with less caching issues :).
      * ConfigGroups and ConfigDicts backends get data from a dictionary
        defined in the wiki config.
      * CompositeGroups and CompositeDicts compose several backends, so data
        may be retrieved from several sources. For example, groups may be
        defined in the wiki config and on wiki pages.
    * Using cfg.groups and cfg.dicts, you can define the backend to use to
      access group and dict information (default: WikiGroups / WikiDicts
      backend).
      See the wiki/config/more_samples/ directory (groups_wikiconfig_snippet
      and dicts_wikiconfig_snippet).
    * See also the new HelpOnDictionaries and HelpOnGroups pages.

  * Improved Xapian indexing / search:
    * Moin's Xapian based search code was refactored:
      * It is now based on the xappy library (see MoinMoin.support.xappy).
      * Minimum Xapian requirement is 1.0.6 now.
      * Outdated and unmaintained xapwrap lib was removed.
      * regex search with Xapian enabled also is based on the xapian index now
    * Safe 2-stage xapian index rebuilding:
      moin index build --mode=buildnewindex  # slow, concurrent
      <stop wiki>
      moin index build --mode=usenewindex  # fast
      <start wiki>
    * Added wikiconfig snippet for xapian search.

  * Improved drawing support:
    * TWikiDraw:
      * Support code was refactored/moved to the twikidraw action.
      * Use drawing:example.tdraw to invoke it (drawing:example also still
        works for backwards compatibility)
      * Drawings are now stored as a single attachment foo.tdraw.
        We added a migration script that converts your existing drawings.
    * AnyWikiDraw:
      * Java applet added, source code see contrib/.
      * Support code for it is in anywikidraw action.
      * Use drawing:example.adraw to invoke it.
      * Drawings are stored in a similar way as foo.adraw.
    * cfg.extensions_mapping added for mapping of attachment file extensions
      to actions (currently used for anywikidraw/twikidraw action)

  * Themes / static files related:
    * Added modernized_cms theme (hides most wiki widgets from modernized if the
      user is not logged in).
    * Static file serving built-in (moved wiki/htdocs to MoinMoin/web/static/htdocs).
      MoinMoin.web.static has a static file serving wrapper that uses the files
      from htdocs subdirectory by default (docs=True).
      You can also give another path or switch off creation of that static wrapper.
      See the docstring of the static package for details.
    * Theme packages: do_copythemefile now copies theme files to
      MoinMoin/web/static/htdocs.

  * Syntax highlighting is based on the pygments library now, it does this for
    LOTS of stuff (programming languages, config files, ...) - use it like this:
    {{{#!highlight xxx
    ...
    }}}
    xxx is any of the markups pygments supports (see HelpOnParsers).
    Note: we still have some (deprecated) small wrappers around pygments,
    so the old syntax #!python/pascal/cplusplus/... still works.

  * Authentication improvements:
    * HTTP auth related (see also HelpOnAuthentication):
      * HTTPAuthMoin: http basic auth done by moin
      * HINT: auth.http.HTTPAuth is now auth.GivenAuth
        This was badly named from the beginning as for most servers, it just
        looked at REMOTE_USER environment variable and relied on the server
        doing the authentication (could be http basic auth or any other auth).
    * LDAP/AD auth: new name_callback param to create a custom wiki username (not
      the ldap login username)
    * OpenID auth:
      * Support for Simple Registration (SREG) extension.
        Basic profile fields can be copied from OpenID provider when logging in.
      * Support for Teams extension.
      * Ability to accept logins from specific OpenID providers.
        Login form changes based on configuration for better usability:
        * 0 providers: normal text input box for OpenID URL
        * 1 provider: hidden field, automatic form submission with JavaScript
        * 2+ providers: select field, uses directed identity

  * Sessions / cookies:
    * HINT: cfg.cookie_lifetime is now a tuple (anon, loggedin), giving the
      lifetime of the cookie in hours, accepting floats, for anon sessions and
      logged-in sessions. Default is (0, 12). 0 means not to use a session
      cookie (== not to establish a session) and makes only sense for anon users.
    * cfg.cookie_httponly is new and defaults to False. Please note that if you
      set it to True, TWikiDraw and similar stuff won't be able to use the session
      cookie. Thus, if your wiki page doesn't allow writing for everybody, saving
      a drawing will fail, because there is no session (== no logged in user) for
      the TWikiDraw applet's saving POSTs.

  * Macros:
    * WikiConfigHelp: added section keyword for selecting a subset of the
      description, e.g. <<WikiConfigHelp(section="xapian")>>
    * HighlighterList: show Pygments syntax highlighters (see HelpOnParsers)

  * Actions:
    * SlideShow action added (please use the "modernized" theme [default])
    * raw action mimetype support: ...?action=raw&mimetype=text/css
    * PackagePages: create package file on-the-fly in memory and send it to the
      client (do NOT create package.zip attachment)

  * Improved logging / debugging / developer support:
    * Main exception handler: include request url in log output.
    * Environment variable MOIN_DEBUGGER=off/web/external (default is "off").
    * Handle wikiserverconfig(_local) in the same way as wikiconfig(_local).

  * GUI editor: improved attachment dialog

  * "moin ... account homepage" script to create user homepages.


  Removed features: ==========================================================
  * Removed cfg.traceback_* settings (use logging configuration)
  * Removed old session code and settings:
    * Removed cfg.session_handler and session_id_handler (use cfg.session_service)
    * Removed cfg.anonymous_session_lifetime (use cfg.cookie_lifetime)


  Bug fixes: =================================================================
  * Xapian indexing:
    * Rely on xapian's locking (remove moin's additional and sometimes broken
      locking, that blocked index-rebuilds or updates sometimes).
    * Removed indexer threading.
    * Fixed (reimplemented) indexer queue.
    * Less disruptive xapian index rebuild.
  * AdvancedSearch: example didn't work, fixed

  * With the groups/dicts code rewrite, we fixed the caching problems that the
    old code (< 1.9) sometimes had.

  * Actions:
    * Abort RenamePage if renaming of main page fails (do not try to rename
      subpages).
    * AttachFile do=view: quote filename and pagename params for EmbedObject
      macro call
    * unsubscribe action: add msg types so icons get displayed

  * Parsers:
    * fixed MoinMoinBugs/LineNumbersWorkingBuggyWithHighlightParser

  * GUI editor: roundtripping works now for .pdf/doc/... attachment transclusion

  * AttachFile: added remove_attachment() and FileRemovedEvent (mail and xapian
    support, no jabber support yet).

  * Fix makeForbidden403() calls - is makeForbidden(403, ...) now.
  * sendmail: add more debug logging, check for empty recipients list
  * Fix MoinMoinBugs/MissingPageShouldn'tOfferToCreatePageForReadonlyUsers
  * Fix MoinMoinBugs/1.6XmlRpcPutPagePagenameEscape
  * Bug with "language:en" was fixed for the Moin search. Now language:
    behaves like described on HelpOnSearching.
  * Fixed MoinMoinBugs/DeprecatedIsNotRespected (search ranking, WantedPages).
  * OpenID: always return error messages with CancelLogin if OpenID process fails.
  * suid: simplify and fix, bigger selection box

  * patch werkzeug 0.5.1 to catch OverFlowError and ValueError so it doesn't
    crash when receiving invalid If-modified-since header from client.


  Other changes: =============================================================
  * 'modernized' theme:
    * use it by default (1.8 used 'modern')
    * move title_with_separators() from Modernized theme to ThemeBase
    * add a span with "pagepath" class to title_with_separators
  * add the sidebar() method from Mandarin and Gugiel themes to ThemeBase
  * updated flup to 1.0.2+ ( http://hg.saddi.com/flup-server/rev/6ea1ffac1bcb )
  * updated pygments to 1.1.1+ ( http://dev.pocoo.org/hg/pygments-main/rev/948f8885af16 )
  * updated parsedatetime to 0.8.7
  * increase surge protection limits for AttachFile to avoid trouble with image galleries
  * HINT: simplify wikiserver configuration by using same names as werkzeug's
    run_simple() call.
  * Removed moin account check's --lastsaved option, it is default now
    (checking last use with trail file did not work in 1.9 anyway).
  * ImageLink page has been killed (ImageLink macro is gone since 1.6.1).
  * Allowed disabling of timezone and language user prefs if they are
    part of the user's login fields (i.e. OpenID SREG).
  * Added option to disable local registration links and direct user
    to registration page at an OpenID provider instead.

  Developer notes: ===========================================================
  * groups and dicts API changes:
    * request.groups and request.dicts provide access to groups and dicts.
    * MoinMoin.wikidicts is gone, please use MoinMoin.datastruct.
    * LazyGroup and LazyGroupsBackend base classes for implementing backends
      which potentially deal with huge amounts of data (like a LDAP directory).
      Use MoinMoin/datastruct/backends/config_lazy_groups.py as a draft for
      new backends.
    * See http://moinmo.in/Groups2009 for more details.
  * i18n: new approach for defining sets of system/help pages (see i18n.strings).
    CheckTranslation, page packager, wikiutil.isSystemPage() use those sets.
  * killed deprecated macro.form attribute (didn't work as expected anyway due
    to WSGI refactoring) - please use macro.request.{args,form,values}


Version 1.8.8:
  Fixes:
    * Fixed XSS issues (see MoinMoinBugs/1.9.2UnescapedInputForThemeAddMsg).
    * Fixed XSS in Despam action (CVE-2010-0828).
    * wikiutil.clean_input: avoid crash if it gets str type
    * Add RenderAsDocbook to actions_excluded if we have no python-xml
    * AttachFile._build_filelist: verifies readonly flag for unzip file link
    * attachUrl: fix wrongly generated tickets (e.g. for AttachList macro)
    * MoinMoin.util.filesys.dc* (dircache can't work reliably):
      * disable usage of dircache, deprecate dc* functions
      * remove all calls to filesys.dc* (dclistdir, dcdisable)
    * Fixed crash, see MoinMoinPatch/IncludeMacroWithDocBookFormatter
    * Avoid hardly recoverable crashes if #format specification is invalid

  New features:
    * auth.ldap_login: add report_invalid_credentials param to control wrong
      credentials error message (typically used when using multiple ldap
      authenticators)


Version 1.8.7:
  Fixes:
  * Fixed major security issues in miscellaneous parts of moin.
    HINT: if you have removed superuser configuration to workaround the issue
    (following our security advisory), you may re-add it after installing this
    moin release. If you don't need superuser capabilities often, it might be
    wise to not have superusers configured all the time, though.
  * Improved package security: cfg.packagepages_actions_excluded excludes
    unsafe or otherwise questionable package actions by default now.
  * wiki parser: fixed transclusion of (e.g. video) attachments from other
    pages.
  * Fixed edit locking for non-logged in editors and cfg.log_remote_addr=False.
  * xmlrpc:
    * Process attachname in get/putAttachment similarly.
    * revertPage: convert pagename to internal representation.
  * Fixed config.umask usage for page packages.
  * Fixed usage of i18n.wikiLanguages() on class level (moved to method),
    failed when tools import the module (e.g. pydoc -k foo).
  * SubProcess: fixed win32-specific parts, fixed imports (fixes calling of
    external xapian index filters)


Version 1.8.6:
  Bug fixes:
  * Xapian indexing / indexing filters:
    * fix deadlocks with well- and misbehaving external filters
    * work around indexing run crashing when encountering encoding problems
      with non-ascii filenames
    * OpenOffice/OpenDocument filters: catch UnicodeDecodeErrors (happens
      with password protected files)
  * i18n: check if languages is not initialized yet, don't crash
  * http_redirect: use 301 redirect for some cases
  * do not use httponly session cookies, makes trouble with twikidraw and ACLs
  * GetText2 macro: fix for named placeholder
  * Fix SHA -> SSHA password hash upgrade for old user profiles.
  * abort RenamePage if renaming of main page fails (do not try to rename
    subpages)

  New features:
  * search: improve search result ordering
  * add MS Powerpoint indexing filter (needs catppt from catdoc package)
  * migration scripts: make finding damaged edit-log entries easier
  * SubscribeUser action: support username regexes and unsubscribing.
    Usage (enter this into the input form field you get after invoking
    SubscribeUser action from the "More Actions" menu:
    [+|-][re:]username[,username,...] 

    +username: subscribes user <username> (+ is optional/default)
    -username: unsubscribes user <username>
    +re:username_re: subscribes users who match <username_re> regex.
    -re:username_re: unsubscribes users who match <username_re> regex.


Version 1.8.5:
  Bug fixes:
    * Attachment links: fix processing of attributes (e.g. 'target', 'title')
    * Upgrade FCKeditor from 2.6.4 to 2.6.4.1.
    * PDF embedding: fix html, works better with PDF browser plugins now.
    * Fix typo in rightsidebar CSS.
    * Action revert: avoids reverting to a deleted current revision.
    * Action diff: enable prev/next button only in the range of given revisions.
    * Add a Auto-Submitted: auto-generated header to generated mails.
    * Include comment in email notifies.
    * mailimport: fix endless looping while trying to import a forwarded mail.
    * fuid: keep same fake_mtime for intervals of max_staleness duration.
    * Fixes a bug with empty list items in the GUI editor.
    * Improve filesys.rename compatibility code (win32).
    * Fix locking for CacheEntry.
    * Xapian indexing: catch exception when a bad zip file is encountered.
    * openidrp / botbouncer: fix param count for CancelLogin().

  New features:
    * Added CAS authentication.
    * Added httponly cookie support and use it for session cookie.

  Other changes:
    * HTTP auth: added debug logging.
    * Minor LDAP auth improvements.
    * Data browser widget:
      * Add (h)column<idx> css class to make it styleable.
      * Include only necessary autofilter options.
    * moin maint cleancache purges now drafts, too.
    * Add gopher and apt protocols to url_schemas.
    * Add .csv, .flv, .swf to MIMETYPES_MORE.


Version 1.8.4:
  Bug fixes:
    * ACL security: fix bug in hierarchical ACL processing, more restrictive
      sub page ACLs did not work if the current user name did not give a match
      within the sub page ACL (instead, the less restrictive parent page ACL
      was used).
      Non-hierarchical ACL processing (the default) is NOT affected.
    * Creole parser: fix spaces in multiline elements.
    * Use msie.css only for Internet Explorer older than version 8, fixes
      e.g. the double rendering of link icons.
    * http auth: do auth_type comparisons case-insensitively (spec-compliant)

  New features:
    * EmbedObject macro: changed default width value for PDF files to 100%
                         (use a recent Adobe Reader to make this work).
    * CopyPage action: added a TextCha for it

  Other changes:    
    * Creole parser: Add second license: BSD


Version 1.8.3:
  Bug fixes:
    * AttachFile XSS fixes: move escaping to error_msg / upload_form
    * AttachFile move: add more escaping (maybe not XSS exploitable though)
    * email attachments import with xapian indexing enabled: fix AttributeError
    * fix wrong links in attachment notifications
    * AttachFile do=view: quote filename and pagename params for EmbedObject
      macro call
    * AttachFile: fix exception when someone just clicks on upload, without
      giving a file
    * ldap_login: use None as default value for ssl certs/keys (using '' for
      the pathes lets it fail with Connect Error)
    * release edit lock if someone saves an unchanged page
    * fix sendmail.encodeAddress (do not [QP] encode blanks, do not un-
      necessarily use [QP] encoding for pure ascii mail addresses)
    * Fixed docs bug: see HINT about secrets configuration at version 1.8.0
      (1.8.0 Other changes).
    * backup action: add 'self' dummy argument for backup_exclude function
    * login action: fix formatting of error messages
    * unsubscribe action: add msg types so icons get displayed
    * fix quoting for pagehits stats (info action) - was not working for pagenames with blanks
    * macro.TableOfContents: bug fix for MoinMoinBugs/TableOfContentsIgnoresSectionNumbersPragma

  New features:
    * added modernized_cms theme
    * use url_prefix_fckeditor if you don't want to use the builtin FCKeditor
      of moin, but a separate one at some specific url
    * action.Load: added textcha feature
    * add mumble protocol (nice and good quality F/OSS VOIP conference chat sw)
    * ldap auth: new name_callback param to create a custom wiki username (not
      the ldap login username).

  Other changes:
    * add compatibility code for set to xapwrap.index (fix py 2.6 warnings)
    * wikiutil: MIMETYPES_MORE extended for .md5 as text/plain


Version 1.8.2:
  Bug fixes:
    * Fix AttachFile and antispam XSS issues.
    * Modernized, modern and rightsidebar themes: make nonexistent or
      badinterwiki links gray also when they are already visited.
    * Fix anchor parsing for interwiki links and #redirect processing
      instruction.
    * user.apply_recovery_token: key must be of type string (for Python 2.6).
    * Fix MoinMoinBugs/GuiEditorBreaksIndentedTable.
    * Fix autofilter javascript breakage caused by including a databrowser
      widget.
    * Use per-wiki i18n cache (fixes wrong links to other farm wikis).
    * Made cfg.interwikiname and cfg.user_homewiki unicode objects (str only
      worked for ascii names).
    * Xapian search: fixed historysearch.
    * Xapian search indexing:
      * Fix index updating for trivial changes.
      * With history search enabled and in update mode, do not try to re-index
        old page revisions again.
      * With history search enabled, index page attachments only once.
      * Fix last modified time of xapian index (shown on SystemInfo page).
    * Make logging handlers defined in logging.handlers work (e.g.
      class=handlers.RotatingFileHandler)
    * Jabber notifications:
      * Use an RFC compliant message type.
      * Fix user creation notifications.
    * OpenID: Compatibility fix for python-openid 2.x.x (also works with
      1.x.x), fixes crash when trying to associate moin user to OpenID.
    * Have a wikiserverconfig.py in wiki/server/ so setup.py copies it.
    * Fixed inconsistent handling of fragments / anchor IDs:
      * Fixed creole and wiki parser, other parsers might need similar fixes.
      * IDs with blanks, non-ASCII chars etc. are now sanitized in the same way
        for links as well as for link targets, so the user editing a page won't
        have to bother with it.
        E.g. [[#123 foo bar]] will link to:
        * <<Anchor(123 foo bar)>> (moin) or {{#123 foo bar}} (creole)
        * headline = 123 foo bar = (moin / creole)
        Simple rule: if the link and the target are consistent, it should work.
      * The creole wiki parser created non-human-readable sha1 heading IDs
        before 1.8.2, now it creates same (sometimes readable) heading IDs as
        the moin wiki parser.
      * TitleIndex/WordIndex now also use IDs sanitized in that way internally.
      HINT: if you manually worked around the inconsistencies/bugs before, you
            likely have to remove those workarounds now. Same thing if you used
            creole's sha1 heading IDs or IDs on TitleIndex/WordIndex.

  Other changes:
    * Updated FCKeditor to 2.6.4 (== many bug fixes in the GUI editor).
    * Enhanced privacy by a new setting: cfg.log_remote_addr (default: True),
      it controls whether moin logs the remote's IP/hostname to edit-log and
      event-log. Use log_remote_addr = False to enhance privacy.
    * Streamline attachment_drawing formatter behaviour.
    * Search results: only redirect to a single search result for titlesearch
      (fuzzy goto functionality), but not for fulltext search results.



Version 1.8.1:
  Bug fixes:
    * Workaround win32 locking problems (caused by spurious access denied
      exceptions on that platform).
    * Fix unicode errors that happened when password checker failed a password
    * WikiConfig/WikiConfigHelp: fixed wrong language table headings
    * Themes: make the margins around trail line work properly
    * "modernized" theme:
      * make broken links gray
      * add new right/center/left/justify css classes
      * don't force Arial
    * Standalone server: be more specific when catching socket exceptions,
      treat socket errors in http header emission in the same way.
    * GUI editor:
      * Fix heading levels when inserting new headings.
      * Fix headers already sent exception when using e.g. edit LOCKing.
    * Xapian indexing: fixed missing import for execfilter (only happened on
      non-posix platforms like win32)

  * New features:
    * Themes:
     * Make the TOC shrinkwrap, add white background to navigation macro.
       The table of contents looked bad spanning the whole width of the page.
       It's made to shrinkwrap now, so it will only get as wide, as the longest
       heading. We use display:inline-table, so this won't work in MS IE6,
       which still displays it the old way.
       Navigation macro now has a white background, to make it more readable
       when it's floating over a pre block or TOC.
     * Make the numbers in lists in table of contents right-aligned.
     * Refactored and extended theme.html_stylesheets() to make alternate
       stylesheets possible. Stylesheet definitions now can either be:
       2-tuples: (media, href)  # backwards compatibility
       or:
       3-tuples: (media, href, title)  # new, for defining alternate stylesheets
       This works within themes as well as in the wiki config.
       See also: http://www.w3.org/Style/Examples/007/alternatives.html


Version 1.8.0:
  Note: This is a reduced CHANGES, ommitting details from rc/beta test and
        also less interesting minor changes and fixes. It shows changes
        relative to 1.7.2 release.
        If you want to see full detail, read it there:
        http://hg.moinmo.in/moin/1.8/file/6130eab15936/docs/CHANGES

  New Features: ==============================================================
    * HINT: New "modernized" theme - if you use "modern" [default], try:
      theme_default = 'modernized'
      If you find problems with "modernized", please report them because we
      want to use it as default theme in future.
    * GUI Editor:
      * upgraded to use FCKEditor version 2.6.3
      * user can insert and modify various types of MoinMoin links
    * New plugin_dirs setting to allow multiple plugin pathes (additional to
      the automatically configured plugin_dir [default: data_dir/plugin]).
    * @EMAIL@ expands to a MailTo macro call with the obfuscated email address
      of the current user.
    * New macros "WikiConfig" and "WikiConfigHelp".
    * Per-parser quickhelp, 'quickhelp' class variable of parser class.
    * Secure session cookies for https (see cfg.cookie_secure).
    * Added left/center/right/justify css classes to builtin themes.
      Use them like:
      {{{#!wiki justify
      this content is justified....
      }}}

  Removed Features: ==========================================================
    * HINT: url_prefix setting (use url_prefix_static or just use the default)
    * traceback_log_dir setting (we just use logging.exception)
    * editor_quickhelp setting (replaced by per-parser quickhelp)
    * Restoring backups with the backup action and related settings (while
      creating backups is no big issue and should work OK, restoring them
      had fundamental issues related to overwriting or not-overwriting of
      existing files - thus we removed the "restore" part of the action and
      recommend that you just contact the wiki server admin in case of trouble,
      give him your wiki backup file and let him carefully restore it.)
    * Removed unmaintained DesktopEdition (moin 1.5.x style) and phpwiki
      migration scripts from contrib/ directory.

  Bug Fixes: =================================================================
    * GUI Editor - fixed lots of bugs.
    * Fixing https detection for servers using HTTPS=1 and also for WSGI
      servers not using HTTPS/SSL_ environment, but just wsgi.url_scheme.
    * Search results: link to 'view' rendering of found attachments.
    * Standalone server: fix serverClass and interface argument processing,
      announce used serverClass in log output.
    * mointwisted: fixed Twisted start script.
    * Logging:
      * Use logging framework for messages emitted by warnings module (e.g.
        DeprecationWarning), silence some specific warnings.
      * Removed superfluous linefeeds in timing log output.
    * Bug fix for language not installed (MoinMoinBugs/WikiLanguageNotDefined).
    * Fixed editbar hidden comment link cosmetics for sidebar themes (hide the
      complete list element).
    * MoinMoinBugs/DoubleScriptNameInSitemap (fixing urls given by sitemap
      action, if the wiki does not run in the root url of the site)
    * Fixed backup action configuration (broke on win32).
    * Fixed MoinMoinBugs/PackagesAddRevision.
    * SyncPages: add workaround for callers calling log_status with encoded
      bytestrings.
    * Fixed dbw_hide_buttons javascript.
    * HINT: Jabber bot can now be configured to use an authentication realm
      which is different from the server's hostname; the xmpp_node
      configuration parameter can now contain a full JID and the xmpp_resource
      parameter is no longer supported.

  Other Changes: =============================================================
    * HINT: new configuration for misc. secrets, please use either:
          secrets = "MySecretLooongString!" # one secret for everything
      or:
          secrets = {
              'xmlrpc/ProcessMail': 'yourmailsecret', # for mailimport
              'xmlrpc/RemoteScript': 'yourremotescriptsecret',
              'action/cache': 'yourcachesecret', # unguessable cache keys
              'wikiutil/tickets': 'yourticketsecret', # edit tickets
              'jabberbot': 'yourjabberbotsecret', # jabberbot communication
          }
      Secret strings must be at least 10 chars long.
      Note: mail_import_secret setting is gone, use
            secrets["xmlrpc/ProcessMail"] instead of it.
      Note: jabberbot secret setting is gone, use
            secrets["jabberbot"] instead of it.
    * HINT: user_autocreate setting was removed from wiki configuration and
      replaced by a autocreate=<boolean> parameter of the auth objects that
      support user profile auto creation.
    * moin import irclog: use irssi parser to format logs, mapped .irc
      extension to text/plain mimetype.
    * HINT: backup action: backup_exclude (default: "do not exclude anything")
      is now a function f(filename) that tells whether a file should be
      excluded from backup.
      You can get the old regex exclusion functionality by using:
      backup_exclude = re.compile(your_regex).search
      Be careful with your regex, you might need to use re.escape() to escape
      characters that have a special meaning in regexes (e.g.: \.[] etc.).
      If in doubt, maybe just leave backup_exclude at the default and don't
      exclude anything.
    * Speed up javascript comments processing on IE by getElementsByClassName()
    * Added sk (slovak) i18n, updated i18n.


1.7.3:
  New features:
    * Secure session cookies for https, see cfg.cookie_secure.
    * Add left/center/right/justify classes to builtin themes.

  Fixes:
    * Python 2.3 compatibility fixes.
    * Fixed https detection for servers using HTTPS=1 and also for wsgi servers
      not using HTTPS/SSL_ environment, but just wsgi.url_scheme.
    * GUI editor:
      * Fix crash when editing a page with non-ASCII pagename and inserting a link
      * Fix "headers already sent exception" with edit LOCKs.
    * i18n.__init__: Bug fix for wiki language not installed.
    * Fixed URLs given by sitemap action, if the wiki does not run at / URL.
    * Search results: link to 'view' rendering of found attachments
    * Logging:    
      * Removed superfluous linefeed in timing log output.
      * Use logging framework for messages emitted by warnings module (e.g.
        DeprecationWarning), silence some specific warnings.
    * Fix dbw_hide_buttons javascript.
    * Standalone server:
      * fix serverClass argument processing
      * fix --interface="" argument processing
    * mointwisted:
      * added missing pidFile parameter
      * better use Config.name for pidFile to avoid conflicts and keep same
        behaviour as in the past
    * Jabber bot can now be configured to use an authentication realm which
      is different from the server's hostname


Version 1.7.2:
  Fixes:
    * Fix leakage of edit-log file handles (leaked 1 file handle / request!).
    * Fix for MoinMoinBugs/SystemAdminMailAccountData (using POST and forms)
    * Wiki parser: avoid IndexError for empty #! line
    * MonthCalendar macro: fix parameter parsing / url generation
    * Xapian indexing filters (MoinMoin/filter/ or data/plugin/filter/):
      Some indexing filter scripts (e.g. for MS Word documents or PDF files)
      failed on windows because of the single-quote quoting we used (that
      works on Linux and other Posix systems). The fix introduces platform-
      dependant automatic quoting, using double-quotes on win32 and single-
      quotes on posix.
      HINT: if you use own filter plugins based on execfilter, you have to
      update them as the filename quoting (was '%s') is now done automatically
      and must not be part of the command string any more (now just use %s).
      See MoinMoin/filter/ for some up-to-date code (esp. the PDF filter).
    * Prevent CategoryTemplate being listed as a category (it is a Template,
      but matched also the category regex) - added to sample wikiconfig.
    * LDAP auth: fix processing of TLS options
    * UpdateGroup xmlrpc server side: fix wrong arg count error
    * UpdateGroup client: use multicall / auth_token, refactor code so that
      updateGroup function is reusable.
    * Improve Python 2.3 compatibility, add notes where 2.4 is required.


Version 1.7.1:
  New features:
    * New 'cache' action (see developer notes).

  Fixes:
    * Security fix: XSS fix for advanced search form
    * Avoid creation of new pagedirs with empty edit-log files by just
      accessing a non-existant page. If you used 1.7 before, you likely have
      quite some trash pagedirs now and you can clean them up by using:
      moin --config-dir=... --wiki-url=... maint cleanpage
      This will output some shell script (please review it before running!)
      that can be used to move trash pages into some trash/ directory and also
      moves deleted pages into some deleted/ directory. Maybe keep a copy of
      those directories for a while just for the case.
    * Server specific fixes:
      * standalone (wikiserver.py): fix --pidfile and --group option, fix
        operation without a wikiserverconfig.py (use builtin defaults).
      * mod_python: work around mod_python 3.3.1 problems with file uploads.
        Note: if you are still using mod_python, we strongly recommend you
	      try out mod_wsgi (in daemon mode) - it has less bugs, better
	      security, better separation, WSGI is a Python standard, and moin
	      developers also use WSGI. See HelpOnInstalling/ApacheWithModWSGI.
    * revert action: fixed for deleted pages.
    * Search:
      * Xapian indexing: Removed crappy "hostname" tokenization.
        Fixes MoinMoinBugs/1.7 XapianNotWorkingWithLeadingNumbersInTitle.
        Also tokenize CamelCase parts of non-wikiwords.
      * Make query parser reject more invalid input.
      * If query parsing raises a BracketError, at least tell what the problem
        is (and not just raise empty  ValueError).
      * Category search: ignore traling whitespace after ----
    * Argument parser:
      * Fixed sort() usage in UnitArgument to be Python 2.3 compatible.
      * Fixed MoinMoinBugs/TypeErrorInWikiutils.
    * Macros:
      * TableOfContents: skip outer-most <ol> levels when page isn't using
        the biggest headings
      * MonthCalendar: fix MoinMoinBugs/MonthCalendarBreaksOnApostrophe
    * xslt parser: fix MoinMoinBugs/DoNotConvertUnicodeToUTF8ForXsltParser
    * OpenID RP: make it compatible to python-openid 2.2.x
    * PackagePages.collectpackage: removed encoding from file name of zipfile
    * Surge protection: exclude localnet no matter whether user is known or not.
    * Notifications: fix MoinMoinBugs/DuplicateNewUserNotification
    * Script moin account create/disable/resetpw: checks for already existing
      user now.

  Other changes:
    * Prevent CategoryTemplate being listed as a category (it is a Template)
      by changing the default page_category_regex.

  Developer notes:
    * New MoinMoin.action.cache - can be used to cache expensively rendered
      output, e.g. generated images). Once put into the cache, moin can emit
      a http response for that content very fast and very efficient (including
      "304 not changed" handling.
    * New file-like API in MoinMoin.caching (good for dealing with medium
      to large files without consuming lots of memory).
    * wikiutil.importPlugin supports getting the whole plugin module object
      by giving function=None.


Version 1.7.0:
  Note: This is a reduced CHANGES, ommitting details from rc/beta test and
        also less interesting minor changes and fixes. It shows changes
        relative to 1.6.3 release.
        If you want to see full detail, read it there:
        http://hg.moinmo.in/moin/1.7/file/76265568e8d3/docs/CHANGES

  New Features: ==============================================================
    * HINT: we added generic UPDATE instructions as docs/UPDATE.html.

    * HINT: Standalone server usage changed:
      * Standalone server can now be started via the "moin" script command,
        optionally backgrounding itself.
        See: moin server standalone --help
      * In the toplevel dir, we have renamed moin.py to wikiserver.py (it was
        often confused with the moin scripting command).
        Now you have:
        * wikiserver.py - to start the standalone server
        * wikiserverconfig.py - to configure the standalone server
        * wikiserverlogging.conf - to configure logging for it (default config
          is ok for all day use, but can easily be modified for debugging)
        * wikiconfig.py - to configure the wiki engine
      * Removed old moin daemonizing script (replaced by moin server standalone
        --start/stop)
      * We now provide the "moin" script command also for people not using
        setup.py, see wiki/server/moin.

    * Logging
      * New powerful and flexible logging, please see wiki/config/logging/ -
        HINT: you have to upgrade your server adaptor script (e.g. moin.cgi)
        and load a logging configuration that fits your needs from there, or
        alternatively you can also set MOINLOGGINGCONF environment variable
        to point at your logging config file.
        If you use some of our sample logging configs, make sure you have a
        look INTO them to fix e.g. the path of the logfile it will use.
      * Moin now logs the path from where it loaded its configuration(s).

    * Authentication / Sessions:
      * HINT: New authentication plugin system, see HelpOnAuthentication. If
        you do not use the builtin default for 'auth' list, you likely have to
        change your configuration. See wiki/config/snippets/ for some samples.
      * HINT: New session handling system (no moin_session any more, now done
        internally and automatically), see HelpOnSessions for details.
      * Added OpenID client and server support.
        See: HelpOnAuthentication and HelpOnOpenIDProvider.
      * cfg.trusted_auth_methods is a list of auth methods that put an
        authenticated user into the "Trusted" ACL group.

    * User profiles / password recovery / notification:
      * New newacount action for creating new user accounts/profiles. If you
        don't want users creating new accounts on their own, you can add this
        action to actions_excluded list.
      * New recoverpass action for password recovery:
        If you forgot your password, recoverpass sends you an email with a
        password recovery token (NOT the encrypted password) that is valid
        for 12 hours.
      * New moin account resetpw script for resetting a user's password by
        the wiki admin.
      * New preferences plugin system, see MoinMoin/userprefs/__init__.py.
      * New notification system with an optional jabber notification bot, see
        HelpOnNotification. HINT: wiki users have to check their notification
        settings, esp. if they want to receive trivial update notifications.

    * The diff action now has navigation buttons for prev/next change and also
      a revert button to revert to the revision shown below the diff display.
    * ThemeBase: support Universal Edit Button, see there for details:
      http://universaleditbutton.org/
    * ?action=info&max_count=42 - show the last 42 history entries of the page.
      max_count has a default of default_count and a upper limit of
      limit_max_count - you can configure both in your wiki config:
      cfg.history_count = (100, 200) # (default_count, limit_max_count) default
    * The CSV parser can sniff the delimiter from the first CSV line so other
      delimeters than ";" can be used.
    * Admonition support. Added styling for tip, note, important, warning 
      and caution in the modern theme. For more info see HelpOnAdmonitions.
    * DocBook-formatter:
      * supports HTML entities like &rarr; and &#9731;
      * supports the FootNote macro
      * supports bulletless lists
      * support for admonitions
      * will export the wiki page's edit history as the generated article's
        revision history. Doesn't add history of included pages.
      * supports for the MoinMoin comment element, though only inline comments
        are likely to be valid since the DocBook remark is an inline element.
    * New Hits macro: shows the total hits for the page it is used on.

  Removed Features: ==========================================================
    * HINT: Removed attachments direct serving (cfg.attachments - this was
            deprecated since long!). Use AttachFile action to serve attachments.
    * Duplicated file attachment upload code was removed from Load action (just
      use AttachFile action to deal with attachments).
    * Removed 'test' action. If you like to run unit tests, use py.test.
    * Removed Login macro.

  Bug Fixes: =================================================================
    * Better handling of ImportErrors (farmconfig, macros, wikiserverconfig).
    * Fix failure of detection of on-disk cache updates.
    * Fix traceback in filesys.py on Mac OS X when "import Carbon" fails.

    * AttachFile action / file up- and download / zip support:
      * WSGI: use wsgi.file_wrapper (or a builtin simple wrapper). Fixes memory
        consumption for sending of large file attachments.
      * FastCGI: flush often. Fixes memory consumption for sending of large
        file attachments.
      * Use the open temporary file for receiving file attachment uploads
        (fixes big memory consumption for large file uploads).
      * Catch runtime errors raised by zipfile stdlib modules when trying to
        process a defective zip.
      * When unzipping member files, decode their filenames from utf-8 and
        replace invalid chars.
      * Make error msg less confusing when trying to overwrite a file attachment
        without having 'delete' rights.

    * HINT: page_*_regex processing had to be changed to fix category search.
      If you don't use the builtin (english) defaults, you will have to change
      your configuration:
        old (default): page_category_regex = u'^Category[A-Z]'
        new (default): page_category_regex = ur'(?P<all>Category(?P<key>\S+))'
      As you see, the old regex did work for detecting whether a pagename is
      a category, but it could not be used to search for a category tag in the
      page text. The new regex can be used for both and identifies the complete
      category tag (match in group 'all', e.g. "CategoryFoo") as well as the
      category key (match in group 'key', e.g. "Foo") by using named regex
      groups. \S+ means the category key can be anything non-blank.
      If you like to simultaneously support multiple languages, use something
      like this: ur'(?P<all>(Kategorie|Category)(?P<key>\S+))'
      HINT: after changing your configuration, please rebuild the cache:
        * stop moin
        * moin ... maint cleancache
        * start moin
      If you don't do this, your groups / dicts will stop working (and also
      your ACLs that use those groups). You better do a test whether it works.

    * Xapian search / indexing / stemming:
      * Use text/<format> as mimetype for pages.
      * Index also major and minor for mimetypes, so it will find 'text' or
        'plain' as well as 'text/plain'
      * Fix searching for negative terms.
      * Improve result list ordering.
      * Index filters: redirect stderr to logging system.
      * Remove crappy num regex from WikiAnalyzer, improve tokenization.
      * Fix AttributeError that happened when trying to access an attribute only
        used with xapian search (but regex search is not done by xapian)
      * Fix IndexErrors happening when pages are renamed/nuked after the index
        was built.
      * Fixed indexing of WikiWords (index "WikiWords", "Wiki" and "Words").
      * Fix crash if default language is un-stemmable.
      * xapian_stemming: removed some strange code (fixes search
        title:lowercaseword with xapian_stemming enabled)
      * Fixed category indexing (index CategoryFoo correctly as CategoryFoo, not
        Foo - for all languages, see page_*_regex change above).
    * Builtin search: support mimetype: search for pages for the builtin search
      engine (using text/<format>).

    * Parser fixes:
      * Wiki: fix subscript parsing (was broken for cases like 'a,,1,2,,').
      * Docbook: fixed detection of WikiWords.
      * All: Add ssh protocol to url_schemas for ssh:... URLs.

    * XMLRPC:
      * Fix xmlrpc request.read() call to use content-length, if available,
        fixes hangs with wsgiref server.
      * Wiki xmlrpc getPageInfoVersion() fixed:
        * works correctly now for old page versions (was unsupported)
        * works correctly now for current page version (reported wrong
          data when a page had attachment uploads after the last page
          edit)
        * returns a Fault if it did not find a edit-log entry

  Other Changes: =============================================================
    * Using better ACLs and comments on system/help pages now, just taking
      away 'write' permission, but using default ACLs for everything else.
    * HINT: If you want to use xapian based indexed search, you need to have
      Xapian >= 1.0.0 (and you can remove PyStemmer in case you have installed
      it just for moin - we now use the stemmer built into Xapian as it
      supports utf-8 since 1.0.0).
    * Changed default value of cfg.search_results_per_page to 25.
    * Surge Protection: If a user is authenticated by a trusted authentication
      (see also cfg.auth_methods_trusted) then he/she won't trigger surge
      protection, but moin will just log a INFO level log msg with the user's
      name so you can find the culprit in case he/she is overusing ressources.
    * HINT: Added MyPages and CopyPage to actions_excluded because MyPages
      doesn't work without special SecurityPolicy anyway and CopyPage has
      questionable behaviour.
    * Load action now just creates a new revision of the target page, the
      target pagename defaults to the current page name and can be edited.
      If the target pagename is empty, moin tries to derive the target pagename
      from the uploaded file's name.
      Load tries to decode the file contents first using utf-8 coding and, if
      that fails, it forces decoding using iso-8859-1 coding (and replacing
      invalid characters).
    * HINT: cfg.show_login is gone, see code in theme/__init__.py, this may
      affect many themes!
    * HINT: a new userprefs/ plugin directory will be created by the usual
      "moin migration data" command.
    * DocBook-formatter:
      * generates a valid DOCTYPE
      * table support has been improved
      * handling of definitions and glossaries is more robust
      * supports program language and line numbering in code areas
    * HINT: ldap_login behaves a bit different now:
      In previous moin versions, ldap_login tended to either successfully
      authenticate a user or to completely cancel the whole login process in
      any other case (including ldap server down or exceptions happening).
      This made subsequent auth list entries rather pointless.
      Now it behaves like this:
        * user not found in LDAP -> give subsequent auth list entries a
          chance to authenticate the user (same happens if it finds multiple
          LDAP entries when searching - it logs an additional warning then).
        * user found, but wrong password -> cancel login
        * ldap server not reachable or other exceptions -> give subsequent
          auth list entries a chance
      So please make sure that you really trust every auth list entry you have
      configured when upgrading or it might maybe change behaviour in a
      unexpected or unwanted way.
    * ldap_login now supports failover: if it can't contact your LDAP server
      (e.g. because it is down or unreachable), it will just continue and
      try to authenticate with other authenticators (if there are any in
      cfg.auth list). So if you have some mirroring LDAP backup server, just
      put another authenticator querying it there:
          ldap_auth1 = LDAPAuth(server_uri='ldap://mainserver', ...)
          ldap_auth2 = LDAPAuth(server_uri='ldap://backupserver', ...)
          auth = [ldap_auth1, ldap_auth2, ]

  Developer notes: ===========================================================
    * Page.last_edit() is DEPRECATED, please use Page.edit_info().
    * Page._last_edited() is GONE (was broken anyway), please use
      Page.editlog_entry().
    * New request.send_file() call, making it possible to use server-specific
      optimizations.
    * getText's (aka _()) 'formatted' keyword param (default: True in 1.6 and
      early 1.7) was renamed/changed: it is now called 'wiki' and defaults to
      False. Example calls:
      _('This will NOT get parsed/formatted by MoinMoin!')
      _('This will be parsed/formatted by MoinMoin!', wiki=True)
      _('This will be used as a left side of percent operator. %s',
        wiki=True, percent=True)
    * Page.url 'relative' keyword param (default: True in 1.6 and early 1.7)
      was changed to default False).
    * The themedict no longer contains 'page_user_prefs' and 'user_prefs',
      this may affect custom themes.
    * The rst-parser's admonition class names are no longer prepended with
      "admonition_". Instead the class names are now for example "note"
      and not "admonition_note".


Version 1.6.3:
  Fixes:
    * Security fix: a check in the user form processing was not working as
      expected, leading to a major ACL and superuser priviledge escalation
      problem. If you use ACL entries other than "Known:" or "All:" and/or
      a non-empty superuser list, you need to urgently install this upgrade.
    * Security fix: if acl_hierarchic=True was used (False is the default),
      ACL processing was wrong for some cases, see
      MoinMoinBugs/AclHierarchicPageAclSupercededByAclRightsAfter
    * For {{transclusion_targets}} we checked the protocol to be http(s),
      this check was removed (because file: and ftp: should work also) and
      it's not moin's problem if the user uses silly protocols that can't
      work for that purpose.
    * Fixed TableOfContents macro for included pages.
    * server_fastcgi: added Config.port = None. If you want to use some port
      (not a fd), you can set it now in your Config, e.g. port = 8888.
    * category: search matches categories even if there are comment lines
      between the horizontal rule and the real categories, e.g.:
      ... some page text ...
      ----
      ## optionally some comments, e.g. about possible categories:
      ## CategoryJustACommentNotFound
      CategoryTheRealAndOnly

      Note: there might be multiple comment lines, but all real categories
            must be on a single line either directly below the ---- or
            directly below some comment lines.
  
  Other changes:
    * Added 'notes' to config.url_schemas, so you can use notes://notessrv/...
      to invoke your Lotus Notes client.
    * After creating a new user profile via UserPreferences, you are logged
      in with that user (no need to immediately enter the same name/password
      again for logging in).


Version 1.6.2:
  Fixes:
    * Security fix: check the ACL of the included page for the rst parser's
      include directive.
    * Potential security/DOS fix: we removed cracklib / python-crack support
      in password_checker as it is not thread-safe and caused segmentation
      faults (leading to server error 500 because the moin process died).
    * Fix moin_session code for auth methods other than moin_login (e.g. http).
      If you have worked around this using moin_anon_session, you can remove
      this workaround now (except if you want anon sessions for other reasons).
    * Fix moin_session code to delete invalid session cookies and also create
      a new session cookie if it got a valid user_obj at the same time.
    * Fix xmlrpc applyAuthToken: give good error msg for empty token.
    * Fixed category search, use category:CategoryFoo as search term.
    * xapian_stemming = False (changed default) to workaround some problems
      in the code enabled by it. Fixes the problems when searching for
      lowercase or numeric titles or word fragments with the builtin search.
    * Fix trail for anon users without a session, do not show a single page.
    * Fix MoinMoinBugs/WikiSyncComplainsAboutTooOldMoin.
    * Wiki parser: fixed strange insertion of unwanted paragraphs.
    * Wiki parser: fix interwiki linking:
      Free interwiki links did not change since 1.5 (they still require to match
      [A-Z][A-Za-z]+ for the wikiname part, i.e. a ASCII word beginning with an
      uppercase letter).
      Bracketed interwiki links now behave similar to how they worked in 1.5:
      Moin just splits off the part left of the colon - no matter how it looks
      like. It then tries to find that in the interwiki map. If it is found,
      a interwiki link gets rendered. If it is not found, moin will render a
      link to a local wiki page (that has a colon in the pagename). It will
      also render a local wiki page link if there is no colon at all, of course.
      Examples:
      [[lowercasewikiname:somepage]] does an interwiki link (if in the map).
      [[ABC:n]] does a local link to page ABC:n (if ABC is NOT in the map).
    * Wiki parser: fix interwiki linking for the case that there are query args
      in the interwiki map entry and you give additional query args via link
      markup (uses correct query arg separator now), e.g.:
      [[Google:searchterm|search this|&foo=bar]]
    * Creole parser: fixed bug that prevents images inside links.
    * Python parser: catch indentation error.
    * PageEditor: fixed copyPage for write restricted pages.
    * GUI editor: fixed javascript error with too complex word_rule regex,
      see MoinMoinBugs/GuiEditorSyntaxError.
    * Fixed FCKeditor dialog boxes for FireFox3.
    * NewPage macro/newpage action: fixed for non-ascii template pagenames.
    * FootNote macro: Fix MoinMoinBugs/FootNoteNumbering.
    * EmbedObject macro: bug fix for image mimetype
    * WSGI:
      * fix TWikiDraw saving a drawing by also evaluating the query args.
      * work around unpythonic WSGI 1.0 read() API, fixing broken xmlrpc
        putPage with mod_wsgi
    * Fix highlighting (see MoinMoinBugs/SearchForPagesWithComments).
    * Fix logfile code for EACCESS errors.
    * Removed the "logging initialized" log messages because it was issued once
      per request for CGI.

  Other changes:
    * Show "Comments" toggling link in edit bar only if the page really
      contains comments.
    * Made default configuration of surge protection a bit more forgiving,
      especially for edit action which is currently also used for previews.
    * Updated i18n, system/help pages, added Macedonian system text translation.
    * Improved moin xmlrpc write command's builtin docs and auto-append
      ?action=xmlrpc2 to the target wiki url given.


Version 1.6.1:
  New features:
    * Improved params for [[target|label|params]]:
      Added accesskey link tag attribute, e.g.: [[target|label|accesskey=1]].
      Additionally to specifying link tag attributes (like class=foo), you can
      now also specify &key=value for getting that into the query string of
      the link URL.
      The "&" character is important, don't forget it or it won't get into the
      query string!
      E.g. for an attachment, you can use:
      [[attachment:foo.pdf|Direct download of foo.pdf|&do=get]]
      E.g. for linking to some specific diff, you can use:
      [[SomePage|see that diff|&action=diff,&rev1=23,&rev2=42]]
      See also the updated HelpOnLinking page!
    * AdvancedSearch: make multipe categories/languages/mimetype selections possible
    * Added a configuration directive to only do one bind to the LDAP server.
      This is useful if you bind as the user the first time.
      ldap_bindonce = False # default

  Fixes:
    * Fix XSS issue in login action.
    * Fix wrong pagename when creating new pages on Mac OS X - that was a big
      showstopper for moin 1.6.0 on Mac OS X.
    * Fixed 1.6 migration script:
      Make sorting python 2.3 compatible.
      Just skip corrupted event log lines.
      Fix link conversion by using data.pre160 as data_dir.
      Fix bad /InterWiki pagenames when encountering interwiki links with bad
      wiki names.
      Improve ImageLink conversion by using its argument parser code.
      Added STONEAGE_IMAGELINK (default: False) switch to wiki markup converter,
      toggle it if you had a very old ImageLink macro in production and the
      converter output has target and image interchanged.
      Fixed UnicodeDecodeError for wrongly encoded attachment filenames.
    * Wiki parser:
      Fix parsing of link/transclusion description and params.
      Fix relative attachment targets.
      Fix supported URL schemes (some got lost since 1.5.8).
      Showing an upload link for non-existing non-text/non-image transclusions
      now (like e.g. *.pdf).
    * RST parser: fix attachment: and drawing: processing
    * Fix quickhelp when editing RST markup pages.
    * Fix Despam action: editor grouping was broken, increase time interval
      to 30 days.
    * Fix AdvancedSearch domain:system search crashing.
    * Only switch off xapian search if we didn't use it because of missing index.
    * Fix saving twikidraw drawings by removing 'java' from spider regex.
    * Fix classic theme's unsubscribe icon's action link.
    * Fix AttachFile action: don't show unzip for packages, only show install
      for superuser.
    * Fix "su user" troubles on UserPreferences.
    * Removed unit tests from ?action=test (due to changes in our test
      environment, using py.test now, this was broken).
    * Duplicated the top directories' moin.py to wiki/server/moin.py so it gets
      installed by setup.py.
    * Fix MoinMoinBugs/1.6.0LanguageIgnoreBrowserConfigurationError
    * Fix MoinMoinBugs/MoveAttachmentNotWorkingWithModPython
    * Fix MoinMoinBugs/1.6.0SupplementationAndAccessRights
    * Fix MoinMoinBugs/RenamingUserAllowsOldUsernameToLogin
    * Fix MoinMoinBugs/GuiEditorExcelPasteExpatErrorUnboundPrefix

  Other changes:
    * I18n texts, system and help pages updated, please update your underlay
      directory (see wiki/underlay/...).
    * Improved "moin" script help, invoke it with "moin ... package command --help".
    * Added some .ext -> mimetype mappings missing on some systems (like Mac OS X).
    * Removed ImageLink macro, as this can be easily done with moin wiki link
      syntax now - see HelpOnMacros/ImageLink (the 1.6 migration scripts convert
      all ImageLink calls to moin wiki link syntax).
    * Updated EmbedObject macro.


Version 1.6.0:
 * This is a reduced CHANGES, ommitting details from rc/beta test and also
   less interesting minor changes and fixes. If you want to see full detail,
   read it there: http://hg.moinmo.in/moin/1.6/file/640f21787334/docs/CHANGES

   It took MoinMoin development a lot of work and time to implement all the new
   and fixed stuff, so please, before asking for support:
   * take the time to read all the stuff below
   * read the new help pages (copy them from wiki/underlay/ directory)

 * HINT: If you are upgrading from a older moin version and want to keep your
   existing data directory, it is essential that you read and follow
   README.migration because the wiki markup and user profiles changed significantly.
   See also more HINTs below...

  New features: ==============================================================

  User interface: ------------------------------------------------------------
    * Removed "underscore in URL" == "blank in pagename magic" - it made more
      trouble than it was worth. If you still want to have a _ in URL, just
      put a _ into pagename.
    * Discussion pages, see FeatureRequests/DiscussionAndOrCommentPages.
    * cfg.password_checker (default: use some simple builtin checks for too
      easy passwords and, if available, python-crack).
      Use password_checker = None to disable password checking.
    * We now have a drafts functionality (no */MoinEditorBackup pages any
      more):
      * If you edit a page and cancel the edit, use preview or save, a draft
        copy gets saved for you to a internal cache area (data/cache/drafts/).
      * If it is a save what you did and it succeeds, the draft copy gets
        killed right afterwards.
      * If you accidentally used cancel or your browser or machine crashes
        after you used preview, then just visit that page again and edit it.
        the editor will notify you that there is a draft of this page and you
        will see a "Load draft" button. Click on it to load the draft into the
        editor and save the page.
      * The draft storage is per user and per page, but only one draft per page.
    * cfg.quicklinks_default and cfg.subscribed_pages_default can be used to
      preload new user profiles with configurable values.
    * attachment links for non-existing attachments look different now:
      the note about the non-existing attachment moved to the link title,
      the link is shown with nonexistent class (grey).
    * attachment embeddings for non-existing attachments show a grey clip
    * The list of InterWiki sites is editable in the wiki (page InterWikiMap),
      it is getting reloaded every minute.
    * We support some new languages and also have new underlay pages, thanks
      to all translators and people helping with the docs!

  Actions: -------------------------------------------------------------------
    * Synchronisation of wikis using the SyncPages action.
    * Xapian (see http://xapian.org/) based indexed search code.
      To use this:
      * Install xapian-core and xapian-bindings on your machine.
        We used 0.9.4, but newer code should hopefully work, too.
      * cfg.xapian_search = True
      * Execute this to build the index:
        $ moin ... index build   # indexes pages and attachments
        $ moin ... index build --files=files.lst  # same plus a list of files
        You should run those commands as the same user you use for your wiki,
        usually this is the webserver userid, e.g.:
        $ sudo -u www-data moin --config=... --wiki-url=wiki.example.org/ \
               index build --files=files.lst
    * New searches:
        - LanguageSearch: language:de
        - CategorySearch: category:Homepage
        - MimetypeSearch: mimetype:image/png (for attachments/files)
        - DomainSearch: domain:underlay or domain:standard
        - History Search: available in advanced ui
      Note: Some currently only available when Xapian is used.
    * New config options and their defaults:
        xapian_search        False  enables xapian-powered search
        xapian_index_dir     None   directory for xapian indices
                                    (can be shared for wiki farms)
        xapian_stemming      True   toggles usage of stemmer, fallback
                                    to False if no stemmer installed
        search_results_per_page 10  determines how many hits should be
                                    shown on a fullsearch action
        xapian_index_history False  indexes all revisions of pages to
                                    allow searching in their history
    * Speeded up linkto search by avoiding read locks on the pagelinks file.

    * The action menu now calls the actions for the revision of the page you
      are currently viewing. If you are viewing the current page revision, you
      get the same behaviour as in moin 1.5, but if you are viewing an old
      page revision, action "raw" will now show you the raw text of this OLD
      revision (not of the current revision as moin 1.5 did it).
      Note that not every action does evaluate the rev=XX parameter it gets.
      Also please note that the edit, info, ... links in the editbar do NOT
      use the rev parameter, but operate on the latest page revision (as
      they did in moin 1.5).
    * Info action lost the links for "raw", "print" and "revert" actions,
      because you can now just view an old revision and select those actions
      from the menu there.
    
    * ?action=sitemap emits a google sitemap (XML), listing all your wiki pages
      and the wiki root URL.
      Page                      Priority / Frequency / Last modification
      --------------------------------------------------------------------
      /                         1.0 / hourly / <now>
      cfg.page_front_page       1.0 / hourly / page last edit
      TitleIndex,RecentChanges  0.9 / hourly / <now>
      content pages             0.5 / daily / page last edit
      system/help pages         0.1 / yearly / page last edit

    * Action DeletePage and RenamePage can now be used for subpages of a page, too.
    * Added Action CopyPage so you can use now an existing page or page hierarchy
      as template for a new page, see FeatureRequests/CloneOrCopyPages.
    * "Package Pages" action supports attachments now.
    * Added SisterPages support:
      * action=sisterpages will generate a list of url pagename lines for all
        pages in your moin wiki.
      * action=pollsistersites will poll all sister sites listed in
        cfg.sistersites = [(wikiname, fetchURL), ...]
        The fetch URL for the sistersites depends on the wiki engine, e.g.:
        # moin based wiki:
        ('MoinExample', 'http://moin.example.org/?action=sisterpages')
        # oddmuse based wiki:
        ('EmacsWiki', 'http://www.emacswiki.org/cgi-bin/test?action=sisterpages')
        # JspWiki based wiki:
        ('JspWiki', 'http://www.jspwiki.org/SisterSites.jsp')
      * If the current page exists on some sister wiki, a link to it will be
        added to the navibar.
      You can use sister wikis for adding another dimension to your wiki UI: use
      it for simple multi language support, or for comments, or anything else
      "related" you need.
      TODO: add sistersites_force with sister sites we link to even if they do not
            have the page yet (will work only for moin as we don't know
            pagename>url transformation of other wikis)
    * showtags action that lists all tags related to a page.
    * action=view does use mimetypes of EmbedObject too and text files will be shown
      by using their colorized parsers

  Macros: --------------------------------------------------------------------
    * RecentChanges:
      * If a change has happened after your bookmark, the updated/new/renamed
        icon links to the bookmark diff.
      * If a page does not exist any more (because it was deleted or renamed),
        we link the deleted icon to the diff showing what was deleted (for the
        delete action). For the rename action, we just show the deleted icon.
    * Conflict icon in RecentChanges is shown if a edit conflict is detected.
    * Enhanced SystemAdmin's user browser, so a SuperUser can enable/disable
      users from there.
    * Included EmbedObject macro for embedding different major mimetypes:
      application, audio, image, video, chemical, x-world. 
      You are able to change the defaults of allowed mimetypes in the config
      var mimetypes_embed. The config var mimetypes_xss_protect is used to deny
      mimetypes. The order of both variables is Allow, Deny (mimetypes_embed,
      mimetypes_xss_protect).
    * Added support for @SELF to the NewPage macro.
    * GetText2 macro that allows to translate messages that contain data.
    * Make the FootNote macro filter duplicates and display a list of numbers
      instead of a list of identical footnotes. Thanks to Johannes Berg for the
      patch.

  Parsers: -------------------------------------------------------------------
    * Moin Wiki parser: Changed markup for links, images and macros, see these
      wiki pages: HelpOnLinking, HelpOnMacros
    * New wiki markup for /* inline comments */ - they get rendered as a span
      with class="comment", see next item:
    * There is a new item in the edit bar: "Comments". If you click it, the
      visibility of all class "comment" tags will be toggled. There is a user
      preferences item "show_comments" to set if the default view shows them or not.
    * The wiki parser can be used with css classes now:
      {{{#!wiki comment
      This will render output within a div with class "comment".
      You can use any wiki markup as usual.
      }}}
      You can also combine multiple css classes like this:
      {{{#!wiki red/dotted/comment
      This will render a red background, dotted border comment section.
      }}}
      The same thing will work for any other css classes you have.
      If the css classes contain the word "comment", they will trigger some
      special feature, see next item:
    * Wiki nested parser/pre sections work now, using this syntax:
      a) just use more curly braces if you have 3 closing in your content:
         {{{{
         }}} <- does not terminate the section!
         }}}}
      b) use {{{ + some magic string:
         {{{somemagicstring
         }}} <- does not terminate the section!
         somemagicstring}}}
      c) {{{whatever#!python
         # py code
         whatever}}}
      Pitfall: stuff like below does not work as it did in 1.5:
         {{{aaa
         bbb}}}
      Solution:
         {{{
         aaa
         bbb
         }}}
    * Added support for ircs: URLs (secure IRC).
    * New text/creole parser that allows you to use WikiCreole 1.0 markup,
      use #format creole.
    * HTML parser (called "html") that allows you to use HTML on the page.
      Thanks to the trac team for the nice code.
    * Added the diff parser from ParserMarket, thanks to Emilio Lopes, Fabien
      Ninoles and Juergen Hermann.

  XMLRPC: --------------------------------------------------------------------
    * actions_excluded now defaults to ['xmlrpc'] - this kind of disables the
      built-in wiki xmlrpc server code (not completely: it will just answer
      with a Fault instance for any request). If you want to use xmlrpc v1 or
      v2, you have to remove 'xmlrpc' from the actions_excluded list (for
      example if you want to use wikisync, mailimport or any other feature
      using xmlrpc). If you enable xmlrpc, it will be possible that someone
      changes your wiki content by using xmlrpc (it will of course honour ACLs).
    * New XMLRPC methods (see doc strings for details):
      * getMoinVersion
      * system.multicall -- multicall support
      * Authentication System: getAuthToken/appyAuthToken
      * getDiff -- method to get binary diffs
      * mergeDiff -- method to local changes remotely
      * interwikiName -- method to get the IWID and the interwiki moniker
      * getAllPagesEx -- method to get the pagelist in a special way (revnos,
        no system pages etc.)
      * getAuthToken -- make and authentication token by supplying username/password
      * applyAuthToken -- set request.user for following xmlrpc calls (within the
                          same multicall)
      * getUserProfile -- method to get user profile data for request.user
    * Added XMLRPC methods for attachment handling. Thanks to Matthew Gilbert.
    * XMLRPC putPage method adjusted to new AuthToken, config vars 
      xmlrpc_putpage_enabled and xmlrpc_putpage_trusted_only removed.

  Scripts / Commandline interface: -------------------------------------------
    * moin export dump now better conforms to the theme guidelines.
    * Added a --dump-user option to the moin export dump command.
      Thanks to Oliver O'Halloran.

  Security / Auth / AntiSpam / etc.: -----------------------------------------
    * Hierarchical ACLs are now supported, i.e. pages inheriting permissions
      from higher-level pages. See HelpOnAccessControlLists.
    * If you have "#acl" (without the quotes) on a page, this means now:
      "this page has own (empty) ACLs, so do not use acl_rights_default here"
      Please note that this is COMPLETELY DIFFERENT from having no ACL line at
      all on the page (acl_rights_default is used in that case).
    * Antispam master url is now configurable via cfg.antispam_master_url.
      The default is to fetch the antispam patterns from MoinMaster wiki.
    * Antispam now checks the edit comments against BadContent also.
    * TextCHAs (text-form CAPTCHAs).
      Due to increasingly annoying wiki spammers, we added the option to use
      TextCHAs (for page save (not for preview!), for attachment upload, for
      user creation (not for profile save)).
      This function is disabled by default. If you run a wiki that is editable
      by anonymous or non-approved users from the internet (i.e. All: or Known:
      in ACL terms), you should enable it in your wiki config by:
      textchas = { # DO NOT USE EXACTLY THESE QUESTIONS!!!
          'en': {
              u'H2O is ...': u'water', # bad: too common
              u'2 apples and three bananas makes how many fruits?': ur'(five|5)', # good
              u'2 apples and three pigs makes how many fruits?': ur'(two|2)', # good
              u'2+3': ur'5', # bad: computable
              u'
          },
          'de': { # for german users
              u'H2O ist ...': u'wasser',
          },
      }
      This means that english users will get some random question from the 'en'
      set, german users will get some from the 'de' set. If there is no 'de'
      set configured, moin will fallback to language_default and then to 'en',
      so make sure that you at least have a 'en' set configured (or whatever
      you have set as language_default).
      You need to use unicode for the questions and answers (see that u"...").
      For the answer, you need to give a regular expression:
      * In the easiest case, this is just some word or sentence (first en
        example). It will be matched in a case-insensitive way.
      * For more complex stuff, you can use the power of regular expressions,
        e.g. if multiple answers are correct (second en example). Any answer
        matching the regular expression will be considered as correct, any
        non-matching answer will be considered as incorrect.

      Tipps for making it hard to break for the spammers and easy for the users:
      * Use site-specific (not too common) questions.
      * Don't use too hard questions (annoys legitimate users).
      * Don't use computable questions.
      * Don't reuse textchas from other sites.

      textchas_disabled_group = None # (default)
      Set this to some group name and noone in this group will get textchas.
      E.g.: textchas_disabled_group = u'NoTextChasGroup'

    * The login page gives now the possibility to recover a lost password, thanks to 
      Oliver Siemoneit. This is especially useful for wikis where access to user 
      preferences is restricted by acl.
    * Session handling for logged-in users and (not by default due to expiry
      problems) anonymous users.
    * Updated the ldap_login code from 1.5 branch, supports TLS now.
      See MoinMoin/config/multiconfig.py for supported configuration options
      and their defaults (and please just change what you need to change,
      in your wikiconfig).
    * Interwiki auth: You need to define cfg.trusted_wikis and
       cfg.user_autocreate to use it. Logging in works by entering:
      Name: RemoteWikiName RemoteUserName
      Password: remotepass
      Then moin contacts RemoteWikiName after looking it up in the interwiki
      map and tries to authenticate there using RemoteUserName and remotepass.
      If it succeeds, the remote wiki will return the remote user profile items
      and your local moin will autocreate an account with these values.

  Server / Network / Logging: ------------------------------------------------
    * The standalone server script moved to the toplevel directory. This makes
      it possible to directly start moin.py without additional configuration
      to run a MoinMoin DesktopEdition like wiki setup.
      Be careful: DesktopEdition uses relaxed security settings only suitable
      for personal and local use.
    * Added TLS/SSL support to the standalone server. Thanks to Matthew Gilbert.
      To use TLS/SSL support you must also install the TLSLite library
      (http://trevp.net/tlslite/). Version 0.3.8 was used for development and
      testing.

    * cfg.log_reverse_dns_lookups [default: True] - you can set this to False
      if rev. dns lookups are broken in your network (leading to long delays
      on page saves). With False, edit-log will only contain IP, not hostname.
    * Added support for "304 not modified" response header for AttachFile get
      and rss_rc actions - faster, less traffic, less load.

    * Added logging framework, using stdlib's "logging" module. Just do
      import logging ; logging.debug("your text"). Depending on configuration
      in the server Config class, your stuff will be written to screen (stderr),
      to a moin logfile, to apache's error.log, etc.:
      logPath = None # 'moin.log'
      loglevel_file = None # logging.DEBUG/INFO/WARNING/ERROR/CRITICAL
      loglevel_stderr = None # logging.DEBUG/INFO/WARNING/ERROR/CRITICAL
      NOTE: this is NOT in wikiconfig, but e.g. in moin.cgi or moin.py or ...

    * Added some experimental and disabled code, that uses x-forwarded-for
      header (if present) to get the right "outside" IP before a request
      enters our chain of trusted (reverse) proxies.
      This code has the problem that we can't configure it in wikiconfig, so
      if you want to use it / test it, you have to edit the moin code:
      MoinMoin/request/__init__.py - edit proxies_trusted (near the top).
      We will try to make this easier to configure, but there was no time left
      before 1.6.0 release for doing bigger code refactorings needed for that.

  Mail: ----------------------------------------------------------------------
    * You can send email to the wiki now (requires xmlrpc), see:
      FeatureRequests/WikiEmailIntegration, HelpOnConfiguration/EmailSupport

    * Mail notifications contain a link to the diff action so the user
      can see the coloured difference more easily. Thanks to Tobias Polzin.

  Other changes: =============================================================
    * HINT: please copy a new version of your server script from the wiki/server/
      directory and edit it to match your setup.
    * HINT: instead of "from MoinMoin.multiconfig import DefaultConfig" you
      need to use "from MoinMoin.config.multiconfig import DefaultConfig" now.
      You need to change this in your wikiconfig.py or farmconfig.py file.
      See MoinMoin/multiconfig.py for an alternative way if you can't do that.
    * HINT: you need to change some imports (if you have them in your config):
      Old: from MoinMoin.util.antispam import SecurityPolicy
      New: from MoinMoin.security.antispam import SecurityPolicy
      Old: from MoinMoin.util.autoadmin import SecurityPolicy
      New: from MoinMoin.security.autoadmin import SecurityPolicy
    * HINT: you need to change your auth stuff, the new way is:
      from MoinMoin.auth import moin_login, moin_session
      from MoinMoin.auth.http import http
      auth = [http, moin_login, moin_session]
      Do it in a similar way for other auth methods.
    * HINT: you need to change your url_prefix setting in 2 ways:
      1. The setting is now called url_prefix_static (to make it more clear
         that we mean the static stuff, not the wiki script url).
      2. The strongly recommended (and default) value of it is '/moin_static160'
         for moin version 1.6.0 (and will be ...161 for moin 1.6.1). It is
         possible and recommended to use a very long cache lifetime for static
         stuff now (Expires: access plus 1 year), because we require to change
         the URL of static stuff when the static stuff changes (e.g. on a
         version upgrade of moin) to avoid problems with stale cache content.
         Your moin will be faster with lower load and traffic because of this.
         For standalone server, we use 1 year expiry for static stuff now.
         For Apache, Lighttpd and other "external" servers, you have to care
         for configuring them to use a long expiry and change url_prefix_static
         related configuration on upgrade.
      HINT: if you run standalone or Twisted server, the easiest way to get a
            working configuration (with server configuration matching wiki
            configuration) is to NOT set url_prefix_static at all. Moin will
            use matching configuration defaults in this case.
    * url_prefix_action ['action'] was introduced for lowering load and traffic
      caused by searchengine crawlers. Up to now, crawlers where causing a high
      load in internet moin wikis because they tried to get about everything,
      including all actions linked from the user interface.
      Known crawlers only get 403 for most actions, but nevertheless they first
      tried. There was no means keeping them away from actions due to the rather
      braindead robots.txt standard. You can only disallow pathes there, but
      moin's actions were querystring based, not path based (this would need
      regex support in robots.txt, but there is no such thing).
      This changed now. Moin is able to generate action URLs you can handle in
      robots.txt, like /action/info/PageName?action=info. So if you don't want
      bots triggering actions, just disallow /action/ there. Keep in mind that
      attachments are handled by /action/AttachFile, so if you want attached
      files and pictures indexed by search engine, don't disallow
      /action/AttachFile/ in your robots.txt. In order to use this feature,
      set url_prefix_action in your wikiconfig to e.g. "action".
    * We use (again) the same browser compatibility check as FCKeditor uses
      internally, too. So if GUI editor invocation is broken due to browser
      compatibility issues or a wrong browser version check, please file a bug
      at FCKeditor development or browser development.
    * HINT: We removed Lupy based indexed search code. If you were brave enough
      to use cfg.lupy_search, you maybe want to try cfg.xapian_search instead.

  Developer notes: ===========================================================
    * We moved the IE hacks to theme/css/msie.css that gets included after all
      other css files (but before the user css file) using a conditional
      comment with "if IE", so it gets only loaded for MSIE (no matter which
      version). The file has some standard css inside (evaluated on all MSIE
      versions) and some * html hacks that only IE < 7 will read.
      HINT: if you use custom themes, you want to update them in the same way.
    * autofilters for databrowser widget. Thanks to Johannes Berg for the patch.
    * changed formatter.attachment_link call (it is now more flexible,
      because you can render the stuff between link start and link end yourself)
    * Page.url() does not escape any more. You have to use wikiutil.escape()
      yourself if you want to write the URL to HTML and it contains e.g. &.
    * The testing wikiconfig moved to tests/wikiconfig.py, the testing wiki
      is now created in tests/wiki/...
    * HINT: Killed "processors" (finally), formatter method changed to:
      formatter.parser(parsername, lines)
    * Refactored some actions to use ActionBase base class.
    * Moved "test" action from wikiaction to MoinMoin/action/
      (and use ActionBase).
    * Moved MoinMoin/config.py to MoinMoin/config/__init__.py.
    * Moved MoinMoin/multiconfig.py to MoinMoin/config/multiconfig.py.
    * Moved "SystemInfo" macro from wikimacro to MoinMoin/macro/.
    * Moved wikiaction.py stuff to MoinMoin/action/__init__.py.
    * Moved wikimacro.py stuff to MoinMoin/macro/__init__.py.
    * Moved wikirpc.py stuff to MoinMoin/xmlrpc/__init__.py.
    * Moved wikitest.py stuff to action/test.py (only used from there).
    * Moved formatter/base.py to formatter/__init__.py (FormatterBase).
    * Moved util/ParserBase.py to parser/ParserBase.py.
    * Moved / splitted request.py into MoinMoin/request/*.
      Most stuff will be broken, please help fixing it (usually some imports
      will be missing and the adaptor script will need a change maybe):
      Tested successfully: CGI, CLI, STANDALONE, FCGI, TWISTED
    * Moved security.py to security/__init__.py.
    * Moved wikiacl.py to security/__init__.py.
    * Moved logfile/logfile.py to logfile/__init__.py.
    * Moved mailimport.py to mail/mailimport.py.
    * Moved util/mail.py to mail/sendmail.py.
    * Moved auth.py to auth/__init__.py.
      Moved util/sessionParser.py to auth/_PHPsessionParser.py.
      teared auth code into single modules under auth/* - moin_session handling
      and the builting moin_login method are in auth/__init__.py.
    * Added wikiutil.MimeType class (works internally with sanitized mime
      types because the official ones suck).
    * Renamed parsers to module names representing sane mimetypes, e.g.:
      parser.wiki -> parser.text_moin_wiki
    * Added thread_monitor debugging aid. It can be activated using:
      from MoinMoin.util import thread_monitor; thread_monitor.activate_hook()
      and then triggered by requesting URL ...?action=thread_monitor - please
      be aware that monitoring threads has a big performance impact on its own,
      so you only want to temporarily enable this for debugging.
      By default, it dumps its output to the data_dir as tm_<timestamp>.log,
      you can change this at bottom of action/thread_monitor.py if you want to
      see output in your browser.
    * Introduced scope parameter to CacheEntry() - if you specify 'farm', it
      will cache into a common directory for all wikis in the same farm, if you
      specify 'wiki', it will use a cache directory per wiki and if you specify
      'item', it will use a cache directory per item (== per page).
      Creating a CacheEntry without explicit scope is DEPRECATED.
    * Smileys moved from MoinMoin.config to MoinMoin.theme.
    * Removed all _ magic in URLs and filenames.
    * request.action now has the action requested, default: 'show'.
    * Cleaned up duplicated http_headers code and DEPRECATED this function
      call (it was sometimes confused with setHttpHeaders call) - it will
      vanish with moin 1.7, so please fix your custom plugins!
      The replacement is:
          request.emit_http_headers(more_headers=[])
      This call pre-processes the headers list (encoding from unicode, making
      sure that there is exactly ONE content-type header, etc.) and then
      calls a server specific helper _emit_http_headers to emit it.
      Tested successfully: CGI, STANDALONE, FCGI, TWISTED
    * setResponseCode request method DEPRECATED (it only worked for Twisted
      anyway), just use emit_http_headers and include a Status: XXX header.
      Method will vanish with moin 1.7.
    * cfg.url_prefix is DEPRECATED, please use cfg.url_prefix_static.
    * d['title_link'] is not supported any more. You can easily make that link
      on your own in your theme, see example in MoinMoin/theme/__init__.py,
      function "title".
    * There is a new Page method called Page.get_raw_body_str that returns
      the encoded page body. This is useful if you just deal with byte data
      (e.g. while generating binary diffs).
    * The TagStore/PickleTagStore system is used to store the syncronisation tags.
    * XMLRPC functions may return Fault instances from now on
    * Moin got multicall support, including a module that makes it usable on the
      client-side without requiring Python 2.4
    * Added no_magic to text_html formatter to disable tag autoclosing.
    * MOIN_DEBUG can be set in the environment to let MoinMoin ignore exceptions
      that would lead to a traceback in the browser. Thanks to Raphael Bossek.
    * There is a new MoinMoin.Page.ItemCache class now with automatic cache
      invalidation based on global edit-log. We currently use it to cache page
      acls, speedup Page.get_rev and reading the page local edit-log.
    * Added wikiutil.renderText parse and format raw wiki markup with all page elements.
    * The user file format has changed, old files will be read correctly but
      will silently be upgraded to the new format so old versions will not
      read the new files correctly (this only affects 'subscribed_pages' and
      'quicklinks' which will be lost when downgrading.)


Version 1.5.8:
  New features:
    * Added timing.log to help performance debugging. Use cfg.log_timing = True
      to update <data_dir>/timing.log (default is False, meaning no logging).

      Example log entries:


      Timestamp       PID   Timing Flag action     URL
      -----------------------------------------------------------------------------
      20070512 184401 22690 vvv         None       moinmoin.wikiwikiweb.de/RssFeeds
      20070512 184401 22690 0.267s    - show       moinmoin.wikiwikiweb.de/RssFeeds

      Timestamp: YYYYMMDD HHMMSS (UTC)
      PID: the process ID of the moin process
      Timing: when action starts, it will be "vvv"
              when it ends, it logs the total time it needed for execution
      Flag (some are only logged at end of action):
      +   Page exists
      -   Page does not exist
      B   user agent was recognized as bot / spider
      !x! Action took rather long (the higher the x, the longer it took - this
          makes it easy to grep for problematic stuff).
      Action: action name (None is when no action was specified, moin assumes
              "show" for that case)
      URL: the requested URL

      For more information about tuning your moin setup, see:
      http://moinmoin.wikiwikiweb.de/PerformanceTuning
    * Added support for ircs, webcal, xmpp, ed2k and rootz protocols - we
      moved all protocols to config.url_schemas, so this is not empty any more.
      It is possible to use these protocols now on wiki pages and in the
      navi_bar. We just generate the URLs, it is up to your browser what it
      does when clicking on those links.
    * cfg.traceback_show (default: 1) can be used to disable showing tracebacks.
      cfg.traceback_log_dir (default: None) can be used to set a directory
      that is used to dump traceback files to. Your users will get a notice to
      which (random) file in that directory the traceback was been written.
      NOTE: while you can feel free to set traceback_show = 0 and
      traceback_log_dir = None, we will also feel free to reject bug reports
      when you (or your site's users) don't give us enough information (like a
      traceback file) to debug the problem. If you set traceback_show = 0,
      we recommend pointing traceback_log_dir to a directory with reasonable
      free space and putting a page onto your wiki that describes who has to
      get contacted (usually the wiki server admin) in case a traceback happens.
      The admin can then locate the traceback file and submit it to moin
      development, if the bug is not already known (see MoinMoin:MoinMoinBugs).
      Of course we will also need all the other details of a bug report, not
      only the traceback file.

  Other changes:
    * Updated spider agents list.
    * Reduce bot/spider cpu usage for SystemInfo, OrphanedPages, WantedPages,
      PageHits, PageSize, WordIndex macros (we just return nothing for bots).

  Bugfixes:
    * XSS fixes, see http://secunia.com/advisories/24138/ (item 1 and 2).
    * ACL security fixes:
      * MonthCalendar respects ACLs of day pages now.
      * Check the ACL for the rst markup include directive.
    * Fixed cleaning of edit comments (control chars in there could damage
      edit-log).
    * Fixed in-process caching of antispam patterns (didn't update the cache
      for multi-process, persistent servers).
    * Correct encoding/decoding for surge-log data, fixes leftover
      surge-logXXXXXXX.tmp files in data/cache/surgeprotect.
    * Fixed mode of cache files (mkstemp creates them with 0600 mode).
    * Symbolic entities with numbers (like &sup2;) did not work, fixed.
    * We open data/error.log earlier now and we also use it for FastCGI.
    * Fixed unicode cfg.page_group_regex.
    * Fixed moin.spec to use english date format.
    * GUI converter: fixed conversion of relative wiki links.
    * Fixed NewPage macro button label to not be formatted as wiki text.

Version 1.5.7:
  New features:
    * added url_prefix_local which is used for stuff that must be loaded from
      same site as the wiki engine (e.g. FCKeditor GUI editor applet), while
      url_prefix can be a remote server serving the static files (css/img).
      If not set (or set to None), url_prefix_local will default to the value
      of url_prefix.
    * We save some CPU and disk I/O by having EditTemplates and LikePages macro
      (both used on MissingPage) check whether the requesting entity was
      identified as a spider (e.g. search engine bot) and do nothing in that
      case. Normal users won't see any difference.
    * For AttachFile, you can now choose to overwrite existing files of same
      name (nice for updating files).

  Bugfixes:
    * XSS Fixes:
      * fixed unescaped page info display.
      * fixed unescaped page name display in AttachFile, RenamePage and
        LocalSiteMap actions
    * WantedPages listed existing pages that are not readable for the user,
      but are linked from pages that ARE readable for the user (so this is NOT
      a privacy/security issue). We now don't list those pages any more as it
      is pointless/confusing, the user can't read or edit there anyway.
    * MoinMoin:MoinMoinBugs/TableOfContentsUsesNonExistingIncludeLinks
    * MoinMoin:MoinMoinBugs/ActionsExcludedTriggerError
    * GUI editor/converter:
      * ignore <col>/<colgroup>/<meta> elements
      * support <a> within blockquote
    * Remove generated=... attribute from pagelink html output (this attr is
      for internal use only). w3c validator is now happier again.
    * Fixed css class "userpref" (not: "userprefs") of the Login form.
    * Fixed the version number check in the xslt parser for 4suite >= 1.0.
    * We reset the umask to the wanted value every request. This should fix
      wrong file modes when used with Twisted (twistd uses a hardcoded 0077
      umask in daemonize()).
    * Avoid trouble when saving pages with antispam function when MoinMaster
      wiki is having troubles (catch xmlrpc Fault).

  Other changes:
    * Standalone server does not do reverse DNS lookups any more (this is a
      standard feature of BaseHTTPServer stdlib module, but we override this
      now and just print the IP).
    * We moved the IE hacks to theme/css/msie.css that gets included after all
      other css files (but before the user css file) using a conditional
      comment with "if IE", so it gets only loaded for MSIE (no matter which
      version). The file has some standard css inside (evaluated on all MSIE
      versions) and some * html hacks that only IE < 7 will read.
      HINT: if you use custom themes, you want to update them in the same way.
    * Improved ldap auth:
      * cfg.ldap_name_attribute was removed because of new cfg.ldap_filter.
        If you had ldap_name_attribute = 'sAMAccountName' before, just use
        ldap_filter = '(sAMAccountName=%(username)s)' now.
      * New cfg.ldap_filter used for the ldap filter string used in the ldap
        search instead of the rather limited, partly hardcoded filter we used
        before. This is much more flexible:
        ldap_filter = '(sAMAccountName=%(username)s)'
        You can also do more complex filtering expressions like:
        '(&(cn=%(username)s)(memberOf=CN=WikiUsers,OU=Groups,DC=example,DC=org))'
      * Added some processing to filter out result entries with dn == None.
      * We set REFERRALS option to 0 before initializing the ldap server
        connection (this seems to be needed for Active Directory servers).
      * We support self-signed ssl certs for ldaps - completely untested.
      * New cfg.ldap_surname_attribute (usually 'sn'), was hardcoded before.
      * New cfg.ldap_givenname_attribute (usually 'givenName'), hardcoded before.
      * New cfg.ldap_aliasname_attribute (usually 'displayName') - if this
        attribute is not there or empty (in the results of the ldap lookup for
        the user), we just make up the aliasname from surname and givenname
        attribute.
      * We only request the attributes we need from ldap (was: all attrs).
      * We deny user login (and break out of auth chain) for the following cases:
        * if a user is not found by ldap lookup
        * if we find more than one matching entry
        * if the password is empty or incorrect
        * if some exception happens
      * Please note that there is an updated ldap sample config in directory
        wiki/config/more_samples/.
      * Added experimental LDAP SSL/TLS support (untested, please help testing),
        see also the sample config.
    * Work around a IE7 rendering problem with long pages getting more and
      more narrow. We just applied the same "fix" as we used for IE6, using
      "display: none" for span.anchor for IE browsers.
    * RSS feed related:
      * We used to emit a <link> tag for the action=rss_rc RSS feed on any
        page. This was changed, we now emit that link only on RecentChanges and
        the current user's language translation of RecentChanges.
        This was changed because Google Toolbar requests the RSS feed linked
        by such a link tag every time it sees one. Thus, if you used the wiki
        normally, it requested the RSS feed every few seconds and caused
        problems due to surge protection kicking in because of that.
      * HINT for custom theme users: if your theme code calls
        rsslink(), then you need to change that to rsslink(d) for 1.5.7+.


Version 1.5.6:
  A general security notice:
      Check your Python version, there was a buffer overflow issue in Python
      recently! Details: http://moinmoin.wikiwikiweb.de/PythonUnicodeEscapeBug

  Bugfixes:
    * Fix AttributeError traceback with Standalone server (if_modified_since)
    * Fix AttachFile "304 not modified" and redirect status code for Twisted
    * http auth: we now decode username and password to unicode (using
      config.charset == utf-8). Same for SSL client cert auth and CN.
    * Avoid infinite recursion in Page.parsePageLinks.
    * Fixed standalone server failing to shutdown if interface == "".
    * Now MoinMoin does not think anymore that every page links to various user
      homepages.
    * Made the irssi parser more tolerant (Thanks to "TheAnarcat").
    * Now multiple formatters can be used per request, the send_page code was
      not reentrant to this regard. Fixes "empty" search results.
    * Fixed problem with "=" in ImageLink macro links.
    * Not a moin bug, but a silly stdlib os.tempnam function made trouble to
      some people because it lets you override the path given in the code
      by setting the environment variable TMP(DIR). We now use a different
      function to avoid renaming trouble when TMP(DIR) points to a different
      file system.
    * Fixed antispam update on every save (Thanks to "TheAnarcat").
    * GUI converter: don't throw away rowclass for tables.
    * GUI editor formatter: allow height for table cells.
    * GUI editor formatter: comment texts are output using the formatter now. 

  New features:
    * Mail notifications contain a link to the diff action so the user
      can see the coloured difference more easily. Thanks to Tobias Polzin.
    * FeatureRequests/MoveAttachments - you can move attachments from one
      page to another (and also rename the attachment at the same time).
      Thanks to Reimar Bauer.
    * Added support for linking to attachment: and inline: URLs with ImageLink.
    * Added UNIX socket support for FastCGI, just set the port to some (socket)
      filename. Details see: MoinMoin:FeatureRequests/FastCgiUnixSocket
    * [[Attachlist(pagename,mimetype)]] lists attachments of pagename (default:
      current page) with optional mimetype restriction (default: all).
      Thanks to Reimar Bauer.

  Other changes:
    * Minor performance improvements (might be noticeable if you have many
      custom navi_bar entries and high server load).
    * Avoid usage of no-cache because it breaks attachment download on IE6.
      This is a IE bug, not a moin bug.
    * Added XHTML to the unsafe list.
    * Changed the rst parser to be compatible to the new docutils interface
      for directives.
    * Updated EmbedObject macro.


Version 1.5.5a:
  Bugfixes:
    * fixed ticket creation to only use constant values

Version 1.5.5:
  HINT: read docs/README.migration.
  HINT: there was NO change in the underlay/ pages since 1.5.4.
  HINT: If you experience problems with the reStructured Text (rst) parser,
        please downgrade docutils to "0.4" because there were major interface
        breaking API refactorings on the docutils trunk.

  Bugfixes:
    * GUI editor fixes:
      * Fixed MoinMoinBugs/GuiEditorModifiesInterwikiPreferred.
      * Fixed MoinMoinBugs/TableAlignmentProbsWithGUI.
    * Not a moin bug, but it severely annoyed IE users and also was less
      comfortable for users of other browser: since about 1.5.4, we served
      attachments with Content-Disposition: attachment - so that the user has
      to save them to disk. This was to fix a possible XSS attack using attached
      HTML files with Javascript inside for stealing your moin cookie or doing
      other nasty things. We improved this by using different behaviour depending
      on the potential danger the attached file has when served inline:
      mimetypes_xss_protect = ['text/html', 'application/x-shockwave-flash', ]
      This is the default value. If you know more dangerous stuff, please just
      add the mimetypes there to protect your users and file a bug report
      telling us what we missed.
    * Fixed MoinMoinBugs/ReStructuredTextRelativeLinksBroken, thanks to Stefan
      Merten.
    * Make tickets used for some actions more safe.

  New features:
    * edit_ticketing [True] - we protect page save by a ticket (same stuff we
      already use for DeletePage and RenamePage action).
      NOTE: If you don't use your browser for editing, but some tool like
            "editmoin" or "MoinMoin plugin for jEdit", you'll need an update
            of them supporting the ticket.
            Alternatively, you can use edit_ticketing = False setting - this
            is not recommended for internet wikis as it will make spamming them
            easier.
    * If we detect some spammer, we kick him out by triggering surge protection
      (if surge protection is not disabled).

Version 1.5.5rc1:
  Bugfixes:
    * Fixed MoinMoinBugs/XmlRpcBrokenForFastCgi - thanks to Johannes Berg.
    * Fixed gui editor converter confusing of `` and {{{}}} markup.
    * Fixed emission of HTTP headers (esp. Vary: Cache-Control:).
    * Fixed a bad crash that happens (on ANY page!) when you put a *Dict
      page's name as a member into a *Group page.
    * Fix MyPages action title to use an unformatted string.
    * Fix double quoted-printable encoding in generated emails (note: this is
      not a moin bug - this just works around bugs in python stdlib).
    * Fix mode of drawing files (use config.umask).
    * Fix trouble with /?action= urls by dropping getPageNameFromQueryString
      code. 
    * Fixed sre unpickle issues seen on some machines by avoiding to pickle
      the regex.
    * Fix Clock code, add more timers.
    * Worked around FastCGI problem on Lighttpd: empty lines in the error log.
    * Fix (add) locking for caching's .remove() call, small fixes to lock code.
    * Print error message when --target-dir=path is missing from moin export
      dump command.

  New features:
    * Added support for "304 not modified" response header for AttachFile get
      and rss_rc actions - faster, less traffic, less load.
    * Limit rss with full diffs to 5 items.
    * Allow surge_action_limits = None to disable surge protection.
    * moin.fcg improved - if you use FastCGI, you must use the new file:
      * can self-terminate after some number of requests (default: -1, this
        means "unlimited lifetime")
      * the count of created threads is limited now (default: 5), you can use
        1 to use non-threaded operation.
      * configurable socket.listen() backlog (default: 5)
    * Added indonesian i18n (id).
    * Some measures against spammers trying to brute force their spam into moin.
    * EmbedObject macro: added mov, mpg and midi support
    * moin ... export dump --target-dir=PATH --page=PAGENAME_REGEX
      You must specify --target-dir (where dump will write the html files to)
      and you may specify --page and either a page name or a regex used to
      match all pages you want to export. Default is to export all pages.

  Other changes:
    * Tuning:
      * more efficient locking code on POSIX platforms, we do much less I/O
        for locking now
      * removed most chmod calls in favour of a single os.umask call
    * Improved Python 2.5 compatibility. Note: if you think that MoinMoin
      is using too much RAM, you might want to look at Python 2.5 because
      of its improved memory management.
    * Throw away SAVE comments longer than 200 chars (you can't enter those by
      the user interface, so only spammer using automatic POSTs do them).
    * Updated spider user agent list.
    * BadContent and LocalBadContent now get noindex,nofollow robots header,
      same as POSTs.
    * Standalone opens it logfile unbuffered from now on, thanks to
      Carsten Grohmann.
    * Avoid trouble when request.write() data contains None, just skip it -
      thanks to Juergen Hermann.
    * Instead of showing a ConfigurationError, moin now emits "404 Not found"
      http headers and a hint about what could be wrong. This won't fill up
      your logs just because of typos and spiders still trying old URLs.

 
Version 1.5.4:
    HINT: read docs/README.migration.
Version 1.5.4-current:
    * increased maxlength of some input fields from 80 to 200

Version 1.5.current:
  Developer notes:
    * We switched to Mercurial SCM, see here for more infos:
      http://moinmoin.wikiwikiweb.de/MoinDev/MercurialGuide

  Bugfixes:
    * fix MonthCalendar macro for non-ASCII pagenames (thanks to Jonas Smedegaard)
    * remove 'search' and 'google' from bot user agent list and add some more
      specific terms
    * Fix the forgotten password email login URL and also properly encode the
      email body. Thanks to Robin Dunn for the patch.
    * Applied a patch by Matthew Gilbert for increased compatiblity with
      latest docutils.


Version 1.5.3:
  New Features:
    * Added CSS classes for TableOfContents macro.

  Bug Fixes:
    * GUI editor / GUI editor converter:
      * Fixed missing GUI editor link in edit bar.
      * Fixed table/row/cell style spaces.
      * Changed <p> generation for macros.
      * Fixed handling of subpages.
      * Fixed processing of complex list elements (thanks to Craig Markwardt).
      * Fixed processing of html \n (thanks to Craig Markwardt).
      * Fixed joining of comment lines with text below them.
      * Fixed table height attribute crash.
    * Fixed sslclientcert auth.
    * Added some missing files to i18n processing, translatable strings more
      complete now.
    * Change <p> generation from self-closing (<p />) to auto-closing (only
      emit <p>, let browser find place for </p>).
    * Fix eating of newline before tables.
    * Fixed incorrect login hint for not logged-in users trying a disallowed
      action.
    * Fixed nasty missing or double </a> formatter bug (mostly happening when
      user has enabled questionmarks for nonexisting pages).

  Other Changes:
    * We catch and ignore html to wiki conversion errors in case of hitting
      the cancel button, so you can get out of the error screen.

Version 1.5.3-rc2:
  New Features:
    * Modified SystemInfo macro to give human readable units and disk usage
    * cfg.editor_quickhelp makes the quick help below the editor configurable
      (at least as far as the default_markup is concerned). If set to None,
      it doesn't display any quickhelp. Thanks to Seth Falcon for the patch.

  Bugfixes:
    * Fixed double class attribute for nonexistent links
    * Fixed double </a> with qm_noexist option
    * Fixed table xxx="yyy" style attribute parsing
    * If not (editor_force and editor_default == 'text') then display GUI mode
      switch button (this is only a partial fix, but enough to deny the GUI
      mode to your users completely)
    * Fixed XSS issue which could lead to cookie theft etc.
    * Fixed definition list "same level" indenting.
    * Fixed pagename in log for PackagePages action.
    * Made <p> self-closing and line-anchors more well-behaved, thanks to
      Martin Wilck for the patch. I didn't apply the <ol> patch, because this
      is no real problem, just a problem of a bad standard.
    * Fixed gui editor *bgcolor crash.
    * Support/Fix tableclass attr with gui editor.

  Other changes:
    * Moved back UserPreferences action link from menu to top of page (renaming
      it to "Preferences"), added "Cancel" button to make it possible to return
      to the previous page without saving preferences.
    * Removed formatter.url "attrs" keyword arg that took premade html, we use
      separate kw args per attribute now.
    * Moved broken tests to MoinMoin/_tests/broken (= disabling them).
      All "active" tests run ok now.
      If you want to compare, I included the output of this test run:
      $ make test >tests/make_test.out

 
Version 1.5.3-rc1:

  New features:
    * HINT: please read README.migration
    * Login and Logout are actions now, therefore you stay on the page where
      you were before.
    * UserPreferences is also an action now and moved from top border (in
      modern theme) to the "more actions" dropdown menu. You also stay on the
      same page.
    * There is also a [[Login]] macro now. You can put it on any page you want
      and if the user is not logged in, it renders the login form. If the user
      is logged in, it doesn't render anything.
    * We check cfg.superuser to be a list of user names (as documented) and
      deny superuser access if it is not. This avoids security issues by
      wrong configuration.
    * auth methods changed:
      HINT: if you wrote own auth methods, please change them as you see in
            MoinMoin/auth.py and test them again before relying on them.
      * now get a user_obj kw argument that is either a user object returned
        from a previous auth method or None (if no user has been made up yet).
        The auth method should either return a user object (if it has
        determined one) or what it got as user_obj (being "passive") or None
        (if it wants to "veto" some user even if a previous method already has
        made up some user object).
      * return value of continue_flag is now True in most cases (except if
        it wants to "veto" and abort).
      * moin_cookie auth method now logs out a user by deleting the cookie and
        setting user_obj.valid = 0. This makes it possible to still get the
        user's name in subsequent auth method calls within the same request.
      * added ldap_login and smb_mount auth methods, see MoinMoin/auth.py and
        wiki/config/more_samples/ldap_smb_farmconfig.py
    * MonthCalendar now takes an additional argument for specifying a template
      to use to directly invoke the page editor when clicking on non-existing
      day pages.
    * Added ImageLink macro. Thanks to Jeff Kunce, Marcin Zalewski, Reimar
      Bauer and Chong-Dae Park for working on it.
    * Lupy stuff (still experimental, partly broken and disabled by default):
      * Attachment search using lupy (lupy_search = 1 in your config)
        Title search will also search attachment filenames.
        Full text search will also search attachment contents.
      * Indexing filter plugins, see MoinMoin:FiltersForIndexing
        Some filters depend on external converters that might not be available
        for any platform (see Depends: line in filter plugin).
        Feel free to contribute more filter plugins, especially if you wrote
        some nice platform independant filter in Python for some popular file
        format! Filters implemented so far (depending on):
        MS Word, RTF, MS Excel (antiword, catdoc)
        PDF (pdftotext)
        OpenOffice.org XML based data formats (-)
        XML, HTML (-)
        text/* (-)
        JPEG's EXIF data (-)
        Binary generic (-)
      * As you might know, Lupy is "retired" (that means it isn't developped
        by its authors any more). We are currently evaluating Xapian as new
        indexing search engine in moin.
        If we succeed, we will replace Lupy stuff by some Xapian interface
        code in moin.
        But: the filters will likely stay, as we also need them with Xapian.
    
    * A new MoinMoin script interface was introduced:
      
      Syntax: moin [options] <cmdmodule> <cmdname> [options]
      
      For example:
      moin --config-dir=/my/cfgdir --wiki-url=wiki.example.org/ \
           export dump --page=WikiSandBox
      
      This will call the "moin" script, which will use the --config-dir and
      --wiki-url options to initialize, then it will go to MoinMoin.script
      module, import the export.dump module from there and run it, providing
      the additional --page value to it.

      The old scripts that have not been migrated to this new interface can
      still be found in MoinMoin/script/old/ - including the old migration
      scripts.
    * moin ... account create --name=JoeDoe --email=joe@doe.org
    * moin ... account disable --name=JoeDoe
    * moin ... acount check     <-- this is what usercheck script was before
    * moin ... maint cleancache <-- this is what cachecleaner script was
    * moin ... maint cleanpage  <-- this is what pagescleaner script was

  Bugfixes:
    * cookie_lifetime didn't work comfortable for low values. The cookie was
      created once on login and never updated afterwards. So you got logged
      out cookie_lifetime hours later, no matter whether you were active at
      that time or not. This has been changed, we update the cookie expiry now
      on every request, so it will expire cookie_lifetime after your last
      request (not after login).
    * Fixed logout problems when using cfg.cookie_path.
    * Fixed cookie_path for root url wikis.
    * Lupy search now behaves a bit less funky. Still no guarantees...
    * We lowered the twisted server timeout to 2 minutes now (was: 10) because
      it just used up too many files (open TCP connections until it timeouts)
      on our farm.
    * The algorithm used for processing the farmconfig.wikis list was changed
      to work for big farms (>= 50 wikis), too. This works around the python
      "re" module limitation of having a maximum of 100 named groups in a RE.
    * Fixed a TypeError which occurred for formatters that dislike None values.
      (cf. http://moinmoin.wikiwikiweb.de/MoinMoinBugs/PythonErrorEditingFrontPage)
    * Fixed GUI editor converter error for https:... image URLs.
    * ThemeBase (use by modern/rightsidebar): removed duplicate AttachFile from
      actions menu (we already have it in editbar).
    * Speedup group/dicts scanning for persistent servers.
    * Implemented HEAD requests for standalone server, this should fix some of
      the strange effects happening when using "Save as" on attachments.
    * Not a moin bug, but rather a workaround for non-standard non-ASCII DNS
      hostnames: we just use the IP instead of crashing now.
    * Spurious cyclic usage error in i18n fixed.
    * Fixed antispam for python 2.5a xmlrpclib.
    * I18n for linenumber toggle in listings.
    * All action menu entries are translatable now.

  Other:
    * Added css classes for the rst admonitions. Thanks to TiagoMacambira!

Version 1.5.2:

  New features:
    * Added FullSearchCached macro which is statically cached.
      Use it if you do not depend on fresh search results but prefer raw speed.
    * Added surge protection, see HelpOnConfiguration/SurgeProtection.
    * Allow hex and symbolic entities.
    * If there is a user with empty password, we just generate a random one
      when he requests it getting sent by mail. Thanks to Reimar Bauer.
    * The superuser now can switch to another user using UserPreferences -
      nice to help your users when they forgot their password or need other
      help. You need to logout/relogin to use your own userid afterwards.
      This function only works correctly if you use moin_cookie authentication.
      Thanks to Reimar Bauer.
    * Add new markup for bulletless lists: just use a "." instead of "*".

  Other changes:
    * Added "voyager" to bot useragent list.
    * Added locking for caching subsystem.
    * Deron Meranda's formatter API cleanup.
    * Added div and span to formatter API.
    * Removed old unfinished form and export code.
    * updated i18n

  Fixes:
   * Fixed table attribute parsing.
   * Fixed cookie handling wrt properties adherance.
   * The new "." list markup makes it possible to have a bulletless list with
     elements on the same level. Before this change and only using indentation
     with blanks, that would get merged into a single paragraph.
   * It is possible now to have multiple paragraphs in the same list element,
     just leave an empty line in between the paragraphs.
   * Fixed GAP processing for ordered lists.
   * Fix text_gedit formatter's invalid list nesting.
   * Fixed hr crash in blockquote (but needs more work).
   * Fixed FootNote's formatter usage.
   * Fixed rst's headline levels.
   * Fixed MoinMoinBugs/WikiParserThinksItIsInsidePreWhenItIsNot
   * Fixed MoinMoinBugs/ListItemGeneratedOutsideList
   * Fixed that macros were followed by a wrong <p>.
   * Added <blockquote> to the block elements in the text_html formatter,
     so it does not close it erratically when you close a inner <p>.
   * GUI editor converter now also accept http: urls without // (relative or
     same server urls).
   * Fixed the DocBook parser in cases where the pagename was non-ascii.
   * Fixed MoinMoinBugs/ProcessInlineDontSupportUlElement


Version 1.5.1:

  Fixes:
    * Fixed rst parser docutils version check
    * Repaired attachment unzipping feature.
    * Fixed the AddRevision command of the PackageInstaller.
    * improved the migration scripts (used to migrate pre-1.3 wikis to 1.3+):
      * do not crash on empty lines in event log
      * fix edit log format for very old moin data (like 0.11)
      * workaround for an ugly win32 operating system bug leading to wiki text
        file mtime not matching edit logs timestamp values if there was some
        timezone change since last edit (e.g. a daylight saving tz switch),
        but differing 3600s.
        This affected pre-1.3 moin wiki servers running on win32 OS only.
        We now try to correct those inconsistencies in mig05 by fuzzy matching.
    * fixed bracketed link scheme icon (css class)
    * we included a modified copy of Python 2.4.2's copy.py as some previous
      python versions seem to have problems (2.3.x, x < 5 and also 2.4[.0]),
      see: http://moinmoin.wikiwikiweb.de/MoinMoinBugs/DeepCopyError
      Our own copy.py was slightly modified to run on 2.3.x and 2.4.x.
    * Fixed the problem of not being able to change the date/time format back
      to "Default" (UserPreferences).
    * We generate the GUI editor footer now the same way as the text editor
      footer.
    * Include a CSS workaround for yet another IE bug, see:
      MoinMoinBugs:InternetExplorerPeekABooBugInRightSideBar
    * classic theme: added GUI editor link
    * classic theme: added pagename header to editor screen
    * the "mail enabled" check now also checks whether mail_from is set

  Other changes:
    * Updated FCKeditor to current CVS (2006-01-08 == 2.2+)
    * Split up show_hosts into show_hosts and show_names
    * attachment:file%20with%20spaces.txt in attachment list
    * added support for file:// in GUI editor link dialogue, see also:
      MoinMoin:FileLinks
    * cfg.mail_smarthost now supports "server:port" syntax, the default port
      is 25, of course.
    * removed unused kwargs showpage/editable/form from wikiutil.send_footer
    * updated i18n (translation texts, additional languages)
    * removed interwiki:pagename from print view's top of page, added it to
      the "lasted edited" line at bottom right.


Version 1.5.0:
  HINT: 1.5.0 uses the same data/pages format as 1.3.x. The only thing you want
        to check is whether the 1.5.x version you are upgrading to has NEW mig
        scripts compared to the version you are running now (e.g. in 1.3.5 we
        added some scripts that fixed some small problems).
        See the MoinMoin/scripts/migration/ directory.
        You must run every mig script in sequence and only ONCE ever.
  Fixes:
    * Fix <x=y> table attributes parsing. Thanks to Reimar Bauer.
    * Fixed a few bugs in the reStructured text parser. Note that you
      need to install docutils 0.3.10 or newer (snapshot from December 2005
      or newer) to make reStructuring parsing work:
     * Case preservation for anonymous links
     * MoinMoin links get the appropriate CSS class
     * Images do not get special CSS markup anymore
     Thanks to Matthew Gilbert.
    * Fixed a bug in the WSGI code which led to incorrect exception handling.
    * Removed all nationality flags. They used to be used for indicating some
      specific language (NOT nationality) and this was simply wrong and a bad
      idea.
    * Fixed some header rendering issues (CSS).
    * SystemAdmin macro now checks against cfg.superuser list.

  Other changes:
    * Added turkish i18n. To be considered as alpha as it got in last minute.


Version 1.5.0rc1:
  This is the first release candidate of MoinMoin 1.5.0.
  
  Fixes:
    * fixed broken logs when a DeletePage (maybe also RenamePage) comment
      contained CR/LF characters (could happen when using copy&paste)
    * fixed GUI editor MoinEditorBackup page containing HTML instead of wiki
      markup
    * fixed invalid HTML in FootNotes
    * fixed HTML source in EditorBackup after canceling GUI editor
    * Footnotes of included pages are not shown at the bottom of the including page.
    * Bug in Dict handling that often breaks first entry

Version 1.5.0beta6:
  Authentication:
    * Added SSO module for PHP based apps. Currently supported: eGroupware 1.2.
      No need to login in two systems anymore - MoinMoin will read the PHP session
      files.

  Fixes:
    * Improved rendering of bullet lists and external links in Restructured text.
      Thanks to Matthew Gilbert.
    * Fixed modern theme rendering, including some fixes and workarounds for
      broken MS IE.
    * When checking for email uniqueness, do not compare with disabled user
      profiles.
    * Fix sending of HTTP headers for Despam action.
    * Add some margin left and right of the link icons.

  Other changes:
    * Made it easier for auth methods needing a user interface (like ldap or
      mysql stuff). Unlike http auth, they usually need some "login form".
      We made UserPreferences login form values (name, password, login, logout)
      available as kw args of the auth method, so it is easy and obvious now.
    * Make login and logout show at the same place. Is only shown when
      show_login is True (default).
    * Disabled login using &uid=12345.67.8910 method. Please use name/password.
    * Made builtin moin_cookie authentication more modular: the cookie is now
      touched by MoinMoin.auth.moin_cookie only, with one minor discomfort:
      When creating a user, you are not automatically logged in any more.
    * We now use the packager for additional help and system pages in all other
      languages except English. The packages are attached to SystemPagesSetup
      page and can be installed from there after getting "superuser" powers.
      The "extra" package contains a collection of orphan pages not listed on
      some SystemPagesIn<Language>Group page.


Version 1.5.0beta5:
  Fixes:
    * Fixed a minor user interface bug: it showed RenamePage and DeletePage
      actions in the menu if you only had write rights and then complained
      when you really tried when you had no delete rights additionally.
    * We don't remove RenamePage and DeletePage from menu any more if user is
      unknown. This stuff is only driven by ACLs now.
    * Some fixes to Despam action.
    * Fixed moin_dump (broken by some recent theme init change).
    * Fixed a few tests by moving the theme init from moin_dump to RequestCLI.
    * removed old_onload reference from infobox.js
    * Fixed MoinMoin logo for IE.
    * search: fixed whitespace handling in linkto: search terms
    * Increased stability of the tests system by outputting results to sys.stdout
      instead of request. Note that this changes the semantics for e.g. mod_py or
      mod_fcgi.
    * Fixed packaging system in the case of AddRevision that does not alter the page.
    * Fixed a few bugs in the XML formatters (dom_xml, text_xml, xml_docbook).
    * Fixed link icons. We now just use a.xxx.before where xxx is the link scheme,
      e.g. a.http.before. See theme's common.css.
    * Hopefully fixed some issue with non-ASCII attachment filenames.
    * Workaround for Opera 8.5 making silly "No addition" categories.
    * Do not show GUI editor for non-wiki format pages, because we only have a
      converter from html to wiki right now.
    * Fix the modern CSS issues for editbar, when it shifted content far right.
      Also removed the absolute height value that never was right.
    * Fix mod_python adaptor bugs failing to handle Location correctly.
      See: http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=339543

  Other changes:
    * Added irc:// to the builtin supported link schemas. You can remove it
      from config.url_schemas in case you have patched it in there.
    * Added cfg.user_autocreate (default: False). Use True to enable user
      profile autocreation, e.g. when you use http authentication, so your
      externally authenticated users don't need to create their moin profile
      manually. The auth method (see cfg.auth list) must check this setting
      if it supports auto creation.
    * Added user_autocreate support for auth.http and auth.sslclientcert.
    * Added "." and "@" to allowed characters in usernames. This is needed
      e.g. when using mod_pubcookie for authentication. mod_pubcookie returns
      userids like "geek@ANDREW.CMU.EDU" (e.g. the Kerberos domain is part of
      the id). Thanks to Brian E. Gallew for his patch, which we used for
      inspiration for user autocreation changes.
    * Changed auth method to return a tuple (user_obj, continue_flag), see
      comments in auth.py.
    * auth methods now create user objects with kw args auth_method and
      auth_attribs, so that moin knows later how the user was authenticated
      and which user object attributes were determined by the auth method.
    * Added MoinMoin/scripts/import/IrcLogImporter.py to import supybot's
      IRC logs into a moin wiki. We use MonthCalendar compatible page names,
      so you can use the calendar for showing / navigating the logs.
    * Removed packager binary from FCKeditor (fixing a Debian policy problem).
    * Worked around .png transparency bugs of IE with the new logo. We ship
      two logos: moinmoin.png without an alpha channel (IE compatible) and
      moinmoin_alpha.png which has an alpha channel and looks better on
      browsers with full .png support.
    * Allow a .zip file to have a directory in it if it is the only one.

Version 1.5.0beta4:
  Fixes:
    * use <span class="anchor"> instead of <a> for line-xxx anchors, this
      fixes some rendering problems on IE
    * Fixed the ReStructured text parser when it was used with non-HTML
      formatters. Increased compatiblity with new docutils code.
      (Thanks to Matt Gilbert.)
  Other changes:
    * cfg.stylesheets = [] (default). You can use this on wiki or farm level
      to emit stylesheets after the theme css and before the user prefs css.
      The list entries must be ('screen', '/where/ever/is/my.css') style.
    * Added sample code for auth using an external cookie made by some other
      program. See contrib/auth_externalcookie/*. You need to edit it to
      fit whatever cookie you want to use.

Version 1.5.0beta3:
  Fixes:
    * fixed editor preview throwing away page content for new pages
    * require POST for userform save and create* action
    * use request.normalizePagename() while collecting pagelinks
    * do not offer gui editor for safari
  Other changes:
    * tell user if account is disabled
    * added support for linking to .ico and .bmp
    * attachment methods for the text_xml and xml_docbook formatters
    * new favicon
    * updated i18n (fixed nl, did nobody notice this?) and underlay
    * changed show_interwiki default to 0

Version 1.5.0beta2:
  Fixes:
    * fix wrong _ in title links (MoinMoinBugs/AddSpaceWikiNameAtHead)
    * fix gui editor (converter) crash on save
    * MoinMoinBugs/PageHitsFails
    * MoinMoinBugs/PackagePagesFailsBecauseAllowedActionsMissing
    * Avoid destroying existing page content if editor is called with
      template parameter for an existing page.
    * fix countdown javascript for browser status line in editor
    * added page title display for editor
    * added header div for classic theme

  Authentication and related:
    * Added a WhoAmI.py wiki xmlrpc plugin to check whether auth works
      correctly for xmlrpc. There is a counterpart script WhoAmI.py that
      uses http auth when calling the xmlrpc plugin, so you can use it to
      check http auth.

Version 1.5.0beta1:
    * Requirements changed to require Python >= 2.3. We recommend that
      you use the latest Python release you can get. The reason we
      dropped 2.2.2 support is because no developer or tester uses this
      old version any more, so incompatibilities crept in the code
      without anybody noticing. Using some recent Python usually is no
      real problem, see there for some hints in case you still run an
      old python: http://moinmoin.wikiwikiweb.de/NewPythonOnOldLinux
      The hint also does apply to other POSIX style operating systems,
      not only Linux.
    * We recommend you use MoinMoin/scripts/cachecleaner.py to clean the
      wiki's cache (see comments at top of the script).
      The cache will automatically be rebuilt (some operations may take
      some time when first being used, e.g. linkto: search, so be patient!).

  Config Changes:
     * there is a file CHANGES.config with just the recently changed stuff
       from multiconfig.py
     * new defaults:
       * page_front_page old: u"FrontPage" new: u"HelpOnLanguages"
         please just read the help page in case you see it :)
       * bang_meta old: 0 new: 1
       * show_section_numbers old: 1 new: 0
       * some regexes that used to be [a-z]Uxxxx$ are now [a-z0-9]Uxxxx$
       * navi_bar has no page_front_page as first element any more
     * removed settings and code [new behaviour]:
       * acl_enabled [1]
       * allow_extended_names [1]
       * allow_numeric_entities [1]
       * backtick_meta [1]
       * allow_subpages [1]
     * new settings:
      * cfg.mail_sendmail = "/usr/sbin/sendmail -t -i" can be used if sending
        via SMTP doesn't work on your server. Default is None and that means
        using SMTP.
      * language_default replaces the old default_lang setting (just renamed).
      * language_ignore_browser = True can be used to let moin ignore the
        user's browser settings (e.g. if you run a local-language only wiki
        and your users use misconfigured or buggy browsers often). Default is
        False. Don't forget to set language_default when using this.
 
    * Wiki Editor changes / new WYSIWYG editor
     * fully imported the javascript based LGPLed FCKeditor (many thanks
      to Fred CK for his great work). See http://fckeditor.net/ for details.
     * config for FCKeditor is at wiki/htdocs/applets/moinfckeditor.js
     * added cfg.interwiki_preferred (default = []) to set a list of wikis to
       show at the top of the wiki selection list when inserting an
       interwiki link (just use the same wiki name as in interwiki
       map). If the last list item is None, then the preferred wikis
       will not be followed by the entries of the interwiki map.
    * moved save/preview/... buttons to the top so that they can be
      easily reached
    * reduced edit_rows default to 20 lines
    * Added support for edit by doubleclick in the diff view

    * Improved wiki farm support
     * make user files sharable between several wikis in a farm
      * allow/use interwiki subscriptions
      * use interwiki links in page trail
      * save bookmark per wiki name
     * cfg.cookie_domain can be used to set a cookie valid for a complete
       domain (default: None == only for this host). If you use '.domain.tld',
       the cookie will be valid for all hosts *.domain.tld - good for host
       based wiki farms.
     * cfg.cookie_path can be used to set a cookie valid for a wiki farm under
       some base path (default: None == only for this wiki's path). If you use
       '/wikifarm',  the cookie will be valid for all wikis
       server.tld/wikifarm/* - good for path based wiki farms.
     * Interwiki user homepage (if you have MANY users)
       Generated links for usernames are interwiki now, use cfg.user_homewiki
       (default: 'Self') to specify in which wiki the user home pages are
       located. Note: when pointing this to another wiki, the /MoinEditorBackup
       functionality will be disabled.
       @SIG@ also uses interwiki when needed.

    * Authentication, ACLs and related
     * Modular authentication: cfg.auth is a list of functions that return a
       valid user or None, use it like this:
           from MoinMoin.auth import http, moin_cookie
           auth = [http, moin_cookie]
     * cfg.auth_http_enabled was removed, please use cfg.auth instead.
     * http auth now supports "Negotiate" scheme, too
     * Added sslclientcert auth method (Apache: untested, Twisted: not
       implemented, IIS: no idea). See MoinMoin/auth.py for details.
       Submit a patch if you have improvements.
     * cfg.superuser is a list of unicode usernames. It is used by some
       critical operations like despam action or PackageInstaller.
     * removed allowed_actions, we now use actions_excluded only and it
       defaults to [], that means, no action is excluded, everything is
       allowed (limited by ACLs). In case of RenamePage and DeletePage,
       this shouldn't be a problem as both can be reverted. In case you
       did not allow attachments, you now have to use:
       actions_excluded = ['AttachFile']
     * special users (All, Known, Trusted) in Groups are now supported
     * MoinMoin.security.autoadmin SecurityPolicy added
       When using this security policy, a user will get admin rights on his
       homepage (where pagename == username) and its sub pages. This is needed
       for the MyPages action, but can also get used for manual ACL changes.
       It can also be used for Project page auto admin functionality, see the
       comments in the script for details.
       Further it can automatically create the user's group pages when the
       user saves his homepage.
     * there is a UpdateGroup xmlrpc call, see MoinMoin/xmlrpc/UpdateGroup.py -
       you can use this to update your *Group pages e.g. when generating them
       from an external group database.

    * UserPreferences changes
     * Alias name: is used for display purposes, when "name" is cryptic. It is
       shown e.g. in the title attribute of userid links (displayed when
       moving the mouse over it).
     * "Publish my email (not my wiki homepage) in author info" - use this
       if you don't have a wiki homepage, but if you want to be contactable
       by email. When you edit a page, your email address will be published
       as mailto: link on RecentChanges, at bottom of page (last editor) and
       in page info. If the wiki runs publically on the internet, be careful
       using this or your email address might be collected by spammers.
     * Preferred Editor: whether you want to use the text editor (as in
       previous moin versions), the gui editor (new!) or both (you will get
       2 edit links in that case).
     * a user can add/remove the current page to/from his quicklinks with an
       appropriate action now
     * if cfg.user_email_unique = False, we don't require user's email
       addresses to be unique
     * removed show_fancy_links user preferences setting to simplify code and
       caching. Displaying those icons is now done by CSS styles (see
       common.css). Maybe needs fixing for non-standard themes and RTL langs.

    * Markup
     * added strikethrough markup: --(striked through text here)--
     * @ME@ expands to just the plain username (no markup added) on save
    
    * User homepages
     * when a user accesses his own non-existing homepage (pagename ==
       username), the wiki will present the MissingHomePage system page
       content, explaining what a user homepage is good for and offer
       one-click editing it with content loaded from HomepageTemplate
     * creation of homepage subpages is assisted by the MyPages action, which
       offers rw, ro page creation (and a related group) or creation of private
       pages. If you are not in the user_homewiki, you will get redirected
       there first.

  Other changes/new features:
    * Added PackageInstaller and unzipping support (see wiki page
      HelpOnActions/AttachFile for further details).  PackageInstaller requires
      the user to be in cfg.superuser list.
     * Added an PackagePages action to simplify the package creation.
    * Added location breadcrumbs - when you are on some subpage, the page
      title parts link to the corresponding parent pages, the last part does
      the usual reverse linking.
    * added WSGI server support, thanks to Anakim Border, see:
      wiki/server/moinwsgi.py (moin as WSGI app, uses the flup WSGI server,
                               see http://www.saddi.com/software/flup/)
      MoinMoin/server/wsgi.py (adaptor code)
    * added a "Despam" action to make de-spamming a wiki easy (mass revert
      bad changes done by a single author or bot). You need to be in
      cfg.superuser to use it.
    * Better diffs with links to anchors to the changed places
    * Enhanced table support in the DocBook formatter.
    * Added 'moin' daemon script, that let you run moin standalone
      server as daemon and control the server with simple command line
      intreface: moin start | stop | restart | kill
    * Add 'restart' option to mointwisted script
    * Add properties option to standalone server config. Allow
      overriding any request property like in other server types.
    * Add support for running behind proxy out of the box with out
      manual url mapping.
      See HelpOnConfiguration/IntegratingWithApache
    * added a WikiBackup action, configure it similar to this:
      data_dir = "/path/to/data"
      backup_include = [data_dir, ] # you can add other dirs here
      backup_users = ["BackupUserName", ] # only TRUSTED users!
      You usually don't need to change the default backup_exclude setting.
      The default backup_include list is EMPTY and so will be your
      backup in case you don't configure it correctly.
      If you put your data_dir there, the backup will contain private
      user data like email addresses and encrypted passwords.
    * Added a SubscribeUser action which allows the administrator to subscribe users to the
      current page.
    * Added thread count to SystemInfo macro.
    * Added Petr's newest patch against the DocBook code. It allows you to use macros (esp. the include macro) in DocBook pages in order to build larger documents.
    * Added a RenderAsDocbook action which redirects to the DocBook formatter.
    * Added searching for wiki-local words lists under <data_dir>/dict/.
      They are used additionally to the global lists in MoinMoin/dict/.
    * moin_dump now also dumps attachments referenced from the page.
      It doesn't dump stuff that is just attached, but not referenced!
    * On RecentChanges we now force the comment to be breakable, this improves
      rendering of over-long words or on narrow browser windows - especially
      for themes with limited content width like rightsidebar.
    * We now have the "new" icon on RecentChanges clickable, just links to the
      page.
    * Print view now shows "interwikiname: pagename" (for show_interwiki = 1).

  International support:    
    * mail_from can be now a unicode name-address 
      e.g u'Jürgen wiki <noreply@jhwiki.org>'

  Theme changes:
    * logo_string is now should be really only the logo (img).
      If you included your wiki's name in logo_string you maybe want to remove
      it now as it is shown as part of the location display now anyway (if
      you set show_interwiki = 1).
    * You maybe want to remove page_front_page from your navi_bar - we link to
      that page now from the logo and (new, if you set show_interwiki = 1) from
      the interwiki name displayed in location display, so you maybe don't need
      it in navi_bar, too.
    * If you have a custom theme, you should / may:
     * sync modern/css/screen.css #pagelocation #pagetrail stuff to your
       screen.css or pagelocation display (title()) will look strange (like a
       list).
     * remove "#title h1 ..." CSS (or any other CSS assuming h1 is a page
       title and not just a first level heading), it is not used any more.
     * we now render = heading = as <h1> (was <h2> before 1.5),
       == heading == as <h2> (was <h3>), etc.
     * maybe move both title() and trail() to header area, like the builtin
       themes do it.
     * there is a new interwiki() base theme method that optionally (if
       show_interwiki = 1) shows the interwiki name of this wiki and links to
       page_front_page. The css for it is #interwiki.

  Developer notes:    
    * Plugin API was improved. When plugin module is missing,
      wikiutil.PluginMissingError is raised. When trying to import a
      missing name from a plugin module, wikiutil.PluginMissingError is
      raised. You must update any code that use wikiutil.importPlugin.
      Errors in your plugin should raise now correct tracebacks. See
      http://moinmoin.wikiwikiweb.de/ErrorHandlingInPlugins
    * pysupport.importName was changed, it does not check for any
      errors when trying to import a name from a module. The calling
      code should check for ImportError or AttributeError. Previous
      code used to hide all errors behind None.
    * Its easier now to customize the editbar by overriding
      editbarItems() in your theme, and returning a list of items to
      display in the editbar. To change a single editbar link, override
      one of the xxxLink methods in your theme.

  Internal Changes:
    * request.formatter (html) is available for actions now
    * theme API's d['page_home_page'] is gone (sorry) and replaced by
      d['home_page'] which is either None or tuple (wikiname,pagename).
      It is better to use the base classes function for username/prefs anyway.
    * introduced cfg.hacks for internal use by development, see comment in
      multiconfig.py and file HACKS.
    * added IE7 (v0.9) from Dean Edwards (see http://dean.edwards.name/IE7/) -
      that should fix quite some IE bugs and annoyances (on Win32).
      * for enabling IE7, use cfg.hacks = { 'ie7': True }
    * reducewiki now also copies all attachments (we use that to make underlay
      directory from moinmaster wiki's data_dir)

  Fixes:  
    * Fixed a typo in xslt.py which led to a traceback instead of an
      error message in case of disabled XSLT support.
    * Fixed crash in twisted server if twisted.internet.ssl is not
      available.
    * Fixed wrong decoding of query string, enable wiki/?page_name urls
      with non ascii page names.
    * Fixed wrong display of non ascii attachments names in
      RecentChanges and page revision history.
    * Fixed a crash when trying to run standalone server on non posix os.
    * Fixed highlight of misspelled words in Check Spelling action.
    * Fixed case insensitivity problems on darwin (Mac OS X). See
      MoinMoinBugs/MacHfsPlusCaseInsensitive
    * Added RecentChanges (only the english one) to the pages getting
      html_head_index headers
    * text_html cache files written with this code will invalidate themselves
      if they detect to be older than the wikiconfig. Note: you should remove
      all old text_html cache files once after upgrading, they will then be
      rebuilt automatically with the new code.
    * Fixed MoinMoinBugs/12_to_13_mig10_Walk
    * Fixed the word_rule: a word like AAAbbAbb isn't teared into two parts
      any more (was: AA<link>AbbAbb</link>)
    * Fixed false positive InterWiki markup for languages like Finnish.
      InterWiki links are only rendered if the left side has an appropriate
      entry in the interwiki map, otherwise it is rendered as simple text.
    * Fixed unicode error when uploding non-ascii file name using mod
      python.
    * Fixed error handling of wikirpc requests, should give more
      correct errors and prevent no error output and blocking the
      client in some cases.
    * Fixed the "lost password" mail processing. If a user entered some email
      address unknown to the system, he was not notified of this, but just got
      a useless mail with no account data in it. Now the system directly tells
      the user that he entered an unknown email address.
    * Fixed SystemInfo, it now also lists parsers in data/plugin/parser dir.
    * Fix error handling on failure, improved error display
    * Fix error handling when importing plugins or importing modules
      dynamically. The fix is not backward compatible with older plugins.
    * Fix chart action, returns a page with error message when chart
      can not be created.
    * Fixed formatter usage in the ShowSmileys macro.
    * Fixed updating pagelinks cache for [:page:text] or [wiki:Self:page text],
      fixes display of LocalSiteMap and rendering of such links.
    * Hopefully fixed urllib problems (esp. with py 2.4.2, but also before) by
      using our own urllib wrapper that handles encoding/decoding to/from
      unicode, see wikiutil.py. Also made a similar fix for making and parsing
      query strings.
    * Fixed MonthCalendar tooltips when containing special chars like quotes.
    * Added html escaping for diff text for RSS feed with diff=1.
    * The distance between page content beginning and the first = heading =
      was much too much. Fixed.
    
Version 1.4:

    We used that version number for an internal and early development version
    for what will be called moin 2.0 at some time in the future.
    There will never be a 1.4.x release.


Version 1.3.5 (2005-08-04, Revision moin--main--1.3--patch-883)

Fixes:
    * small CSS fix for rightsidebar theme
    * applied some Debian patches (thanks to Jonas!):
      * de i18n spelling fixes
      * AttachFile fix, we strip CR in .draw files now
      * when loading spellcheck dictionaries, we want utf-8, but we make
        a 2nd try with iso-8859-1 encoding.

New Features:

    * enabled using https with the Twisted server:
      You need to use port 443, have PyOpenSSL (+ ssl libs it depends on)
      installed and have some site key and certificate PEM files configured in
      your twistedmoin.py file:
      sslcert = ('/whereever/cert/sitekey.pem', '/whereever/cert/sitecert.pem')


Version 1.3.5rc1 (2005-07-31, Revision moin--main--1.3--patch-865)

Fixes:

    * Fixed security bug when acl of deleted page was ignored. See:
      http://moinmoin.wikiwikiweb.de/MoinMoinBugs/ACLIgnoredAfterDelete
    * AttachFile did not display the original filename plus there
      was a confusion in input field labelling ('Rename to').
    * Fixed shortcut link non-existent page detection.
    * Fixed non-working bookmark function on python 2.2.x.
    * Fixed wikirpc getPageInfo call on python 2.2.x.
    * Fixed the failing import of plugins from the data/plugin/
      directories if run in zipimport environments.
    * Fixed traceback which occurred on negated searches.
    * Fixed crash when trying to render error message on twisted, fast
      cgi and modpy.
    * Fixed error message with modpy, used to show wrong errors below
      the real message.
    * Fixed search and goto text fields for better compatibility with
      dark themes and better control through css.
    * Show an edit link if MissingPage is missing and a warning in the
      server log.
    * Fixed missing footer in the editor.
    * Fixed indented (invalid) headings with broken links in table of
      contents.
    * Fixed crash when file name is too long, show standard error message.
    * Save trail file in a safe way, should be enough for normal use.
    * Fixed remember_last_visit user preferences option when show_trail
      is not selected.
    * Fixed the tests for Standalone, Twisted, FastCGI and Mod_Python.
      Run with ?action=test from any page.
    * Fixed rare bug when wrong search type was performed when pasting
      search term in Safari.
    * Fixed crash for custom formatters and dom_xml (which occurred if
      smileys were in the page).
    * Editor opens on double click in pages with single quote in the
      name, like "Ben's Wiki".
    * '/.' in page names are not replaced any more by '/(2e)'
    * Fixed the long delays while saving pages using RequestCLI.
    * Fixed variable expanding for users with non WikiName.
    * Fixed MonthCalendar's calculation of "today" to use the user's
      time zone setting.
    * Fixed moin_dump script, use same configuration options as other
      scripts.
    * Fixed url_mappings to work in proxied setups and sent mails
      again. Also fixed for image links. Thanks to JohannesBerg.
    * Fixed page shown after saving a drawing (esp. when saved from a
      sub page). Fixed help link for drawings.
    * Fixed mig10 script to run on Python < 2.3.
    * The twisted server defaulted to a socket timeout of 12 hours!
      We reduced that to a more sane 10 minutes, that should still be more
      than enough. This fixed the "too many open files" problem we
      encountered quite often recently. Thanks to Helmut Grohne!

Other Changes:

    * Added {hu} flag.
    * Added cz, pt and pt-br i18n.
    * We send a 404 http status code for nonexisting wiki pages now,
      maybe this will repell some search engines from requesting gone
      pages again and again. The wiki user still sees the MissingPage
      wiki stuff, so a user usually won't notice this change.
    * Return 500 error code on failure and exceptions.
    * Added some more bot / leech tool user agent strings.
    * Prevent page floating elements from floating out of the page over
      the footer, in modern, rightsidebar and classic themes.
    * Encode URLs in a safer way
    * We allow usernames with ' character in them now (like Tim O'Brian).
    * Added support for the new security flags in docutils 0.3.9.
    * @MAILTO@ expands now to safer [[MailTo()]] macro.
    * Clarified and i18ned lost password mails.
    * Added 'TitleIndex' and 'SiteNavigation' (+ translation) to the
      list of pages that use html_head_index (so that robots
      "index,follow").  Please make sure to have either FindPage,
      TitleIndex or SiteNavigation in your navi_bar or in your
      page_front_page content if you want search engines to find all
      your pages.
    * Make it possible to send account data when being logged in (for
      future reference or whatever purpose).
    * Speed up when running with persistent servers, the wiki config
      does only get loaded once and misc. stuff is being cached between
      requests now.
    * The unit tests are disabled when using multi threading, because
      the wiki configuration is shared between diffrent threads.
    * The main code path (using standalone server) of MoinMoin runs on
      PyPy now.
    * Formatters do automatically transform HTML to plain text if they are
      called with raw HTML code.
    * Using larger socket backlog on Standalone and FastCGI servers
      should be more reliable on high load.
    * We now strip leading path from attachments uploaded by IE (this is
      a bug in IE, not in MoinMoin). Better use a sane browser, like Firefox.
    * added "teleport" to the user agent blacklist

New Features:

    * Integrated Lupy indexer for better search performance. It is disabled
      by default as of 1.3.5 as it still has known issues.
      See multiconfig.py if you want to test it.
    * Integrated MonthCalendar 2.1, with some new features:
      * a mouseover bubble that shows first level headlines of the linked
        day page
      * all calendars with same pagename move when using cal navigation,
        thanks to Oliver Graf
      * included AnnualMonthlyCalendar patch of Jonathan Dietrich
        (use [[MonthCalendar(Yearly,,,+1,,6,1)]] syntax for birthdays and
        other annually repeating stuff)
      Make sure you remove old MonthCalendar.* from data/plugin/macro so that
      moin will use the new code in MoinMoin/macro/MonthCalendar.py.
      Maybe also clear the text_html cache.
    * Added the new XSLT parser and the DocBook parser. This should increase
      the 4suite compatiblity. See HelpOnXmlPages for details.
      It now should run on 4suite 1.0a4 and 1.0b1. Thanks to Henry Ho!
    * Added the DocBook formatter. This will let you generate DocBook markup
      by writing simple wiki pages. It needs PyXML.
    * It is now possible to customize parts of the UserPreferences page in
      your wikiconfig (changing defaults, disabling fields, removing fields):
      * Use user_checkbox_* for the checkboxes.
      * Use user_form_* for other fields.
      * See MoinMoin/multiconfig.py for the built-in defaults.
    * New standalone server classes: ThreadPoolServer using pool of
      threads, ThreadingServer with thread limit and ForkingServer.
    * New standalone server configuration options: serverClass,
      threadLimit, requestQueueSize.
    * Use "PythonOption Location" in mod_python setup to solve script_name
      problems.

Developer notes:
    
    * Theme can now override maxPagenameLength() method to control page
      name shortening.
    * A search Match now provides access to the full re match via
      the re_match attribute (use to access groups of the match)
    * Underlay is not managed by arch any more. The tree contains an
      underlay tarball, and you should untar after you update from main.
    * "make update-underlay" will untar underlay
    * "make merge" will star-merge main into your tree
    * "make test" will now create and run in a fresh testwiki instace
    * "make clean" options added
    * _tests module does not have a global request any more. To refer to
      the current request in a test, use self.request.
    * _tests.TestConfig class require a request in the constructor.
    * "python tests/runtests.py test_module" will run only test_module
    * request.cfg stays between requests (for persistent servers).


Version 1.3.4 (2005-03-13, Revision moin--main--1.3--patch-666)

Fixes:

    * Fixed ACL check in LikePages macro that caused links to unreadable 
      pages to show.
    * Fixed ACL check in newpage action.
    * Fixed a security problem when admin policy defined in a custom
      SecurityPolicy class was ignored.
    * Fixed ACL check in action=show so that a user who may not read a page
      also can't find out WHEN the protected page was updated.
    * Workaround on Windows 95, 98, ME in order to clear the dircache.
      This fixes some bugs related to an outdated page list and newly created
      pages that did not appear immediately.
    * Fixed decoding issues of page names on Windows, finally.
      http://moinmoin.wikiwikiweb.de/MoinMoinBugs/BrokenUmlautsInLinksIn131
    * Fixed traceback on IIS.
      http://moinmoin.wikiwikiweb.de/MoinMoinBugs/request%2epy_broken_on_IIS
    * Fixed wikirpc for standalone server.
    * Other fixes (encoding and str/unicode data type related) to wikirpc
      server, fixing some non-ascii issues hopefully.
    * Fixed broken query strings for Standalone installations.
    * Fixed backlinks - the result did not always show all links, often it 
      showed too many irrelevant matches (MoinMoinBugs/BacklinksAreBroken).
    * Fixed the acceptance of the show_hosts setting. Now you should be able
      to hide any IP or host name from being published by MoinMoin by enabling
      this option.
    * Fixed wrong line endings on email messages.
    * Fixed MoinMoinBugs/StandaloneUnquotesTooMuch.
    * Fixed crash when trail file is missing.
    * Fixed a traceback when searching for single ( or ).
    * Added mig10 script to fix crashes with uncoverted edit-locks and file
      attachments. Just use it as you did with mig1..mig9 before.
    * Added mig11 script to add __init__.py files to data/plugin (and below).
    * added some fixes for the xslt parser (thanks to fanbanlo), it might be
      still broken, but someone with deeper knowledge about xslt should fix it.
    * Replaced image link with W3C's "html 4.01 compliance" icon by a simple
      text link to avoid https: or config trouble.
    * Catch OverflowError backtrace when illegal date strings (e.g. <1970 or
      >2038) are fed to moinmoin's time routines. It will just output current
      date / time in those cases.
    * UserPreferences now also set a date_fmt preference and Date macro
      honours it. You may have to reset your UserPreferences value for that.
    * Fixed free parent and subpage links in interwiki notation.
      http://moinmoin.wikiwikiweb.de/MoinMoinBugs/FreeParentLinksAreBroken
    * Fixed a traceback for invalid ReST markup.
    * Fixed UnicodeError in SystemAdmin's Attachment Browser.

Other Changes:

    * Optimized the IRC parser.
    * Support for zipimport of the MoinMoin package. This allows you to use
      py2exe and similar programs.
    * Show the editor's name in the mail subject.
    * Added the pragmas description and keywords. They will add <meta> headers
      if used.
    * Added MoinMoin/scripts/xmlrpc-tools/putPageTest.py example script, useful
      as a starting point for importing data using wiki xmlrpc.
    * Optimised display on Opera browser.

New features:

    * The search modifier "linkto:" was introduced. You can use it to search
      for links.
    * The NewPage macro now can take a PageTemplate parameter, see HelpOnMacros.
    * New config settings (so you don't need to edit wikirpc.py any more):
      xmlrpc_putpage_enabled = 0 (if 1, enables writing to arbitrary page names)
      xmlrpc_putpage_trusted_only = 1 (if 0, doesn't require users to be
       authenticated by http auth - DANGEROUS, DO NOT SET TO 0!!!)
    * Added support for Digest and NTLM authentication with CGI (e.g. if you
      use those Apache modules)
    * The datetime string accepted by Date and DateTime macros was extended to
      accept a timezone specification, so now +/-HHMM is also valid, e.g.:
      2005-03-06T15:15:57Z (UTC, same as +0000)
      2005-03-06T15:15:57+0000 (UTC)
      2005-03-06T16:15:57+0100 (same time given as local time for time zone
                                with offset +0100, that is CET, e.g. Germany)
      2005-03-06T10:15:57-0500 (same time given as local time for time zone
                                with offset -0500, EST, US Eastern Std. Time)
      The values given as macro argument will be transformed to UTC internally
      and then adapted again according to viewing user's UserPreferences, so
      the user will see the same moment in time but shown in his local time
      zone's time (at least if he set his UserPreferences correctly and didn't
      forget changing them twice a year for DST and non-DST).
    * Readded (now optional) editlink footer to Include macro. Add
      ',editlink' to call to enable this.
    * star "smileys" e.g. {*}{*}{*}{o}{o}


Version 1.3.3 (2005-01-24, Revision moin--main--1.3--patch-595)

Fixes:

    * fixed ACL security problem in search
    * fix for IIS with CGI allowing page names that contain chars
      that are not in the system code page
    * fixed MoinEditorBackup revisions to start with 1 now
    * improved page locking ('current' file)
    * Unittests (normally shown at end of action=test output) are currently
      disabled for everything except CGI, because they only work reliably with
      CGI, giving wrong results for other request methods.


Version 1.3.2 (2005-01-23, Revision moin--main--1.3--patch-587)

Fixes:

    * ACL bugfix for deleted pages with ACL protection.
    * ACL bugfix for "Default" acl.
    * Fixed updating of groups and dicts
    * Python 2.2.x related fixes (worked on 2.3+)
      * Fixed traceback in RecentChanges.
      * Fixed traceback with links browser.
    * Fixed 0 revision display in 'Show changes'.
    * Fixed traceback in Antispam which occurred when it could not connect
      to MoinMaster. Log the errors to stderr or error.log.
    * Fixed bug in Page init (no date, use rev). Fixes problem with
      #deprecated PI.
    * Fixed empty lists in empty search results.
    * Cosmetic fix for modern theme (when viewed with Internet Explorer).
    * Fixed migration 9 script, do not drop newline, do not drop error.log, 
      note about missing error.log.
    * Fixed repair_language.py script, keep ending newline on revisions.
    * Show headings and macro content in correct direction when mixing content 
      in several directions in the same page and using caching.
    * Fixed bug in standalone re farmconfig.
    * Fixed DOS condition in antispam code.
    * Use smaller margin in print mode to get better results with 
      Mozilla/Firefox.
    * Fixed some user input escaping issues.
    * Fixed a problem when one wiki plugin override other wikis plugins in 
      same farm.
    * Fixed some broken tests.
    * Fixed recursive include in pstats.
    * Fixed bug in standalone - HTTP result code was 200 even when the access
      was forbidden.
    * Fixed traceback when trying to login with non-ascii password.
    * Fixed traceback when xml is not available, reported on Python 2.2.?
    * Fixed slideshow to show slides in sorted order again.
    * Fixed serving multiple wikis on same IP/different ports with twisted and
      farmconfig.
    * It is possible to run with data_underlay_dir = None for special
      application, but be aware that the wiki won't be usable unless you have
      at least some of the system pages from underlay/ available.
    * Files with Unicode characters in their filename are possible now.
    * Bugfix for broken [:page#anchor:text] links.
    * Workaround an instability of the gdchart module leading to
      stalled servers etc.
    * Fixed some event-log decoding issues that affect charts rendering.

Other changes:

    * Major speed improvement over 1.3.1. Many times faster title search,
      creating new page, opening page editor and any operation that list pages.
      See http://moinmoin.wikiwikiweb.de/MoinBenchmarks
    * Improved README.migration.
    * Cleaner design for login/register interface, login is always the default
      button when the user click Enter.
    * If there are problems found in the configuration, log the error
      and display helpful error messages in the browser.
    * More forgiving unicode configuration policy, you must use the u'string' 
      format only for unicode values.
    * Added profiling to CGI.
    * The content of farmconfig.py is similar to wikiconfig.py now.
    * Unexpected errors while loading cache files are logged.
    * i18n for icon ALT tags.
    * Include request initialization code in the profile in standalone server.
    * When creating new theme, style sheets are inherited correctly, no need
      to override style sheets just to get them working.
    * Many times faster plugin system. Typical pages are about 35% faster, 
      pages with many plugins can be many times faster. 
    * Spiders are allowed to fetch attachments.
    * Old user files containing password hash encoded in pre 1.3 charset
      are auto repaired on first login.
    * data_dir defaults to './data', underlay_data_dir to './underlay' now.
      It is a good idea to replace those by absolute pathes in wikiconfig.py.
    * Renamed "Refresh" to "Delete Cache" - it was misused by users. The action 
      was also moved into the action menu in the modern and rightsidebar themes.
    * Added a workaround for TableOfContents missing some links by making it
      uncacheable via a "time" dependency.
    * Removed interwiki icon and title attribute for wiki:Self:... links.
    * Unittests (normally shown at end of action=test output) are currently
      disabled because they worked unreliably, giving wrong results sometimes.

New features:

    * Create new pages easily using configurable interface and page templates 
      with the new NewPage macro.
    * ReStructuredText (rst) support is built-in now. See HelpOnParsers.
    * New experimental feature in mointwisted.py - each interface may 
      specify a port: '12.34.56.78:80'. Without a port, the port option
      is used.

API changes:

    * For a complete list of changes, see MoinMoin:ApiChanges.
    * wikiutil.importPlugin's first argument is now a wiki config instance 
      (request.cfg) and there is no path keyword.
    * Wiki plugins always override MoinMoin plugins. wikiutil.importPlugin
      implements this override.
    * util.pysupport.importName does not accept path - you should call 
      it with correct module name, e.g 'wikiconfig.plugin.parser.wiki' for 
      wiki plugins, or 'MoinMoin.parser.wiki'. 
    * wikiutil.extensionPlugin was renamed to wikiPlugins and it gets config 
      instance instead of path.
    * New function wikiutil.importWikiPlugin used to import wiki plugins 
      using a cache in a thread safe way.
    * New config option config.use_threads is used to activate thread 
      safe code.
    * New keyword arguments for getPageList, enable 10X faster operation
      for common cases by controlling page filtering.
    * New up to 100X times faster getPageCount


Version 1.3.1 (2004-12-13, Revision moin--main--1.3--patch-434)

Fixes:

    * Fixed "Error Cyclic usage" crash when user had Italian (it), Korean
      (ko), Serbian (sr) or Vietnamese (vi) as user interface language.
    * Fall back to en (instead of crashing) when user uses a language moin
      does not support / does not support any more (like pt,sv,fi,sr).
    * In 1.3.0, people accidentally put iso-8859-1 chars into wiki configs,
      but those where expected to be pure utf-8 and thus it crashed.
      Fixed by using unicode strings (varname = u'whatever'), a matching
      encoding setting (see top of script comment) and, when decoding strings,
      using decode to ASCII with replace mode (this replaces non-ASCII chars,
      but at least it won't crash - and you get a warning to better use
      Unicode strings).
    * Fixed long time broken table formatting. ||<style="see css spec" a||b||
      Now even generates valid HTML! The old markup for align, valign, width,
      bgcolor still works, but synthesizes style attribute data.
    * SystemAdmin macro shows attachments of ALL pages now.
    * Users without write acl rights will be able to see attachments again and
      also have AttachFile action in menu.
    * Fixed wrong match count in search results, find all matches in page 
      titles, show all matches in contents in some rare cases.
    * Run about 200% faster with long running processes (standalone, Twisted), 
      about 20% faster with cgi, by better internal data handling in wikidicts.
    * On SF, the dict files use utf-8 encoding now. We included them also in
      distribution, see contrib/dict/.
    * Fixed permissions to shared template stuff.
    * Speeded up search, fixed wrong match counts.
    * Speeded up internal data handling (wikidicts).
    * Fixed rare unicode error after deleting a page (reported only on SuSE
      Linux 9.0 / Python 2.3.0).
    * Fixed file permissions of files in the data dir.  
    * Fixed some cosmetic problems in migration scripts and use sys.path.insert
      to get latest moin code when executing them.

Other Changes:

    * Improved docs, system and help pages.
    * Updated translation files.

Known Bugs:

    * Internet Explorer renders our HTML/CSS in a suboptimal way.
      (MoinMoin:MoinMoinBugs/InternetExplorer)
      Workaround: use a non-broken browser like FireFox / Mozilla.
      Fixed in MoinMoin 1.3.2.
    * Passwords using non-ascii do not work.
      (MoinMoin:MoinMoinBugs/NonAsciiPasswordsBroken)
    * The TOC macro is broken partly.
      (MoinMoinBugs/TableOfContentsBrokenForIncludedPages,
       MoinMoinBugs/TableOfContentsLacksLinks)
    * See also: http://moinmoin.wikiwikiweb.de/MoinMoinBugs
      

Version 1.3.0 (2004-12-06, Revision moin--main--1.3--patch-400)

    As you see from the length of the 1.3 changes below, 1.3 is a major(!)
    upgrade. We could have also named it "2.0", but we decided against.
    So take the time for reading the informations thoroughly and do the
    migration exactly as we tell you - this is no 5 minutes upgrade!

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!! We heavily changed configuration, data encoding, dir layout:    !!!
    !!!  * the default encoding changed to utf-8.                       !!!
    !!!  * also, we changed the escaping for special chars to %XX%YY in !!!
    !!!    URL and (xxyy) in file system.                               !!!
    !!!  * layout of data dir changed completely                        !!!
    !!! If you upgrade an existing wiki, you must run the migration     !!!
    !!! scripts or you will get data corruption or other problems.      !!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    HINT: Upgrading your wiki - critical information

      If you are NOT starting from scratch, you MUST convert your existing
      data - see README.migration for details.

      If you use ##language: xx comments on your OWN pages, you should also run
      repair_language script. Not needed for help/system pages as we already
      have done that for you.

      MoinMoin uses Unicode internally now (UCS-2 with 16 bits or UCS-4 with
      32 bits, depending on your Python installation). The encoding used
      for page files and html output is set by config.charset.

      Moin 1.3 uses utf-8 encoding only, there is NO SUPPORT for using a
      charset different from utf-8 with 1.3. If you try, you are on your own.

    Directory layout

      Directory layout was heavily changed. Each page now is a directory,
      containing page revisions, attachments, cache files and edit-log.
      
      You can delete a page or move a page from one wiki to another
      easily. Look at the wiki/data directory to see.
      
      Example:
        old: data/text/FrontPage
        new: data/pages/FrontPage/revisions/00000042
             data/pages/FrontPage/current (contains: 00000042)
        old: data/backup/FrontPage.xxxxxxxx
        new: data/pages/FrontPage/revisions/00000023

      For cleaning up cache files, use MoinMoin/scripts/cachecleaner.py 
      (see comments in script).

   Python / Libs
      
      * For using RSS, you need to have PyXML installed:
        Python 2.4*   -> PyXML 0.8.4 (cvs version)
        Python 2.3.x  -> PyXML 0.8.3
        Python 2.2.2+ -> ???
        This will also make "Live Bookmarks" of Mozilla Firefox working.
        New: if you don't have PyXML installed, the RSS icon on RecentChanges
        will not be displayed any more. Python with no PyXML installed
        generates invalid RSS XML.

   Page names handling

      * Handling of special characters in file names changed from _xx format
        to (xx...) format.
      * In URLs, moin now uses %xx%yy quoting, (because this is supported by 
        browsers), and sub pages use "/" instead of the ugly "_2f".
      * Underscore character "_" is used now as a space character " " both 
        in file names and URLs. " " and "_" will be handled equivalent at most
        places in the future (represented as "_", rendered as " ").
      * To prevent wiki abuse and user typing errors, page names are normalized 
        in URLs, query strings, the "go" box and when renaming pages. This 
        include leading, trailing and multiple slashes and white space. Certain 
        invisible unicode characters are removed from page names.
      * Group page names are restricted even more, any non unicode alpha-numeric
        character is removed. This is done to enable changing acl syntax in 
        the future. The restriction might be loosen on future versions.
      * You can edit config.page_invalid_chars_regex to control which characters
        are allowed in page names (Changing it is not supported).
      * When you enter page name, it is normalized and you are redirected to
        the normalized page, or if nothing left (e.g '/////'), to FrontPage.
      * When renaming a page to a name that can be normalized to an empty string,
        the new page name will be "EmptyName" and the user will not get an
        error message.
       
   Underlay directory

     * Pages (especially system and help pages) are now located in an underlay
       directory (data_underlay_dir). You will see the pages there if they are
       NOT covered (overlayed) by a page in the normal pages directory
       (as set using data_dir).
       MAKE SURE THAT data_underlay_dir IS CORRECT OR YOU WILL SEE MANY EMPTY
       PAGES ONLY IN A NEW WIKI.
     * If you edit a page that is shown from underlay directory, it will be
       copied to the normal page directory on save (copy-on-write).
     * You can use one copy of the underlay directory shared by many
       wiki instances. Each wiki will then have only your local, self-made
       wiki pages in its data directory, and only system and help pages in the
       single, shared underlay directory - this simplifies upgrades a lot.
     * It is recommended to keep your underlay system and help pages immutable
       using acl, so you can upgrade your wiki easily. The default help and
       system pages already have those ACLs (using MoinPagesEditorGroup).
     * Do not forget to remove your old help and system pages after migrating
       your wiki. We don't provide a script for that as that would be
       dangerous for edited pages. Just use some file manager (e.g. mc) to
       clean the data/pages/ directory. As soon as you have removed the
       system pages there, you will see the new pages in the underlay dir.
       See the EditedSystemPages page for a list of pages that exist in both
       data and underlay directory (use this page as admin!).

       When updating from 1.2 or lower to 1.3 or higher, you will want to
       clean out the copies of the system pages in your {{{wiki/data}}}
       directory. All of these pages will now reside in the underlay
       directory. If you have system pages from 1.2 or lower in your
       wiki/data/ directory, they will overshadow the more up-to-date
       documentation. This can be done using the following manual procedure:
       1. You have just converted from 1.2 or lower to post-1.3.
       2. Go to your wiki's EditedSystemPages.
       3. Find all the pages that are MoinMoin system or help pages. You will
          know if it is one of those pages because it is not your page.
       4. Check if it is okay to delete by either:
          1. Using the this page "info" link and check the Revision History to
             see if it is greater than 1. If so, there are modifications, so do
             not delete the page and evaluate the modifications to see if they
             are necessary.
          2. Using your file browser (Windows Explorer, etc) to go to your
             wiki/data/<<systemPage>>/revisions/ directory and to see if there
             are no modifications. If there are, do not delete the page and
             evaluate the modifications to see if they are necessary.
       5. Delete that wiki/data/<<systemPage>> using your file browser.

    Multiple languages

      * New file name quoting method allow 50% longer page names in languages
        that use more than one byte per character, like Hebrew, Korean etc.
      * Configuration file uses 'utf-8' encoding now. Certain values that are
        marked with [Unicode] can use any character in your language. Examples 
        are page names in navi_bar, page types regular expressions and site name.
      * For configuration examples adopted to your language, check ConfigMarket 
        in the MoinMoin wiki.
      * The system and help pages that come with moin are now in utf-8.
      * MissingPage system page localized, should display in your language.
      * We did many i18n (translation) updates.
      * CSS file use utf-8 encoding. User css is also expected to be utf-8.
        This is relevant only if you use non-ASCII values in the CSS file.
      * config.upperletters and config.lowerletters were removed.
        We now use a pre-made ucs-2 spanning set and you usually don't have to
        change it. See MoinMoin/util/chartypes.py if you're interested.
      * ACL works with any user name or group name in any language, even names 
        with spaces.
      * Now you can use any charset in config.charset. Note: only utf-8 is 
        a supported configuration!
      * Improved url handling, now creating pages directly from the browser 
        url box with non-ascii names works in most cases, even when 
        config.charset is not utf-8.
      * When using non-utf-8 config.charset, characters in URLs that does
        fit in the charsets are replaced with "?" (instead of crashing).
      * All themes and most macros and actions are Right to Left friendly.
        Full RTL support planned for 1.3 release.
      * If page language is specified with #language processing instruction
        the page is displayed in the correct direction. Pages without
        language are displayed using the wiki default_lang.

    Multiple configurations

      * You can run multiple wikis from the same wiki directory or server. 
        For example, you can run one Twisted server that serve multiple wikis, 
        instead of running multiple servers. Samples of the new configuration
        are supplied in wiki/config/*.
      * You can't just use your old moin_config.py file. It is now called
        wikiconfig.py and the config variables now have to be in a class
        "Config" and that class must inherit from
        MoinMoin.multiconfig.DefaultConfig - see the provided wikiconfig.py
        sample for details.
        This is very useful, e.g. you could derive a GermanConfig from
        DefaultConfig. After that, you can derive configs for wikiA and wikiB
        from that GermanConfig.
      * farmconfig.py contains a mapping attribute called "wikis" with pairs of
        wikiconfig module name and regular expression. The regular expression
        is matched against the URL of the request and the first matching entry
        determines the config module to be imported by MoinMoin.
      * If you use farmconfig.py's "wikis" mapping, then any wiki has a private
        config module, named after the wiki - e.g. wiki named moinmoin would
        use moinmoin.py.
      * If you only have a single wiki, you do not need farmconfig.py. just make 
        a wikiconfig.py and it will be used no matter what URL is requested. 
      * There is one common global "config" that holds sitewide settings (like
        umask or charset) - you do not need to change settings there.
        This file is located in the MoinMoin code: MoinMoin/config.py.
      
    General configuration

      * SecurityPolicy now uses "write" instead of "edit" (so it is may.write
        now). This is to get it in sync with ACLs.
      * SecurityPolicy now automatically can use everything in acl_rights_valid.
      * There is a new config option "config_check_enabled". It will warn about
        any unknown variable name (probably typo) to stderr or error.log. 
        If something doesn't work at all and changing the config does no 
        difference, switch it on and look at the error message. 
      * The sample config file comes with config_check_enabled = 1. If you 
        introduce additional variables yourself, you definitely want to switch 
        that check off or it will fill your log.
      * If you define "page_front_page" variable, this name will show in the 
        navigation bar now, instead of the default "FrontPage".

    New search engine

     * Full text and title search do support multiple search terms now - 
       see HelpOnSearching for details.
     * Regular expressions are still supported but have to be turned on per
       search term. Search terms in macros using regular expressions will have
       to be fixed.
     * The URL interface of the search engine has also changed. Links that 
       point directly to search actions may be broken.

    User names

      * User names can not use group names, even if ACLs are not enabled.
        This will prevent error later, if you start to use acl in the future
        (acl is going to be mandatory in 1.5).
      * User names are not restricted any more to only CamelCase. 
      * To prevent imposing as other users, leading, trailing and multiple 
        whitespace in user names is not allowed. Only Unicode alpha numeric 
        characters are allowed, with optional one space character between 
        words.
      * When a user name with a group name or "bad" name is trying to 
        access the wiki, he is redirected to the UserPreferences page and 
        asked to create a new account.
      * When trying to login or create a new account with a bad name, 
        correct error message is displayed in all cases.   

    CGI

      * You can not use your old moin.cgi file, as we removed cgimain.py 
        (was deprecated since 1.2). Copy the new file from the server dir.     

    Moin servers - Twisted and standalone

      * Configuration self checking on startup. Will raise an error in case
        of bad configuration or non-accessible directories.
      * Both use shorter and identical configuration options.
      * Server scripts contain detailed comments and examples.
      * Configuration defaults changed to fit most users.
      * There is memory profiler option for debugging, switched off by default.
      * If you perform a standard install, server scripts should run out
        of the box or with minimal change.

    Twisted server

      * All code moved into the new server package, the server script
        contains only configuration options.
      * Listen to more than one interface with "interfaces" list.
      * Code updated to new Twisted API.
      * Use mointwisted script to start and stop the server, using 
        "mointwisted start" and "mointwisted stop".
      * The Twisted server runs as daemon by default.
      * All moin Twisted files are called now mointwisted instead of 
        moin_twisted.
      * Fixed getting username from Twisted request (http auth)

    Standalone server

      * Configuration moved from moin_config.py to moin.py.
      * If run as root, you can set both user and group for the server.
      * Can use logfile instead of logging to stderr.
      * Fixed missing unquoting of query string (caused problems in rare cases).

    mod_python server

     * moin_modpy server files renamed to moinmodpy.

    Wiki Markup

     * '''strong''', ''em'' and __underline__ have now paragraph scope. You can
       set these attributes on words level. For multiple paragraphs, wrap each 
       with needed markup.
     * If you leave unclosed ''', '' and __  markup, its is closed when the 
       paragraph ends.

    User interface

     * Due to many changes in CSS files, the wiki may look "broken" until
       your reload once or twice, or empty your browser cache.
     * The "Send mail notification" checkbox is replaced by "Trivial change"
       checkbox. The default behavior did not change - regular edit is not
       a trivial change, and mail will be sent to subscribes. If you check
       trivial change, mail will be sent only to users who selected to 
       get trivial changes in their user preferences.
     * New theme "modern" has been added, and used as default theme. 
     * classic and rightsidebar improved.
     * viewonly theme removed, as any theme can be use now as viewonly
       by using #acl All:read in the wikiconfig.
     * All themes use new navibar, displaying both wiki links, user links
       and the current page.
     * navibar and pagetrail use now shortened page names, so very long
       names does not break the interface visually.
     * All themes have improved search interface at the top of the window.
     * Only avaiable actions are displayed, so most situations when a user
       try to do something he can't do are prevented.
     * When creating a new page, no action is available until the page 
       is created. You can't attach files to non-existing page any more.
     * Non registered users get a "login" link. Registered uses get
       "username" link to their home page, and "user preferences" link.
     * Messages more clear using bold type, designed by css.
     * Few useless messages removed (but there are many more)
     * Default wiki logo uses the wiki name instead of the MoinMoin troll 
       logo.

    Other fixes and changes
    
     * Most generated html code is valid "html 4 strict". There are still
       some problems that still have to be fixed, mainly macros, table
       attributes, and inline markup crossing (<a><b></a></b>).
     * WantedPages can include and exclude system pages, which makes it 
       much more useful.
     * Fixed a bug in TitleIndex where not all system pages are excluded.    
     * RenamePage action now renames everything, including backups, page
       history, attachments. It does not change toplevel editlog, though.
       After you rename a page, you are redirected to the new page.
     * Syntax colorization supports more languages (Java, C++, Pascal)
     * Inline: display of attachments was extended. A Parser now knows which
       extensions it can handle.
     * TableOfContents and Include macros now cooperate a bit better. There
       are still problems with multiple Includes of the same page.
     * Excluded actions at bottom of page are not displayed any more.   
     * Editor: removed the columns size setting, just using 100% of browser
       window width (it didn't work because of that anyway). Also removed that
       "reduce editor size" link at top of editor as you would lose your
       changes when using it.
     * Removed the option to choose text smileys instead of images, this made
       more trouble than it was worth. The text version is still given in ALT
       attribute.
     * Moved stuff from contribution/ to MacroMarket page on MoinMoin wiki
     * Some nasty people try to use a running moin as a proxy (at least they
       did on moinmaster.wikiwikiweb.de:8000, maybe due to the magic port
       number). We changed the code to check for that and just return 403
       in that case. Moin can not be used as a proxy anyway.
     * moin.cgi?test was removed in favor of a new buildin test
       action. It works for all deployments, just use ?action=test.
     * Sending mail does use tls if server supports it.

    3rd party developer notes

     * Themes should be now sub class of MoinMoin.theme.ThemeBase. Sub
       classes will get automatically all new improved user interface
       elements for free.
     * Theme authors should update their theme for 1.3. Some keys removed
       from them dict. See ThemeBase class in MoinMoin/theme/__init__.py. 
     * Actions writers should call request.setContentLangauge with the 
       correct language used by the action. This enable themes and other
       code to use correct direction.
     * The Formatter interface was changed. Formatters and parsers using 
       the formatter interface have to be adjusted.
     * started deprecation of Processors: they are still recognized, but
       implementors should start to rewrite their Processors as Parsers.
       A processor with the same name as a parser in a pre #! section is
       currently preferred. This will change in the next release.

    Deprecation notes

     * Processors are deprecated, see section above.

     * Using the cookie (or the login url with ID) only and not setting (or
       setting and not remembering) your email/password in UserPreferences
       is DEPRECATED. Those quite unsecure methods will likely be dropped
       in next moin version.

     * Operating with acl_enabled = 0 is also DEPRECATED. Due to some other
       improvements planned, we will have to operate with ACLs enabled ONLY
       in a future moin version, so this setting will likely be dropped.
       So clean up your user accounts (see moin_usercheck.py) and switch ACLs
       on NOW.
       There are no drawbacks, so you will like it. Having ACLs enabled
       doesn't mean you really have to USE them on wiki pages...

     * allow_extended_names = 0 is deprecated (default was/is 1).
       Future versions will be able to use extended names (aka free links) in
       any case and the config setting will be removed.

     * allow_subpages = 0 is deprecated (default was/is 1).
       Future versions will be able to use subpages in any case and the config
       setting will be removed.

     * attachments = {...} - we would like to remove that setting because of
       several reasons:
       * when not being extremely careful, this can easily lead to security
         problems (like when uploading a .php exploit and then executing it
         by accessing it directly via web server)
       * makes code more complicated - code that we want to change completely
         in next version
       If you need that feature, speak up now and tell us your reasons WHY you
       need it.


Version 1.2.4 (2004-10-23, Revision 1.187)

This will probably be the last 1.2.x release as we are soon doing release
candidates for 1.3 release (with big internal changes) and are expecting
release 1.3 in december 2004.

Fixes:
    * fixed "None" pagename bug in fullsearch/titlesearch
    * fixed projection CSS usage
    * the compiled page is removed when a page is deleted, so no ghost page
      appears after deletion
    * fixed AbandonedPages day-break problem
    * fixed [[GetVal(WikiDict,key)]]
    * the msg box is now outside content div on PageEditor, too
    * privacy fix for email notifications: you don't see other email addresses
      in To: any more. mail_from is now also used for To: header field, but
      we don't really send email to that address.
    * privacy fix for /MoinEditorBackup pages that were made on previews of
      pages that were not saved in the end
    * fix double content div on PageEditor preview

Other changes:
    * workaround for broken Microsoft Internet Explorer, the page editor now
      stops expanding to the right (e.g. with rightsidebar theme).
      Nevertheless it is a very good idea to use a non-broken and more secure
      browser like Mozilla, Firefox or Opera!

    * from MoinMoin.security.antispam import SecurityPolicy in your
      moin_config.py will protect your wiki from at least the known spammers.
      See MoinMoin:AntiSpamGlobalSolution for details.

    * xmlrpc plugin for usage logging, currently used for antispam accesses

    * (re-)added configurable meta tags:
        * html_head_queries = '''<meta name="robots" content="noindex,nofollow">\n'''
        * html_head_posts   = '''<meta name="robots" content="noindex,nofollow">\n'''
        * html_head_index   = '''<meta name="robots" content="index,follow">\n'''
        * html_head_normal  = '''<meta name="robots" content="index,nofollow">\n'''

    * i18n updates/fixes

    * New UserPreferences switch:
      you may subscribe to trivial changes (when you want to be notified about ALL
      changes to pages, even if the author deselected to send notifications).

    * New AttachList and AttachInfo macros - thanks to Nigel Metheringham and
      Jacob Cohen.

Version 1.2.3 (2004-07-21, Revision 1.186)

Fixes:
    * fixed NameError "UnpicklingError" in user.py
    * fixed version number in moin.spec
    * reverts done by bots or leechers
      There was a bad, old bug that triggered if you did not use ACLs. In that
      case, moin used some simple (but wrong and incomplete) function to
      determine what a user (or bot) may do or may not do. The function is now
      fixed to allow only read and write to anon users, and only delete and
      revert to known users additionally - and disallow everything else.
    * avoid creation of unneccessary pages/* directories
    * removed double content divs in general info and history info pages
    * fixed wiki xmlrpc getPageHTML
    * fixed rightsidebar logout URL, also fixed top banner to link to FrontPage
    * use config.page_front_page and .page_title_index for robots meta tag
      (whether it uses index,follow or index,nofollow), not hardcoded english
      page names
    * ACL security fix for PageEditor, thanks to Dr. Pleger for reporting
    * default options for new users are same as for anon users

Version 1.2.2 (2004-06-06, Revision 1.185)

Fixes:
    * python related:
     * own copy of difflib removed
       Until moin 1.2.1 we had our own copy of python 2.2.3's difflib coming
       with moin. This was to work around some problems with broken older 2.2
       python installations. We removed this now because if you have py 2.3,
       there is even a better difflib coming with python (and that fixes an
       extremely slow diff calculation happening in some rare cases).
       So the good news is that when you run python 2.3, you don't need to do
       anything and it will run great. If you run python 2.2.3, it will mostly
       work good and you also don't need to do anything. The bad news is that
       if you run an old and broken 2.2 installation (2.2.1, maybe 2.2.2) you
       will have to fix it on your own (just copy difflib.py from python 2.2.3
       over to your python 2.2.x installation).
       But better upgrade to python 2.3 (for debian woody, there's a backport),
       as 2.3 generally runs better and faster than 2.2.
     * scripts changed to use #!/usr/bin/env python (not /usr/bin/python2.2)

    * user accounts and ACLs:
     * we now require the user to specify a password for a new account (you
       were not able to login without a password anyway)
     * it is not allowed any more to create user accounts with user names
       matching config.page_group_regex - please check manually that you do
       not already have such users existing (like a user named "AdminGroup"):
       cd data/user ; grep name=.*Group *  # there should be no output!
     * subscription email sending now honours ACLs correctly

    * markup / rendering / user interface fixes:
     * fixed merging multiple lines indented by the same amount of blanks
     * ## comments don't break tables in two parts
     * added a "remove bookmark" link to RecentChanges
     * fixed action=titleindex (added \n after each entry)

    * RSS fixes:
     * non-ASCII characters should work now
     * RSS feed (Recentchanges?action=rss_rc) gives UTC timestamps now
     * removed attribute breaking RSS feed on RecentChanges

    * better email generation:
     * if you use python >=2.2.2, we add a Message-ID header to emails
     * if you use python 2.2.1, there is no email.Header. Instead of crashing
       (like previous moin 1.2.x releases), we just use the subject "as is" in
       that case. If it is not ASCII, this is not standards compliant.
     * If you have >=2.2.2 it will use email.Header to make standards compliant
       subject lines.
     * use config.mail_from as sender address when sending "lost my password"
       emails

    * file attachments:
     * fixed for standalone server
     * attachment URLs (when handled by moin) don't include server name
     * fixed some wrong &amp;amp; in html src
    
    * better themeability:
     * some entries in dict "d" where only present in header theme calls, some
       only in footer theme calls. Now almost all is present in both calls.
     * added some missing "content" divs so sidebar themes look better

    * fixed some crashes producing backtraces:
     * no IOError when diffing against deleted page
     * no backtrace in xml footnote generation
     * no SystemInfo crash when no editlog exists in new wikis
     * xmlrpc.getRecentChanges fixed

    * MoinMoin.util.filesys.rename is now a wrapper around os.rename that
      fixes os.rename on broken win32 api semantics

Other Changes:
    * saving traffic and load by improved robot meta tag generation:
     * "noindex,nofollow" on queries and POSTs
     * "index,follow" on FrontPage and TitleIndex (give robots a chance ;))
     * "index,nofollow" on all other pages (hopefully saving lots of senseless
       requests for page?action=...) 
     * removed config.html_head_queries (was used for same stuff)
    * added russian i18n (utf-8)
    * misc. other translation updates / fixes
    * added rightsidebar theme
    * TitleIndex now folds case, so "APage" and "anotherPage" are both under
      letter "A".
    * added macro/PageHits.py - it calculates the hits each page gets since
      beginning of logging


    * Full text and title search do now support multiple search terms - 
      see HelpOnSearching for details
 
    * The Formatter interface was changed. Formatter and parser using 
      the formatter interface have to be adjusted.

Version 1.2.1 (2004-03-08, Revision 1.184)

Fixes:
    * minimum requirement to run moin 1.2/1.2.1 is python 2.2.2
     * not: 2.2(.0), as this does not have True/False
     * not: 2.2.1, as this does not have email.Header. You maybe can work
       around that one by:
      * getting the python 2.2.x (x>=2) /usr/lib/python2.2/email directory
      * putting it into directory 'x' (whereever you like)
      * doing a sys.path[0:0] = ['x'] in moin.cgi [or other appropriate place]
      No guarantee, this is untested.
    * Twisted: the http headers missed the charset data, fixed
    * mod_python: fixes for mod_python 2.7
    * wiki/data/plugin/__init__.py added - fixes not working plugin modules
    * plugin processors work now, too
    * fixed displaying non-existent translations of SiteNavigation in footer
    * fixed zh-tw iso name (wrong zh_tw -> correct zh-tw)
    * fixed reversed diffs in RecentChanges RSS
    * fixed "last change" info in footer (wasn't updated)
    * fixed event.log missing pagename (and other) information
    * fixed horizontal line thickness >1
    * fixed setup.py running from CVS workdir
    * fixed crash when doing action=info on first revision of a page
    * fixed hostname truncation in footer
    * minor css fixes
    * fixed clear msg links (they missed quoting, leading to strange page
      names when you click on some of them)
    * fixed python colorizer processor
    * fixed quoting of stats cache filenames
    * catched "bad marshal data" error when switching python versions

Other changes:
    * updated danish (da) i18n
    * updated japanese (ja) i18n
    * added serbian (sr) i18n
    * added chinese (zh) i18n
    * added a simple "viewonly" theme based on classic theme - you can use
      this as default theme, so anonymous users won't get the usual wiki stuff,
      but a far simpler (and less powerful) user interface.
      It also displays the navibar at the left side.
    * added moin.spec for building RPMs
    * included MoinMoin/i18n/* into distribution archive (nice for translators)
    * included some stuff under MoinMoin/scripts - xmlrpc-tools and account
      checking stuff. removed some version control clutter from the dist
      archive, too.

    * code colorization was refactored and some new languages (Java, C++,
      Pascal) where added.
    * inline: display of attachments was extended. A Parser now knows which
      extensions it can handle.

Version 1.2 (2004-02-20, Revision 1.183)

New features:
    * MoinMoin now requires Python >=2.2.2., we recommend to use Python >=2.3.2
      (with 2.3.x, MoinMoin runs about 20-30% faster).
    * by refactoring request processing, we made it possible to run moin under
      persistent environments:
        * twisted-web (http://twistedmatrix.com)
        * httpdmain.py (use moin.py for starting this mini server)
        * mod_python
        * FastCGI
      Of course, CGI is still possible.
    * wiki pages will be compiled to bytecode now (by default), so no need for
      slow parsing/formatting on every view ("WASP", see caching_formats)
    * when using a persistent environment (like twisted) and WASP, you get up
      to 20x speed - compared to CGI and moin 1.1
    * added support for diffs between arbitrary revisions.
    * removed requirement of the external diff utility
    * config.auth_http_enabled (defaults to 0) - use this to enable moin
      getting your authenticated user name from apache (http basic auth,
      htpasswd) - if you enable this, your basic auth username has to be the
      same as your wiki username.
      Should work with CGI, FCGI and maybe even with mod_python.
      Does not change behaviour of moin under twisted or standalone server.
    * config.tz_offset = 0.0 sets a default timezone offset (in hours
      from UTC)
    * config.cookie_lifetime (int, in hours, default 12) sets the lifetime of
      the MOIN_ID cookie:
        == 0  --> cookie will live forever (no matter what user has configured!)
        > 0   --> cookie will live for n hours (or forever when "remember_me")
        < 0   --> cookie will live for -n hours (forced, ignore "remember_me"!)
    * added themeing and some themes (if you improve the existing themes or
      make nice new ones, please contribute your stuff!). The default theme is
      set by config.theme_default (and defaults to 'classic').
    * now supporting plugin directory for parsers, processors, themes, xmlrpc.
    * action=info now defaults to showing page revision history again
    * all actions accessing the logfile (as RecentChanges or history) are now
      much faster
    * #refresh processing instruction, config.refresh
        * config.refresh = (minimum_delay, target_allowed)
            * minimum delay is the minimum waiting time (in seconds) allowed
            * target_allowed is either 'internal' or 'external', depending on
              whether you want to allow only internal redirects or also
              external ones. For internal redirects, just use the Wiki pagename,
              for external, use http://... url.
        * #refresh 3                    == refresh this page every 3 seconds
        * #refresh 5 FrontPage          == internal redirect to FrontPage in 5s
        * #refresh 5 http://google.com/ == redirect to google in 5s
      Use very carefully! Allowing a low minimum_delay and putting a #refresh
      on RecentChanges might slow down your wiki significantly, when some
      people just let their browser refresh and refresh again. Also, it does
      cause quite some traffic long-term. So better do not use this without
      good reason! Default is None (switched off).
    * hide most UserPreferences options before user has logged in, less
      confusing for new users
    * "config.page_dict_regex" defines what pages are dictionary definitions
      Currently dictionaries are used for UserHomePage/MyDict where you can
      define key:: value pairs that get processed like @DATE@ expansion when
      saving a page. The 2 "@" will be added to your keys automatically.
      Please do not use @xxx@ strings on the right side (value), results may
      vary if you do.
      You can also access wiki dictionaries by using the internal macro
      [[GetVal(page,key)]]" - that will go to page "page" and return the
      value (right side) corresponding to "key".
      Implementation note: groups are a subset of the dictionary functionality.
    * standalone server should work now (see server/moin.py), so you don't
      need to setup apache or twisted for a local personal wiki, you only need
      python and moin for that now, no additional stuff any more!
    * if you run your wiki with charset = "utf-8" (the default is still
      iso8859-1), you might want to have a look at contributions/utf8-pages/
      to see if there are already translated system pages for your language.

Fixes:
    * new importPlugin routine (the old one didn't work correctly)
    * removed 0xA0 characters breaking utf-8
    * system page recognition now uses wiki groups (see AllSystemPagesGroup),
      fixing the long-time broken system page exclusion on TitleIndex.
    * mostly HTML 4.01 Strict compliant HTML
    * design is done by CSS now, HTML is semantic markup only 
    * removed target attribute from links, also [^NewWindow] markup - this
      is a HTML 3.2 feature and not valid in HTML 4.01
    * updated TWikiDrawPlugin to 20021003 version, with further modifications
      including source. It can draw imagemaps now and saves PNG. On display a
      GIF will be searched if no PNG is found. We recommend changing all GIFs
      to indexed PNGs cause this fallback might disappear in later versions.

      Sample code using bash and ImageMagick (be sure you know what you do):
      for draw in `find /path/to/wiki/data -name \*.draw`; do
        file=`dirname $draw`/`basename $draw .draw`
        if [ -e "${file}.gif" ]; then
          echo "Converting ${file}.gif to ${file}.png"
          convert "${file}.gif" "${file}.png"
        fi
      done

    * fixed email headers and encoding
    * Changed moin-usercheck to adhere to scripting standards; no
      proprietary config changes needed any more (added --config);
      --wikinames is now part of the usage message.
    * config.umask now defaults to 0770 - if you give world r/w access, ACLs
      could be rather pointless...

Removed config variables:
    * external_diff (not needed any more, we have internal diff now)
    * shared_metadb (wasn't implemented for long - we will re-add it, when it is)
    * title1/2 (please use page_header1/2)
    * page_icons_up

Changed config variables:
    * changed_time_fmt (removed some html and brackets around time from default)
    * html_head (default is empty string now)
    * page_footer1/2 (default is empty string now)
    * page_icons (is now a list of icon names, not html any more)
    * umask (default is 0770 now, not world r/w any more == more secure)

New config variables (see MoinMaster:HelpOnConfiguration):
    * cookie_lifetime
    * mail_login
    * page_credits
    * page_dict_regex
    * page_group_regex
    * page_header1/2
    * page_iconbar 
    * page_icons_table
    * page_license_enabled
    * page_license_page
    * theme_default
    * theme_force
    * tz_offset 

Other:
    * lots of internal code refactoring and optimization
    * began moving src code documentation to epydoc, see "make epydoc"
    * the URL for the RecentChanges RSS feed changed. It now only works with
      ...?action=rss_rc.

Known problems:
    * theme support is neither complete (although covering most important
      stuff) nor perfect - work on that will continue...
    * we removed some html from system messages (the boxes at top of page you
      get after some actions), so it currently looks less nice than before.
    * html is not completely validating and it is not xhtml - this will be
      fixed as soon as we have the infrastructure for that (other parser, DOM)
    * problems with rtl (right-to-left) languages, will be fixed in 1.3
    * if you change moin_config or switch themes, moin will still use already
      cached page content. For the config this can be fixed by touching
      MoinMoin/version.py (or simply deleting everything in
      data/cache/Page.py). If you get more annoyed by this than pleased by
      caching speedup, you can also switch off caching (see docs on
      caching_formats).

Themeing and HTML/CSS cleanup:
    * Browsers with completely broken CSS support (like e.g. Netscape 4.x) are
      no longer supported. If you still need to support them, do not upgrade to
      moin 1.2. If you still use these browsers, we recommend that you upgrade
      your browser first (Mozilla 1.5 has nice and standards compliant HTML and
      CSS support and is available as Free Software for Windows, Linux and Mac).
    * If you changed any html in code or by config you will have to check if it
      still works. For the usual stuff, look into `MoinMoin/theme/classic.py`
      and `classic/css/screen.css`. For config defaults of the html fragments,
      read `MoinMoin/config.py`. If you want to modify a theme, don't simply
      change classic, but copy or subclass it under a new theme name.
    * because of the new theme support the layout of the `htdocs` directory
      changed:
      * Instead of using icons under `img/` and css under `css/`, there will
        be an additional `themename/` directory in between, e.g. `classic/img/`
        and `classic/css/`. If you added own icons, you may have to copy them
        to the themes directory.
      * The filename of the CSS file has changed to the media type, so the
        normal one used for screen output has changed name from `moinmoin.css`
        to `screen.css`. There also were quite some changes and enhancements to
        the CSS files, so better use the new ones.
    * config.css_url was removed

Plugins:
  * we use a new plugin loader that requires a correct `__init__.py` file in
    the plugin directories. See the directory `wiki/data/plugin/` in the
    distribution archive and just copy it over to your wiki's plugin directory.


Version 1.1 (2003-11-29, Revision 1.178)

Version 1.1 requires Python 2.0 or higher, we recommend to use Python 2.2
(version 2.2.2 if that is available on your host) or even better >= 2.3.2
(with 2.3.x, MoinMoin runs about 20-30% faster).

New features:
  Configuration:
    * config.default_lang lets you set a default language for users not
      having specified language in their browser or UserPreferences
    * "config.page_category_regex" defines what pages are categories
    * replaced `config.page_template_ending` by a more flexible setting
      named `config.page_template_regex`
    * the same with config.page_form_regex (was: page_form_ending)
    * "config.page_group_regex" defines what pages are group definitions
      Currently groups are used for "user groups" (see ACLs) and "page
      groups" (see AllSystemPagesGroup).
    * robot exclusion from all pages except the standard view action,
      via the config.ua_spiders regex (reduces server load)
    * "maxdepth" argument for the TableOfContents macro
    * config.title1, config.title2, config.page_footer1,
      config.page_footer2 can now be callables and will be called with
      the "request" object as a single argument (note that you should
      accept any keyword arguments in order to be compatible to future
      changes)
    * "config.html_pagetitle" allows you to set a specific HTML page
      title (if not set, it defaults to "config.sitename")
    * navi_bar / quicklinks can now contain free-form links, i.e.
      entries of the form "[url linktext]" just like in wiki pages
    * if a quick link starts with '^', it opens in a new window; help
      now opens in a new window also
    * `config.smileys` for user-defined smileys (default: `{}`) - a dict
      with the markup as the key and a tuple of width, height, border, image
      name as the value).
    * `config.hosts_deny` to forbid access based on IP address
    * `config.mail_login` can be set to username and password separated by
      a space, e.g. "username userpass", if you need to use SMTP AUTH
    * `config.edit_locking` can be set to None (old behaviour, no
      locking), 'warn <timeout mins>' (warn about concurrent edits, but
      do not enforce anything), or 'lock <timeout mins>' (strict locking)
    * optionally showing a license text on editor page, use:
      config.page_license_enabled = 1
      Optionally use these to customize what is shown there:
      config.page_license_text = "... your text ..."
      config.page_license_page = "MyLicensePage"
      See the default values in MoinMoin/config.py for details and
      override them in moin_config.py, if needed.
    * `config.shared_intermap` can be a list of filenames (instead of a
      single string)
    * If you have added your own `SecurityPolicy`, the class interface for
      that has changed (see `security.py`).

  Authenticaton / Authorization:
    * added ACL support, written by Gustavo Niemeyer of Conectiva and
      Thomas Waldmann. See HelpOnAccessControlLists for more infos.
      You should use MoinMoin/scripts/moin_usercheck.py before activating
      ACLs or some users with bad or duplicate accounts might get into
      trouble.
    * A user account can be disabled using moin_usercheck.py or
      UserPreferences page. Disabling, but keeping it is good for edit
      history.
    * changed security default: deletion only available to known users
    * support for Basic authentication (Apache style: AUTH_TYPE="Basic",
      REMOTE_USER="WikiUserName"). If authentication is there, user
      will be in ACL class "Trusted".
    * support for username / password login
      The username / password login will ONLY work, if you define a
      password. With an empty password, username / password login is not
      allowed due to security reasons. Passwords are stored encrypted
      (format similar to Apache SHA) and can also be entered in the
      UserPreferences form in this format. When requesting login
      information by email, the password is also sent in this encrypted
      format (use copy&paste to fill it in the form).
      ...?action=userform?uid=<userid> is still possible, so if you have
      bookmarks, they will still work). The input field for the ID was
      dropped.
      NOTE: using the userid for login purposes is DEPRECATED and might
            be removed for better security soon.
    * after logging in, you will get a cookie valid until midnight.
      The next day, the cookie will expire and you will have to login
      again. If you don't want this, you can check the "remember me
      forever" option in UserPreferences.
    * if the page file is read-only, you get a message (i.e. you can now
      protect pages against changes if you're the wiki admin).
      Note: you can do that easier using ACLs.

  Markup / Macros / Actions:
    * RandomQuote macro (and even parses Wiki markup now)
    * `[[Navigation]]` macro for slides and subpage navigation
    * [[ShowSmileys]] displays ALL smileys, including user-defined ones
    * the Include macro has new parameters (from, to, sort, items) and
      is able to include more than one page (via a regex pattern)
    * `MailTo` macro for adding spam-safe email links to a page
    * if a fancy link starts with '^' (i.e. if it has the form
      "[^http:... ...]"), it's opened in a new window
     * because of that, the NewWindow macro was removed from contrib
    * "#pragma section-numbers 2" only displays section numbers for
      headings of level 2 and up (similarly for 3 to 6)
    * ../SubPageOfParent links

  User interface:
    * new fancy diffs
    * Page creation shows LikePages that already exist
    * editor shows the current size of the page
    * editor returns to including page when editing an included page
    * Visual indication we're on the editor page (new CSS style)
    * selection to add categories to a page in the editor (use preview
      button to add more than one category)
    * if user has a homepage, a backup of save/preview text is saved as
      a subpage UsersHomePage/MoinEditorBackup
    * added "revert" link to PageInfo view (which makes DeletePage more
      safe in public wikis, since you can easily revive deleted pages
      via revert)
    * Selection for logged in users (i.e. no bots) to extend the listing
      of recent changes beyond the default limits
    * Activated display of context for backlinks search
    * Subscriber list shown on page info
    * LikePages shows similar pages (using difflib.get_close_matches)
    * last edit action is stored into "last-edited" file, and
      displayed in the page footer
    * reciprocal footnote linking (definition refers back to reference)
    * "Ex-/Include system pages" link for title index
      Note: system/help pages algorithm is still mostly broken.
    * list items set apart by empty lines are now also set apart
      visually (by adding the CSS class "gap" to <li>)
    * "save" check for security.Permissions
    * Added Spanish, Croatian and Danish system texts
    * Added flag icons for the languages supported in "i18n"
    * updated help and system pages, more translations, see also
      AllSystemPagesGroup
    * there was quite some work done on wiki xmlrpc v1 and v2 - it
      basically works now.

  Tools and other changes:
    * moin-dump: New option "--page"
    * there are some scripts MoinMoin/scripts/* using wiki xmlrpc for
      backup and wiki page copying applications
    * Updated the XSLT parser to work with 4Suite 1.0a1
    * more infos in cgi tracebacks
    * UPDATE.html is a HTML version of MoinMaster:HelpOnUpdating

Unfinished or experimental features:
    * user defined forms
    * XML export of all data in the wiki
    * RST parser (you need to install docutils to use this)
    * SystemAdmin macro

Privacy fixes:
    * do not use / display user's email address in public places

SECURITY FIXES:
    * Removed two cross-site scripting vulnerabilities reported by "office"

Bugfixes:
    * Bugfix for PageList when no arguments are given
    * Disallow full-text searches with too short search terms
    * [ 566094 ] TitleIndex now supports grouping by Hangul Syllables
     * fix for multibyte first char in TitleIndex
    * Footnotes were not HTML escaped
    * Numbered code displays are now in a table so that you can cut the
      code w/o the numbers
    * Bugfix for wrong mail notifications
    * Create unique anchors for repeated titles
    * [ 522246 ] Transparently recode localized messages
    * [ 685003 ] Using "preview" button when editing can lose data
    * use gmtime() for time handling
    * fixed negative gmtime() arguments
    * [[Include]] accepts relative page names
    * fixed ||NotInterWiki:||...||

-----------------------------------------------------------------------------
Version 1.0 (2002-05-10, Revision 1.159)

THIS IS THE LAST RELEASE WITH PYTHON 1.5.2 SUPPORT! If severe bugs
should occur, a maintenance release will fix them.

Some optional features (like statistics) already require Python 2.0.

New features:
    * security fix: "allow_xslt" has to be set to 1 in order to enable
      XSLT processing; note that this defaults to 0 because XSLT is able
      to insert arbitrary HTML into a wiki
    * "action=content" for transclusion into static web pages; emits the
      pure page content, without any <html>, <head>, or <body> tags
    * "?action=links&mimetype=text/plain" works like MeatBall:LinkDatabase
    * "Preferred language" and "Quick links" user settings
    * Added "processor" concept, processors work on the data in "code
      displays" and are called by a bangpath in the first line of data
    * Processors: Colorize, CSV (see HelpOnProcessors)
    * New icons: "{OK}", "(./)", "{X}", "{i}", "{1}", "{2}" and "{}"
      (see HelpOnSmileys)
    * FullSearch now displays context information for search hits
    * DeletePage offers a textentry field for an optional comment
    * Email notifications are sent in the user's language, if known from
      the preferences
    * @PAGE@ is substituted by the name of the current page (useful
      for template pages)

Unfinished features:
    * user defined forms
    * XML export of all data in the wiki
    * RST parser (you need to install docutils to use this)
    * XMLRPC interface

Bugfixes:
    * Syntax warning with Python 2.2 fixed
    * Macro-generated pagelinks are no longer added to the list of links
    * error codes returned by "diff" are reported
    * fix for attachments on pages with non-USASCII names
    * correct handling of spaces in attachment filenames and URLs

-----------------------------------------------------------------------------
Version 0.11 (2002-03-11, Revision 1.151)

Most important new features: file attachments, definition list markup
(glossaries), change notification via email, variable substitution when
saving pages, edit preview, and improved documentation.

Note that the RSS features require a recent PyXML (CVS or 0.7) due to
bugs in the namespace handling of xml.sax.saxutils in earlier versions.
This is (hopefully) automatically detected on every installation.

Statistical features are NOT designed to work with Python 1.5.2 and
require Python 2.0 or higher. Overall, MoinMoin 0.11 is not explicitely
tested for 1.5.2 compatibility.

New features:
    * XML formatting now (most often) produces well-formed, and, depending
      on proper layout of the wiki page, valid StyleBook XML
    * Headers are now automatically numbered, unless you set the config
      item 'show_section_numbers' to 0
    * "#pragma section-numbers off" (or "0") switches that off explicitely,
      and "on" or "1" enables numbering 
    * Added a "contributions" directory for 3rd party extensions
    * AttachFile action, contributed by Ken Sugino; note that you have
      to enable this action because of the possibility of DoS attacks
      (malicious uploads), by adding this to your moin_config:
            allowed_actions = ['AttachFile']
    * "attachment:" URL scheme allows access to attachments, to get files
       from other pages use "attachment:WikiName/filename.ext".
    * New macros: Date(unixtimestamp) and DateTime(unixtimestamp) to
      display a timestamp according to system/user settings
    * Variable substitution when a page is saved, note that saving
      template pages does NOT expand variables. Supported are:
        @DATE@      Current date in the system's format
        @TIME@      Current date and time in the user's format
        @USERNAME@  Just the user's name (or his domain/IP)
        @USER@      Signature "-- loginname"
        @SIG@       Dated Signature "-- loginname date time"
        @MAILTO@    A fancy mailto: link with the user's data  
    * Copied some new emoticons from PikiePikie
        || {{{ :-? }}} || :-? || tongue.gif ||
        || {{{ :\  }}} || :\  || ohwell.gif ||
        || {{{ >:> }}} || >:> || devil.gif  ||
        || {{{ %)  }}} || %)  || eyes.gif   ||
        || {{{ @)  }}} || @)  || eek.gif    ||
        || {{{ |)  }}} || |)  || tired.gif  ||
        || {{{ ;)) }}} || ;)) || lol.gif    ||
    * AbandonedPages macro
    * Added definition list markup: {{{<whitespace>term:: definition}}}
    * Added email notification features contributed by Daniel Sa�    * SystemInfo: show "Entries in edit log"
    * Added "RSS" icon to RecentChanges macro and code to generate a
      RecentChanges RSS channel, see
          http://www.usemod.com/cgi-bin/mb.pl?UnifiedRecentChanges
      for details
    * Added config.sitename and config.interwikiname parameter
    * Better WikiFarm support:
      * <datadir>/plugin/macro and <datadir>/plugin/action can be used
        to store macros and actions local to a specific wiki instance
      * config.shared_intermap can contain a pathname to a shared
        "intermap.txt" file (i.e. one stored outside the datadir)
    * added `backtick` shortcut for {{{inline literal}}} (has to be
      enabled by "backtick_meta=1" in the config file); note that ``
      is then a shorter replacement for '''''' escaping
    * added inline search fields (at the bottom of each page)
    * Added preview to the editor, including spell checking
    * New languages: Chinese (Changzhe Han) and Portuguese (Jorge
      Godoy), updated French (Lucas Bruand), added Korean (Hye-Shik
      Chang) and Italian (Lele Gaifax)
    * New SystemAdmin macro
    * `[[Anchor(anchorname)]]` macro to insert anchors into a page,
      and [#anchorname Anchor Links].
    * User option to open editor view via a double-click
    * Added commentary field to editor, recent changes and page info
    * Page trails (user option)
    * UserPreferences: checkboxes for double-click edit, page trail,
      fancy links, emoticons, jump to last page visited, and some
      other yes/no options
    * "config.nonexist_qm" is now the default for a user setting
    * `[[GetText(text)]]` macro loads I18N texts (mainly intended
      for use on Help pages)
    * table attributes via "||<attrlist> ... ||", more details on
      http://purl.net/wiki/moin/HelpOnTables
    * PythonFaq interwiki tag and support for $PAGE placeholder
    * event logging, as the basis for future statistics
    * "moin-dump" command line tool to create a static copy of
      the wiki content
    * "config.external_diff" allows to set an exact path to the
      command, or change the name to for example "gdiff" if GNU
      diff is not a native command in your UNIX flavour
    * `[[PageSize]]` macro
    * the interwiki name "Self" now always points to the own wiki
    * config.title1 and config.title2 are inserted into the output
      right before and after the system title html code (title1
      is right after the <body> tag and normally undefined, title2
      defaults to the "<hr>" above the page contents)
    * Additional link on diff pages to ignore whitespace changes
    * Subpages (config.allow_subpages, config.page_icons_up)
    * super^script^, sub,,script,, and __underline__ markup
    * `[[FootNote]]` macro
    * many other new config options, see HelpOnConfiguration for
      a complete list
    * [[StatsChart(type)]] shows statistical charts (currently
      defined types: hitcounts, pagesize, useragents)
    * 'inline:' scheme works like 'attachment:', but tries to
      inline the content of the attachment into the page;
      currently knows about "*.py" sources and colorizes them
    * support for Java applet "TWikiDrawPlugin" via
      drawing:<drawingname> URL scheme (you need to activate
      the AttachFile action if you want drawings)
    * numeric entities (&#nnnnn;) are now optionally NOT escaped,
      which allows you to insert more characters into a Latin-1
      page, especially the Euro symbol
    * navi_bar is now a list of page names which should be linked
      on every page
    * test.cgi is now rolled into moin.cgi, and can be called
      by adding "?test" to the wiki base URL. Also, as a security
      feature, the server's environment is only shown for requests
      local to the web server.

Unfinished features:
    * user defined forms
    * XML export of all data in the wiki

Documentation:
    * extended the online help ("Help*" pages)
    * German help pages (thanks to Thomas Waldmann)

Bugfixes:
    * #425857: python Parser bug on the second call
    * #424917: Caching control
    * #465499: Two HTTPS problems
    * #491155: FrontPage hardcoded
    * Handling of inbound UTF-8 encoded URIs (only with Python >= 2.0)
    * Fix for subtle changes in "re" of Python 2.2
    * User-provided URLs are now never URL-escaped, which allows appending
      #anchors and using %20 for spaces in InterWiki links

-----------------------------------------------------------------------------
Version 0.10 (2001-10-28, Revision 1.134)

This version is still Python 1.5.2 compatible, but it's not extensively
tested for that version and some parts of the system might not work
there, especially seldom used macros and actions. Bug reports welcome!

New features:
    * "#deprecated" processing instruction
    * config entry "SecurityPolicy" to allow for customized permissions
      (see "security.py" for more)
    * added distutils support
    * though not extensively tested, the standalone server now does POST
      requests, i.e. you can save pages; there are still problems with
      persistent global variables! It only works for Python >= 2.0.
    * "bang_meta" config variable and "!NotWikiWord" markup
    * "url_mappings" config variable to dynamically change URL prefixes
      (especially useful in intranets, when whole trees of externally
      hosted documents move around)
    * setting "mail_smarthost" and "mail_from" activates mailing
      features (sending login data on the UserPreferences page)
    * very useful for intranet developer wikis, a means to view pydoc
      documentation, formatted via a XSLT stylesheet, for details see
      http://purl.net/wiki/python/TeudViewer?module=MoinMoin.macro.TeudView
      or MoinMoin/macro/TeudView.py
    * "LocalSiteMap" action by Steve Howell <showell@zipcon.com>
    * Added FOLDOC to intermap.txt

Bugfixes:
    * Full config defaults, import MoinMoin now works w/o moin_config.py
    * Better control over permissions with config.umask
    * Bugfix for a UNIX time billenium bug (affecting RecentChanges
      sorting and page diffs)
    * data paths with directory names containing dots caused problems

-----------------------------------------------------------------------------
Version 0.9 (2001-05-07)

New features:
    * XML page input (pages that start with "<?xml") and XSLT formatting
    * Page caching, for now limited to XSLT processing (where it's
      absolutely needed); new code & API to add the "RefreshCache" link
    * Selection of common date/time formats in UserPreferences
    * New action "titleindex" to support wiki introspection (MetaWiki);
      see the new links below the index bar in "TitleIndex"
    * UserPreferences: editable CSS URL for personal styles
    * PageInfo: the editor's name or IP is shown for each change
    * WantedPages: a new macro that lists links to non-existent pages
    * OrphanedPages: a new macro that lists pages no other page links to
    * Extensions to the FullSearch macro (see HelpOnMacros)
    * Python syntax highlighting
    * "DeletePage" action (has to be activated, see MoinMoinFaq)
    * "Remove trailing whitespace from each line" option in the editor
    * I18N (currently German and Swedish)
    * Config option "url_schemas" to extend the supported URL types
    * Improved tracebacks by using Ka-Ping's "cgitb"

Bugfixes:
    * The editor now sends a "no-cache" HTTP header
    * "PageList" results are now sorted
    * New config parameter "html_head_queries": send additional header
      for all pages EXCEPT the "normal" view; main usage is to have
      only the normal pages indexed by a spider, not the edit, print,
      etc. views (which cause multiple hits on the same information)
    * Store the modification time of the page file in the editlog, not
      the current time when the log entry is created

-----------------------------------------------------------------------------
Version 0.8 (2001-01-23)

New features:
    * Page templates (create a new page using a template page, by Richard)
    * Pluggable actions (by Richard)
    * Added "diff since bookmark"
    * Only "normal" URLs (outside of brackets) are converted to inline images
    * Show number of backups in SystemInfo macro
    * Show info on installed extension macros and actions
    * New macro: [[BR]] for line breaks
    * New action "LikePages" (again, Richard)
    * Highlighting of search results, and of bad words when spellchecking
    * Support for "file:" URLS
    * "SpellCheck" action (Richard, me, and Christian)
    * [[Include]] macro (you guessed it, Richard)

Bugfixes:
    * Update bookmark with load time, not click time
    * Changed CSS styles to better suit Netscape's broken handling of CSS

-----------------------------------------------------------------------------
Version 0.7 (2000-12-06)

New features:
    * RecentChanges bookmarking

Bugfixes:
    * SECURITY FIX
    * Non-greedy extended WikiNames

-----------------------------------------------------------------------------
Version 0.6 (2000-12-04)

New features:
    * [[UserPreferences]] macro and associated functions
    * [[TableOfContents]] macro
    * Mechanism for external macros (user extensions)
    * Numbered list types and start offsets

Bugfixes:
    * Search dialogs did not work on the FrontPage
    * Add newline to text if last line has none (better diffs)

-----------------------------------------------------------------------------
Version 0.5 (2000-11-17)

New features:
    * Major refactoring: code is now broken up into modules within the
      "MoinMoin" package
    * Diagnosis of installation via a "test.cgi" script
    * Smileys
    * "#format" processing instruction
    * "##comment"
    * [[RandomPage]] and [[RandomPage(number)]] macro
    * configurable footer ("page_footer1" and "page_footer2")
    * "#redirect" processing instruction

Bugfixes:
    * Bugfix for broken CGI environment of IIS/4.0
    * URLs and InterWiki links are now less greedy (punctuation at the end
      is excluded, and "<" ends them, too)

-----------------------------------------------------------------------------
Version 0.4 (2000-11-01)

New features:
    * Table markup "||a||b||c||"
    * Headlines "= H1 =", "== H2 ==", and so on up to H5
    * [[PageCount]] macro
    * Added [[Icon(image)]] macro and macro arguments
    * [[PageList(title-regex)]] macro
    * New help system (set of help pages describing all features)

Bugfixes:
    * Create complete URL for "Clear message" link
    * Inline code spans needed cgi.escape
    * Better fix for Python 1.6 "re" problems
    * Fix for uppercase extensions in inline images ("foo.JPG")
    * Fixed colspan in RecentChanges
    * HR size is now limited to 8
    * "}" ends an URL pattern (fixes URLs right at the end of code displays)

-----------------------------------------------------------------------------
Version 0.3 (2000-10-25)

New features:
    * Check for inline images with InterWiki links (Spam:eggs.gif)
    * New config variable "allow_extended_names", which enables markup for
      wiki names containing ANY character like this: ["any chars"] 
    * New config variable "html_head"
    * New macro [[SystemInfo]]
    * Added inline code ("{{{" and "}}}" on the same line)
    * Support for new config variable "max_macro_size"

Bugfixes:
    * Don't treat sequences with a double colon (CPP::Namespace) as an
      InterWiki link
    * The local part of InterWiki links is now correctly URL-escaped
    * Quickfix for a bug in 1.6's regular expressions
    * Fixed "SpamSpamSpam" bug (multiple entries in word list)
    * Anchor names get quoted in WordIndex and TitleIndex
    * Filtering of filenames in page_list() corrected
    * Escape &, <, > when sending the editor
    * Final(?) fix for japanese wiki names

-----------------------------------------------------------------------------
Version 0.2 (2000-08-26)

New features:
    * When saving, a datestamp saved in the form and that of the file are
      compared now; so, accidently saving over changes of other people is
      not possible anymore (saving still needs file locking though, for
      race conditions)
    * if the directory "backup" exists in the data dir, pages are saved
      there before a new version is written to disk
    * Removed the "Reset" button from EditPage
    * Added "Reduce editor size" link
    * Added Latin-1 WikiNames (JürgenHermann ;)
    * Speeded up RecentChanges by looking up hostnames ONCE while saving
    * Show at most 14 (distinct) days in RecentChanges
    * Added icons for common functions, at the top of the page
    * Added a printing preview (no icons, etc.)
    * Added bracketed (external) URLs
    * Added support for quoted URLs ("http://...")
    * Added styles for :visited links to CSS
    * Embed image if an URL ends in .gif/.jpg/.png
    * No markup detection in code sections
    * Grey background for code sections
    * Added handling for numbered lists
    * the edit textarea now grows in width with the browser window
      (thanks to Sebastian Dau�for that idea)
    * Added page info (revision history) and viewing of old revisions
    * Added page diff, and diff links on page info
    * Added InterWiki support (use "wiki:WikiServer/theirlocalname"; the list
      of WikiServers is read from "data/intermap.txt")
    * Added "normal" InterWiki links
    * Added "action=raw" to send the raw wiki markup as text/plain (e.g. for
      backup purposes via wget) 

Bugfixes:
    * Removed an exception when saving empty pages
    * Fixed bold nested into emphasis ('''''Bold''' Italic'')

-----------------------------------------------------------------------------
Version 0.1 (2000-07-29)

Improvements over PikiPiki 1.62:
    * Moved configuration to "moin_config.py"
    * Added "edit_rows" setting
    * Added navigation bar
    * Improved HTML formatting
    * Added timing comment (page created in xx secs)
    * ISO date and time formats by default
    * Formatted RecentChanges with HTML tables
    * Uppercase letters for the index pages
    * Added PythonPowered logo

Bugfixes:
    * Javadoc comments now get formatted properly in {{{ }}} sections
    * Remove \r from submitted pages (so we get PORTABLE wiki files)
    * chmod(0666) eases manual changes to the data dir

-----------------------------------------------------------------------------
