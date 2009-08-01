# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Package Installer

    @copyright: 2005 MoinMoin:AlexanderSchremmer,
                2007-2009 MoinMoin:ReimarBauer
    @license: GNU GPL, see COPYING for details.
"""

import os, re, sys
import zipfile
from MoinMoin import config, wikiutil, caching, user
from MoinMoin.items import Item

MOIN_PACKAGE_FILE = 'MOIN_PACKAGE'
MAX_VERSION = 1


# Exceptions
class PackageException(Exception):
    """ Raised if the package is broken. """
    pass

class ScriptException(Exception):
    """ Raised when there is a problem in the script. """

    def __unicode__(self):
        """ Return unicode error message """
        if isinstance(self.args[0], str):
            return unicode(self.args[0], config.charset)
        else:
            return unicode(self.args[0])

class RuntimeScriptException(ScriptException):
    """ Raised when the script problem occurs at runtime. """

class ScriptExit(Exception):
    """ Raised by the script commands when the script should quit. """

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

def str2boolean(string):
    """
    Converts the parameter to a boolean value by recognising different
    truth literals.
    """
    return (string.lower() in ('yes', 'true', '1'))

class ScriptEngine:
    """
    The script engine supplies the needed commands to execute the installation
    script.
    """

    def _extractToFile(self, source, target):
        """ Extracts source and writes the contents into target. """
        # TODO, add file dates
        target_file = open(target, "wb")
        target_file.write(self.extract_file(source))
        target_file.close()

    def __init__(self):
        self.themename = None
        self.ignoreExceptions = False
        self.goto = 0

        #Satisfy pylint
        self.msg = getattr(self, "msg", "")
        self.request = getattr(self, "request", None)

    def do_print(self, *param):
        """ Prints the parameters into output of the script. """
        self.msg += '; '.join(param) + "\n"

    def do_exit(self):
        """ Exits the script. """
        raise ScriptExit

    def do_ignoreexceptions(self, boolean):
        """ Sets the ignore exceptions setting. If exceptions are ignored, the
        script does not stop if one is encountered. """
        self.ignoreExceptions = str2boolean(boolean)

    def do_ensureversion(self, version, lines=0):
        """
        Ensures that the version of MoinMoin is greater or equal than
        version. If lines is unspecified, the script aborts. Otherwise,
        the next lines (amount specified by lines) are not executed.

        @param version: required version of MoinMoin (e.g. "1.3.4")
        @param lines: lines to ignore
        """
        _ = self.request.getText

        from MoinMoin.version import release
        version_int = [int(x) for x in version.split(".")]
        # use a regex here to get only the numbers of the release string (e.g. ignore betaX)
        release = re.compile('\d+').findall(release)[0:3]
        release = [int(x) for x in release]
        if version_int > release:
            if lines > 0:
                self.goto = lines
            else:
                raise RuntimeScriptException(_("The package needs a newer version"
                                               " of MoinMoin (at least %s).") %
                                             version)

    def do_setthemename(self, themename):
        """ Sets the name of the theme which will be altered next. """
        self.themename = wikiutil.taintfilename(str(themename))

    def do_copythemefile(self, filename, ftype, target):
        """ Copies a theme-related file (CSS, PNG, etc.) into a directory of the
        current theme.

        @param filename: name of the file in this package
        @param ftype:   the subdirectory of the theme directory, e.g. "css"
        @param target: filename, e.g. "screen.css"
        """
        _ = self.request.getText
        if self.themename is None:
            raise RuntimeScriptException(_("The theme name is not set."))

        from MoinMoin.web.static import STATIC_FILES_PATH as htdocs_dir
        if not os.access(htdocs_dir, os.W_OK):
            raise RuntimeScriptException(_("Theme files not installed! Write rights missing for %s.") % htdocs_dir)

        theme_file = os.path.join(htdocs_dir, self.themename,
                                  wikiutil.taintfilename(ftype),
                                  wikiutil.taintfilename(target))
        theme_dir = os.path.dirname(theme_file)
        if not os.path.exists(theme_dir):
            os.makedirs(theme_dir)
        self._extractToFile(filename, theme_file)

    def do_installplugin(self, filename, visibility, ptype, target):
        """
        Installs a python code file into the appropriate directory.

        @param filename: name of the file in this package
        @param visibility: 'local' will copy it into the plugin folder of the
            current wiki. 'global' will use the folder of the MoinMoin python
            package.
        @param ptype: the type of the plugin, e.g. "parser"
        @param target: the filename of the plugin, e.g. wiki.py
        """
        visibility = visibility.lower()
        ptype = wikiutil.taintfilename(ptype.lower())

        if visibility == 'global':
            basedir = os.path.dirname(__import__("MoinMoin").__file__)
        elif visibility == 'local':
            basedir = self.request.cfg.plugin_dir

        target = os.path.join(basedir, ptype, wikiutil.taintfilename(target))

        self._extractToFile(filename, target)
        wikiutil._wiki_plugins = {}

    def do_installpackage(self, itemename, filename):
        """
        Installs a package.

        @param itemname: item where the file is attached. Or in 2.0, the file itself.
        @param filename: Filename of the attachment (just applicable for MoinMoin < 2.0)
        """
        _ = self.request.getText

        package = ZipPackage(self.request, item_name)
        if package.isPackage():
            if not package.installPackage():
                raise RuntimeScriptException(_("Installation of '%(filename)s' failed.") % {
                    'filename': filename} + "\n" + package.msg)
        else:
            raise RuntimeScriptException(_('The file %s is not a MoinMoin package file.') % filename)

        self.msg += package.msg

    def do_additem(self, filename, item_name, mimetype='application/x-unknown', contenttype="utf-8", author=u"Scripting Subsystem", comment=u"", trivial=u"No"):
        """ Adds a revision to a page.

        @param filename: name of the file in this package
        @param item_name: name of the target
        @param mimetype: mimetype of the target default text/moin-wiki
        @param contentype: contentype default UTF-8
        @param author:   user name of the editor (optional)
        @param comment:  comment related to this revision (optional)
        @param trivial:  boolean, if it is a trivial edit
        """
        _ = self.request.getText
        trivial = str2boolean(trivial)
        if self.request.user.may.write(item_name):
            meta = {"mimetype": mimetype}
            item = Item.create(self.request, item_name)
            item._save(meta, self.extract_file(filename.decode(contenttype.lower())), name=item_name, action='SAVE', mimetype=mimetype, comment=comment, extra='')
            self.msg += u"%(item_name)s added \n" % {"item_name": item_name}
        else:
            self.msg += u"action add revision: not enough rights - nothing done \n"

    def do_renameitem(self, item_name, newitemname, author=u"Scripting Subsystem", comment=u"Renamed by the scripting subsystem."):
        """ Renames a page.

        @param item_name: name of the target item
        @param newitemname: name of the new item
        @param author:   user name of the editor (optional)
        @param comment:  comment related to this revision (optional)
        """
        if self.request.user.may.write(itemname):
            _ = self.request.getText
            # TODO ACL?
            item = self.request.cfg.storage.get_item(item_name)
            if not item.exists():
                raise RuntimeScriptException(_("The item %s does not exist.") % item_name)

            r = item.get_revision(-1)
            r.item.rename(newitemname)
            r._save(r.meta, r.data, name=newitemname, action='SAVE/RENAME', extra=item_name, comment=comment)

    def runScript(self, commands):
        """ Runs the commands.

        @param commands: list of strings which contain a command each
        @return True on success
        """
        _ = self.request.getText

        headerline = unpackLine(commands[0])

        if headerline[0].lower() != "MoinMoinPackage".lower():
            raise PackageException(_("Invalid package file header."))

        self.revision = int(headerline[1])
        if self.revision > MAX_VERSION:
            raise PackageException(_("Package file format unsupported."))

        lineno = 1
        success = True

        for line in commands[1:]:
            lineno += 1
            if self.goto > 0:
                self.goto -= 1
                continue

            if line.startswith("#") or len(line) == 0:
                continue
            elements = unpackLine(line)
            fnname = elements[0].strip().lower()
            if fnname == '':
                continue
            try:
                fn = getattr(self, "do_" + fnname)
            except AttributeError:
                self.msg += u"Exception RuntimeScriptException: %s\n" % (
                        _("Unknown function %(func)s in line %(lineno)i.") %
                        {'func': elements[0], 'lineno': lineno}, )
                success = False
                break

            try:
                fn(*elements[1:])
            except ScriptExit:
                break
            except TypeError, e:
                self.msg += u"Exception %s (line %i): %s\n" % (e.__class__.__name__, lineno, unicode(e))
                success = False
                break
            except RuntimeScriptException, e:
                if not self.ignoreExceptions:
                    self.msg += u"Exception %s (line %i): %s\n" % (e.__class__.__name__, lineno, unicode(e))
                    success = False
                    break

        return success

class Package:
    """ A package consists of a bunch of files which can be installed. """
    def __init__(self, request):
        self.request = request
        self.msg = ""

    def installPackage(self):
        """ Opens the package and executes the script. """

        _ = self.request.getText

        if not self.isPackage():
            raise PackageException(_("The file %s was not found in the package.") % MOIN_PACKAGE_FILE)

        commands = self.getScript().splitlines()

        return self.runScript(commands)

    def getScript(self):
        """ Returns the script. """
        return self.extract_file(MOIN_PACKAGE_FILE).decode("utf-8").replace(u"\ufeff", "")

    def extract_file(self, filename):
        """ Returns the contents of a file in the package. """
        raise NotImplementedError

    def filelist(self):
        """ Returns a list of all files. """
        raise NotImplementedError

    def isPackage(self):
        """ Returns true if this package is recognised. """
        raise NotImplementedError

class ZipPackage(Package, ScriptEngine):
    """ A package that reads its files from a .zip file. """
    def __init__(self, request, filename):
        """ Initialise the package.

        @param request: RequestBase instance
        @param filename: filename of the .zip file
        """

        Package.__init__(self, request)
        ScriptEngine.__init__(self)
        self.filename = filename
        # ToDo get status from the zipfile object
        self._isZipfile = True
        #self._isZipfile = zipfile.is_zipfile(filename)
        if self._isZipfile:
            self.zipfile = zipfile.ZipFile(filename)
        # self.zipfile.getinfo(name)

    def extract_file(self, filename):
        """ Returns the contents of a file in the package. """
        _ = self.request.getText
        try:
            return self.zipfile.read(filename.encode("cp437"))
        except KeyError:
            raise RuntimeScriptException(_(
                "The file %s was not found in the package.") % filename)

    def filelist(self):
        """ Returns a list of all files. """
        return self.zipfile.namelist()

    def isPackage(self):
        """ Returns true if this package is recognised. """
        return self._isZipfile and MOIN_PACKAGE_FILE in self.zipfile.namelist()

def main():
    args = sys.argv
    if len(args)-1 not in (2, 3) or args[1] not in ('l', 'i'):
        print >> sys.stderr, """MoinMoin Package Installer v%(version)i

%(myname)s action packagefile [request URL]

action      - Either "l" for listing the script or "i" for installing.
packagefile - The path to the file containing the MoinMoin installer package
request URL - Just needed if you are running a wiki farm, used to differentiate
              the correct wiki.

Example:

%(myname)s i ../package.zip

""" % {"version": MAX_VERSION, "myname": os.path.basename(args[0])}
        raise SystemExit

    packagefile = args[2]
    if len(args) > 3:
        request_url = args[3]
    else:
        request_url = None

    # Setup MoinMoin environment
    from MoinMoin.web.contexts import ScriptContext
    request = ScriptContext(url=request_url)

    package = ZipPackage(request, packagefile)
    if not package.isPackage():
        print "The specified file %s is not a package." % packagefile
        raise SystemExit

    if args[1] == 'l':
        print package.getScript()
    elif args[1] == 'i':
        if package.installPackage():
            print "Installation was successful!"
        else:
            print "Installation failed."
        if package.msg:
            print package.msg

if __name__ == '__main__':
    main()
