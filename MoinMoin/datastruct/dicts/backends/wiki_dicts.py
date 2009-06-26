# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - WikiDict functions.

    @copyright: 2003-2007 MoinMoin:ThomasWaldmann,
                2003 by Gustavo Niemeyer
                2009 MoinMoin:DmitrijsMilajevs
    @license: GNU GPL, see COPYING for details.
"""
import re

from MoinMoin import caching, wikiutil
from MoinMoin.Page import Page
from MoinMoin.datastruct.dicts.backends import BaseDict, BaseDictBackend, DictDoesNotExistError


class WikiDict(BaseDict):
    """ Mapping of keys to values in a wiki page.

       How a Dict definition page should look like:

       any text ignored
        key1:: value1
        * ignored, too
        key2:: value2 containing spaces
        ...
        keyn:: ....
       any text ignored
    """


    def _load_dict(self):
        request = self.request
        dict_name = self.name

        page = Page(request, dict_name)
        if page.exists():
            arena = 'pagedicts'
            key = wikiutil.quoteWikinameFS(dict_name)
            cache = caching.CacheEntry(request, arena, key, scope='wiki', use_pickle=True)
            try:
                cache_mtime = cache.mtime()
                page_mtime = wikiutil.version2timestamp(page.mtime_usecs())
                # TODO: fix up-to-date check mtime granularity problems
                if cache_mtime > page_mtime:
                    # cache is uptodate
                    return cache.content()
                else:
                    raise caching.CacheError
            except caching.CacheError:
                # either cache does not exist, is erroneous or not uptodate: recreate it
                d = super(WikiDict, self)._load_dict()
                cache.update(d)
                return d
        else:
            raise DictDoesNotExistError(dict_name)


class WikiDicts(BaseDictBackend):
    """ a dictionary of Dict objects

       Config:
           cfg.page_dict_regex
               Default: ".*Dict$"  Defs$ Vars$ ???????????????????
    """

    # Key:: Value - ignore all but key:: value pairs, strip whitespace, exactly one space after the :: is required
    _dict_page_parse_regex = re.compile(ur'^ (?P<key>.+?):: (?P<val>.*?) *$', re.MULTILINE | re.UNICODE)

    def __contains__(self, dict_name):
        return self.is_dict_name(dict_name) and Page(self.request, dict_name).exists()

    def __getitem__(self, dict_name):
        return WikiDict(request=self.request, name=dict_name, backend=self)

    def _retrieve_members(self, dict_name):
        page = Page(self.request, dict_name)
        text = page.get_raw_body()
        return dict([match.groups() for match in self._dict_page_parse_regex.finditer(text)])

