"""
    MoinMoin - search expression object representation

    This module defines the possible search terms for a query to the
    storage backend. This is used, for example, to implement searching,
    page lists etc.

    Note that some backends can optimise some of the search terms, for
    example a backend that has indexed various metadata keys can optimise
    easy expressions containing MetaDataMatch terms. This is only allowed
    for classes documented as being 'final' which hence also means that
    their _evaluate function may not be overridden by descendent classes.

    For example, that metadata backend could test if the expression is a
    MetaDataMatch expression, and if so, simply return the appropriate
    index; or if it is an AND() expression build the page list from the
    index, remove the MetaDataMatch instance from the AND list and match
    the resulting expression only for pages in that list. Etc.

    TODO: Should we write some generic code for picking apart expressions
          like that?

    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import re

# Base classes

class Term(object):
    """
    Base class for search terms.
    """
    def __init__(self):
        pass

    def evaluate(self, backend, itemname, get_metadata):
        """
        Evaluate this term and return True or False if the
        item identified by the parameters matches.

        @param backend: the storage backend
        @param itemname: the item name
        @param get_metadata: function (without parameters) that
                  returns a metadata dict (-like) for the item, the
                  return value may not be modified.
        """
        assert hasattr(self, '_result')

        if not self._result is None:
            return self._result

        self._result = self._evaluate(backend, itemname, get_metadata)

        return self._result

    def _evaluate(self, backend, itemname, get_metadata):
        """
        Implements the actual evaluation
        """
        raise NotImplementedError()

    def prepare(self):
        """
        Prepare this search term to make it ready for testing.
        Must be called before each outermost-level evaluate.
        """
        self._result = None

class UnaryTerm(Term):
    """
    Base class for search terms that has a single contained
    search term, e.g. NOT.
    """
    def __init__(self, term):
        Term.__init__(self)
        assert isinstance(term, Term)
        self.term = term

    def prepare(self):
        Term.prepare(self)
        self.term.prepare()

    def __repr__(self):
        return u'<%s(%r)>' % (self.__class__.__name__, self.term)

class ListTerm(Term):
    """
    Base class for search terms that contain multiple other
    search terms, e.g. AND.
    """
    def __init__(self, *terms):
        Term.__init__(self)
        for e in terms:
            assert isinstance(e, Term)
        self.terms = list(terms)

    def prepare(self):
        Term.prepare(self)
        for e in self.terms:
            e.prepare()

    def remove(self, subterm):
        self.terms.remove(subterm)

    def add(self, subterm):
        self.terms.append(subterm)

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__,
                              ', '.join([repr(t) for t in self.terms]))

# Logical expression classes

class AND(ListTerm):
    """
    AND connection between multiple terms. Final.
    """
    def _evaluate(self, backend, itemname, get_metadata):
        for e in self.terms:
            if not e.evaluate(backend, itemname, get_metadata):
                return False
        return True

class OR(ListTerm):
    """
    OR connection between multiple terms. Final.
    """
    def _evaluate(self, backend, itemname, get_metadata):
        for e in self.terms:
            if e.evaluate(backend, itemname, get_metadata):
                return True
        return False

class NOT(UnaryTerm):
    """
    Inversion of a single term. Final.
    """
    def _evaluate(self, backend, itemname, get_metadata):
        return not self.term.evaluate(backend, itemname, get_metadata)

class XOR(ListTerm):
    """
    XOR connection between multiple terms, i.e. exactly
    one must be True. Final.
    """
    def _evaluate(self, backend, itemname, get_metadata):
        count = 0
        for e in self.terms:
            if e.evaluate(backend, itemname, get_metadata):
                count += 1
        return count == 1

TRUE = AND()
FALSE = OR()

# Actual Moin search terms

class TextRE(Term):
    """
    Regular expression full text match, use as last resort.
    """
    def __init__(self, needle_re):
        Term.__init__(self)
        assert hasattr(needle_re, 'search')
        self._needle_re = needle_re

    def _evaluate(self, backend, itemname, get_metadata):
        revno = backend.current_revision(itemname)
        data = backend.get_data_backend(itemname, revno).read()
        return not (not self._needle_re.search(data))

    def __repr__(self):
        return u'<term.TextRE(...)>'

class Text(TextRE):
    """
    Full text match including middle of words and over word
    boundaries. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle), flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Text(%s, %s)>' % (self.needle, self.case_sensitive)

class Word(TextRE):
    """
    Full text match finding exact words. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile('\\b' + re.escape(needle) + '\\b', flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Word(%s, %s)>' % (self.needle, self.case_sensitive)

class WordStart(TextRE):
    """
    Full text match finding the start of a word. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile('\\b' + re.escape(needle), flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.WordStart(%s, %s)>' % (self.needle, self.case_sensitive)

class WordEnd(TextRE):
    """
    Full text match finding the end of a word. Final.
    """
    def __init__(self, needle, case_sensitive):
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle) + '\\b', flags)
        TextRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.WordEnd(%s, %s)>' % (self.needle, self.case_sensitive)

class NameRE(Term):
    """
    Matches the item's name with a given regular expression.
    """
    def __init__(self, needle_re):
        Term.__init__(self)
        assert hasattr(needle_re, 'search')
        self._needle_re = needle_re

    def _evaluate(self, backend, itemname, get_metadata):
        return not (not self._needle_re.search(itemname))

    def __repr__(self):
        return u'<term.NameRE(...)>'

class Name(NameRE):
    """
    Item name match, given needle must occur in item's name. Final.
    """
    def __init__(self, needle, case_sensitive):
        assert isinstance(needle, unicode)
        flags = re.UNICODE
        if not case_sensitive:
            flags = flags | re.IGNORECASE
        _needle_re = re.compile(re.escape(needle), flags)
        NameRE.__init__(self, _needle_re)
        self.needle = needle
        self.case_sensitive = case_sensitive

    def __repr__(self):
        return u'<term.Name(%s, %s)>' % (self.needle, self.case_sensitive)

class NameFn(Term):
    """
    Arbitrary item name matching function.
    """
    def __init__(self, fn):
        Term.__init__(self)
        assert callable(fn)
        self._fn = fn

    def _evaluate(self, backend, itemname, get_metadata):
        return not (not self._fn(itemname))

    def __repr__(self):
        return u'<term.NameFn(%r)>' % (self._fn, )

class MetaDataMatch(Term):
    """
    Matches a metadata key/value pair of an item, requires
    existence of the metadata key. Final.
    """
    def __init__(self, key, val):
        Term.__init__(self)
        self.key = key
        self.val = val

    def _evaluate(self, backend, itemname, get_metadata):
        metadata = get_metadata()
        return self.key in metadata and metadata[self.key] == self.val

    def __repr__(self):
        return u'<%s(%s: %s)>' % (self.__class__.__name__, self.key, self.val)

class HasMetaDataKey(Term):
    """
    Requires existence of the metadata key. Final.
    """
    def __init__(self, key):
        Term.__init__(self)
        self.key = key

    def _evaluate(self, backend, itemname, get_metadata):
        return self.key in get_metadata()

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__, self.key)

class FromUnderlay(Term):
    """
    Requires that an item comes from a layered backend
    marked as 'underlay'.
    """
    def _evaluate(self, backend, itemname, get_metadata):
        return hasattr(backend, '_layer_marked_underlay')
