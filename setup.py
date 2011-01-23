#!/usr/bin/env python
"""
MoinMoin
--------

MoinMoin is an easy to use, full-featured and extensible wiki software
package written in Python. It can fulfill a wide range of roles, such as
a personal notes organizer deployed on a laptop or home web server,
a company knowledge base deployed on an intranet, or an Internet server
open to individuals sharing the same interests, goals or projects.

Links
`````

* `wiki <http://moinmo.in/>`_
"""

import sys, os

from MoinMoin import version

from setuptools import setup, find_packages


setup_args = dict(
    name="moin",
    version=str(version),
    description="MoinMoin is an easy to use, full-featured and extensible wiki software package",
    author="Juergen Hermann et al.",
    author_email="moin-user@lists.sourceforge.net",
    # maintainer(_email) not active because distutils/register can't handle author and maintainer at once
    download_url='http://static.moinmo.in/files/moin-%s.tar.gz' % (version, ),
    url="http://moinmo.in/",
    license="GNU GPL",
    long_description=__doc__,
    keywords="wiki web",
    platforms="any",
    classifiers="""\
Development Status :: 2 - Pre-Alpha
Environment :: Web Environment
Intended Audience :: Education
Intended Audience :: End Users/Desktop
Intended Audience :: Information Technology
Intended Audience :: Other Audience
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License (GPL)
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Topic :: Internet :: WWW/HTTP :: WSGI
Topic :: Internet :: WWW/HTTP :: WSGI :: Application
Topic :: Internet :: WWW/HTTP :: Dynamic Content
Topic :: Office/Business :: Groupware
Topic :: Text Processing :: Markup""".splitlines(),

    packages=find_packages(exclude=['_tests', ]),

    #package_dir={'MoinMoin.translations': 'MoinMoin/translations',
    #             'MoinMoin.static': 'MoinMoin/static',
    #             'MoinMoin.themes.modernized': 'MoinMoin/themes/modernized',
    #             'MoinMoin.templates': 'MoinMoin/templates',
    #             'MoinMoin.apps.admin.templates': 'MoinMoin/apps/admin/templates',
    #             'MoinMoin.apps.misc.templates': 'MoinMoin/apps/misc/templates',
    #            },

    package_data={'MoinMoin.translations': ['MoinMoin.pot', '*.po', ],
                  'MoinMoin.static': ['*', ],
                  'MoinMoin.themes.modernized': ['*', ],
                  'MoinMoin.templates': ['*.html', '*.xml', ],
                  'MoinMoin.apps.admin.templates': ['*.html', ],
                  'MoinMoin.apps.misc.templates': ['*.html', '*.txt', ],
                 },
    zip_safe=False,
    install_requires=[
        'blinker>=1.1',
        'Flask>=0.6',
        'Flask-Babel>=0.6',
        'Flask-Cache',
        'Flask-Script>=0.3',
        'Flask-Themes>=0.1',
        'emeraldtree',
        'flatland==dev', # repo checkout at revision 269:6c5d262d7eff works
        'Jinja2>=2.5',
        'parsedatetime>=0.8.6',
        'pygments>=1.1.1',
        'sqlalchemy>=0.5.6',
        'Werkzeug>=0.6.2', # XXX minimum rev http://dev.pocoo.org/hg/werkzeug-main/rev/657223ad99d0
        #'xappy>=0.5',
    ],
    # optional features and their list of requirements
    extras_require = {
        'reST': ["docutils"],
        'PIL': ["PIL"],
    },
    entry_points = dict(
        console_scripts = ['moin = MoinMoin.cmdline:main'], # TODO
    ),
)

if __name__ == '__main__':
    setup(**setup_args)

