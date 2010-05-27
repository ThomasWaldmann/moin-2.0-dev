# -*- coding: iso-8859-1 -*-
'''
    MoinMoin - Jinja2010 GSoC project
    @copyright: 2003-2009 MoinMoin:ThomasWaldmann,
                2008 MoinMoin:RadomirDopieralski,
                2010 MoinMoin:DiogenesAugustoFernandesHermínio
'''

from MoinMoin.support.jinja2 import Enviroment, FileSystemLoader

TEMPLATES_DIR = '/templates/'
ENVIROMENT = Enviroment(loader=FileSystemLoader(TEMPLATES_DIR))

def render_jinja2(filename, context={}):
    '''
    Function that renders using Jinja2.
    '''
    template = ENVIROMENT.get_template(filename)
    rendered = template.render(**context)
    return rendered
    