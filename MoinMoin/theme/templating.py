# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Jinja2010 GSoC project
    
    This module will be used to rendering a theme using Jinja2.
    
    @copyright: 2010 MoinMoin:DiogenesAugustoFernandesHerminio
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.support.jinja2 import Enviroment, FileSystemLoader

TEMPLATES_DIR = '/templates/'
ENVIROMENT = Enviroment(loader=FileSystemLoader(TEMPLATES_DIR))

class JinjaTheme(object):
    """
    Class used to replace actual ThemeBase.
    """
    
    def __init__(self, request):
        """
        Initialize the JinjaTheme object.

        @param request: the request object
        """
        # Gonna use this for now, it came from ThemeBase
        self.request = request
        self.cfg = request.cfg
        self._cache = {} # Used to cache elements that may be used several times
        self._status = []
        self._send_title_called = False

        jinja_cachedir = os.path.join(request.cfg.cache_dir, 'jinja')
        try:
            os.mkdir(jinja_cachedir)
        except:
            pass

        jinja_templatedir = os.path.join(os.path.dirname(__file__), '..', 'templates')

        self.env = Environment(loader=FileSystemLoader(jinja_templatedir),
                               bytecode_cache=FileSystemBytecodeCache(jinja_cachedir, '%s'),
                               extensions=['jinja2.ext.i18n'])
        from werkzeug import url_quote, url_encode
        self.env.filters['urlencode'] = lambda x: url_encode(x)
        self.env.filters['urlquote'] = lambda x: url_quote(x)
        self.env.filters['datetime_format'] = lambda tm, u=request.user: u.getFormattedDateTime(tm)
        self.env.filters['date_format'] = lambda tm, u=request.user: u.getFormattedDate(tm)
        self.env.filters['user_format'] = lambda rev, request=request: \
                                              user.get_printable_editor(request,
                                                                        rev[EDIT_LOG_USERID],
                                                                        rev[EDIT_LOG_ADDR],
                                                                        rev[EDIT_LOG_HOSTNAME])

    def render_header(context={}):
        """
        Function that renders header.
        """
        return render('header.html', **context)    
    
    def render_footer(context={}):
        """
        Function that renders footer.
        """
        return render('footer.html', **context)
    
    def render(filename, context={}):
        """
        Function that renders using Jinja2.
        """
        return template.render(**context)
    