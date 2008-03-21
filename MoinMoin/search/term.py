"""
    MoinMoin - search expression object representation

    @copyright: 2008 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

import re

# Base classes

class Term(object):
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

    def reset(self):
        """
        Reset this search term to make it ready for testing.
        Must be called before each outermost-level evaluate.
        """
        self._result = None

class UnaryTerm(Term):
    def __init__(self, term):
        Term.__init__(self)
        assert isinstance(term, Term)
        self.term = term

    def reset(self):
        Term.reset(self)
        self.term.reset()

    def __repr__(self):
        return u'<%s(%r)>' % (self.__class__.__name__, self.term)

class ListTerm(Term):
    def __init__(self, *terms):
        Term.__init__(self)
        for e in terms:
            assert isinstance(e, Term)
        self.terms = terms

    def reset(self):
        Term.reset(self)
        for e in self.terms:
            e.reset()

    def __repr__(self):
        return u'<%s(%s)>' % (self.__class__.__name__,
                              ', '.join([repr(t) for t in self.terms]))

# Logical expression classes

class AND(ListTerm):
    def _evaluate(self, backend, itemname, get_metadata):
        for e in self.terms:
            if not e.evaluate(backend, itemname, get_metadata):
                return False
        return True

class OR(ListTerm):
    def _evaluate(self, backend, itemname, get_metadata):
        for e in self.terms:
            if e.evaluate(backend, itemname, get_metadata):
                return True
        return False

class NOT(UnaryTerm):
    def _evaluate(self, backend, itemname, get_metadata):
        return not self.term.evaluate(backend, itemname, get_metadata)

class XOR(ListTerm):
    def _evaluate(self, backend, itemname, get_metadata):
        count = 0
        for e in self.terms:
            if e.evaluate(backend, itemname, get_metadata):
                count += 1
        return count == 1

# Actual Moin search terms

class TextRE(Term):
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

class NameRE(Term):
    def __init__(self, needle_re):
        Term.__init__(self)
        assert hasattr(needle_re, 'search')
        self._needle_re = needle_re

    def _evaluate(self, backend, itemname, get_metadata):
        return not (not self._needle_re.search(itemname))

    def __repr__(self):
        return u'<term.NameRE(...)>'

class Name(NameRE):
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
    def __init__(self, fn):
        Term.__init__(self)
        assert callable(fn)
        self._fn = fn

    def _evaluate(self, backend, itemname, get_metadata):
        return not (not self._fn(itemname))

    def __repr__(self):
        return u'<term.Name(%s, %s)>' % (self.needle, self.case_sensitive)

class MetaDataMatch(Term):
    def __init__(self, key, val):
        Term.__init__(self)
        self.key = key
        self.val = val

    def _evaluate(self, backend, itemname, get_metadata):
        metadata = get_metadata()
        return self.key in metadata and metadata[self.key] == self.val

class HasMetaDataKey(Term):
    def __init__(self, key):
        Term.__init__(self)
        self.key = key

    def _evaluate(self, backend, itemname, get_metadata):
        return self.key in get_metadata()
