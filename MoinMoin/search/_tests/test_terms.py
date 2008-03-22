"""
    Term tests.
"""

import re

from MoinMoin.search import term


_item_contents = {
    u'a': u'abcdefg hijklmnop',
    u'b': u'bbbbbbb bbbbbbbbb',
    u'c': u'Abiturienten Apfeltortor',
    u'Lorem': u'Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Duis placerat, tortor quis sollicitudin dictum, nisi tellus aliquam quam, ac varius lacus diam eget tortor. Nulla vehicula, nisi ac hendrerit aliquam, libero erat tempor ante, lobortis placerat lacus justo vitae erat. In rutrum odio a sem. In ac risus vel diam vulputate luctus. Fusce sit amet est. Morbi consectetuer eros vel risus. In nulla lacus, ultrices id, vestibulum tempus, dictum in, mauris. Quisque rutrum faucibus nisl. Suspendisse potenti. In hac habitasse platea dictumst. Donec ac magna ac eros malesuada facilisis. Pellentesque viverra nibh nec dui. Praesent venenatis lectus vehicula eros. Phasellus pretium, ante at mollis luctus, nibh lacus ultricies eros, vitae pharetra lacus leo at neque. Nullam vel sapien. In in diam id massa nonummy suscipit. Curabitur vel dui sed tellus pellentesque pretium.',
}

_item_metadata = {
    u'a': {'m1': True, 'm2': '222'},
    u'A': {'m1': True, 'm2': '333'},
    u'b': {'m1': False, 'm2': '222'},
    u'c': {'m1': True, 'm2': '222'},
    u'B': {'m1': False, 'm2': '333'},
    u'Lorem': {'m1': 7, 'm2': 444},
}

for n in _item_contents.keys():
    nl = n.lower()
    nu = n.upper()
    _item_contents[nl] = _item_contents[n].lower()
    _item_contents[nu] = _item_contents[n].upper()
    if not nl in _item_metadata:
        _item_metadata[nl] = _item_metadata[n]
    if not nu in _item_metadata:
        _item_metadata[nu] = _item_metadata[n]

class TermTestData:
    def __init__(self, text):
        self.text = text
    def read(self, size=None):
        return self.text

class CacheAssertTerm(term.Term):
    def __init__(self):
        term.Term.__init__(self)
        self.evalonce = False

    def _evaluate(self, backend, itemname, metadata):
        assert not self.evalonce
        self.evalonce = True
        return True

class AssertNotCalledTerm(term.Term):
    def _evaluate(self, backend, itemname, metadata):
        assert False

_b2e = {
    1: term.TRUE,
    0: term.FALSE,
}

class TestTerms:
    # euh. we fake being a backend ourselves...
    def get_data_backend(self, itemname, revno):
        assert revno == 107
        # make sure that text isn't requested for Terms that shouldn't
        assert itemname is not None
        return TermTestData(_item_contents[itemname])

    def current_revision(self, item):
        return 107

    def _evaluate(self, term, itemname, expected):
        term.prepare()
        if itemname is not None:
            meta = _item_metadata[itemname].copy()
            # ease debugging
            meta['__value'] = _item_contents[itemname]
        else:
            meta = {}
        m = lambda: meta
        meta2 = meta.copy()
        assert expected == term.evaluate(self, itemname, m)
        # make sure they don't modify the metadata dict
        assert meta == meta2

    def testSimpleTextSearch(self):
        terms = [term.Text(u'abcdefg', True), term.Text(u'ijklmn', True)]
        for item, expected in [('a', True), ('A', False), ('b', False), ('B', False), ('lorem', False)]:
            for t in terms:
                yield self._evaluate, t, item, expected

    def testSimpleTextSearchCI(self):
        terms = [term.Text(u'abcdefg', False), term.Text(u'ijklmn', False)]
        for item, expected in [('a', True), ('A', True), ('b', False), ('B', False), ('lorem', False)]:
            for t in terms:
                yield self._evaluate, t, item, expected

    def testANDOR(self):
        tests = [
            (True,  [1, 1, 1, 1, 1]),
            (True,  [1, 1, 1, 1]),
            (True,  [1, 1, 1]),
            (True,  [1, 1]),
            (False, [0, 1, 1]),
            (False, [0, 1, 1, 1]),
            (False, [1, 0, 1, 1]),
            (False, [1, 1, 0, 1]),
            (False, [1, 1, 1, 0]),
            (False, [0, 1, 1, 0]),
        ]
        for expected, l in tests:
            l = [_b2e[i] for i in l]
            t = term.AND(*l)
            yield self._evaluate, t, 'a', expected
        for expected, l in tests:
            l = [_b2e[1 - i] for i in l]
            t = term.OR(*l)
            yield self._evaluate, t, 'a', not expected

    def testXOR(self):
        tests = [
            (False, [1, 1, 1, 1, 1]),
            (False, [1, 1, 1, 1]),
            (False, [1, 1, 1]),
            (False, [1, 1]),
            (False, [0, 1, 1]),
            (False, [0, 1, 1, 1]),
            (False, [1, 0, 1, 1]),
            (False, [1, 1, 0, 1]),
            (False, [1, 1, 1, 0]),
            (False, [0, 1, 1, 0]),
            (True,  [0, 0, 0, 1, 0]),
            (True,  [0, 0, 1, 0]),
            (True,  [1, 0, 0]),
            (True,  [0, 1]),
            (False, [0, 0, 0]),
        ]
        for expected, l in tests:
            l = [_b2e[i] for i in l]
            t = term.XOR(*l)
            yield self._evaluate, t, 'a', expected

    def testTextSearchRE(self):
        terms = [term.TextRE(re.compile('^abc')), term.TextRE(re.compile('\shij'))]
        for item, expected in [('a', True), ('A', False), ('b', False), ('B', False), ('lorem', False)]:
            for t in terms:
                yield self._evaluate, t, item, expected

    def testTextSearchRE2(self):
        terms = [term.TextRE(re.compile('sollici')), term.TextRE(re.compile('susci'))]
        for item, expected in [('a', False), ('A', False), ('b', False), ('B', False), ('lorem', True)]:
            for t in terms:
                yield self._evaluate, t, item, expected

    def testResultCaching1(self):
        cat = CacheAssertTerm()
        expected = True
        t = term.AND(cat, cat, cat)
        yield self._evaluate, t, None, expected

    def testResultCaching2(self):
        cat = CacheAssertTerm()
        expected = True
        t = term.OR(cat, cat, cat)
        yield self._evaluate, t, None, expected

    def testResultCaching3(self):
        cat = CacheAssertTerm()
        expected = False
        t = term.AND(cat, cat, cat, term.FALSE)
        yield self._evaluate, t, None, expected

    def testResultCaching4(self):
        cat = CacheAssertTerm()
        expected = True
        t = term.OR(cat, cat, cat)
        yield self._evaluate, t, None, expected

    def testShortCircuitEval1(self):
        yield self._evaluate, term.AND(term.TRUE, term.FALSE, AssertNotCalledTerm()), None, False

    def testShortCircuitEval2(self):
        yield self._evaluate, term.OR(term.TRUE, term.FALSE, AssertNotCalledTerm()), None, True

    def testSimpleTitleSearch(self):
        for item, expected in [('a', True), ('A', False), ('b', False), ('B', False), ('lorem', False)]:
            yield self._evaluate, term.Name(u'a', True), item, expected

    def testSimpleTitleSearchCI(self):
        for item, expected in [('a', True), ('A', True), ('b', False), ('B', False), ('lorem', False)]:
            yield self._evaluate, term.Name(u'a', False), item, expected

    def testTitleRESearch(self):
        for item, expected in [('a', True), ('A', False), ('b', False), ('B', False), ('lorem', True)]:
            yield self._evaluate, term.NameRE(re.compile('(a|e)')), item, expected

    def testMetaMatch1(self):
        t = term.MetaDataMatch('m1', True)
        for item, expected in [('a', True), ('A', True), ('b', False), ('B', False), ('lorem', False)]:
            yield self._evaluate, t, item, expected

    def testMetaMatch2(self):
        t = term.MetaDataMatch('m2', '333')
        for item, expected in [('a', False), ('A', True), ('b', False), ('B', True), ('lorem', False)]:
            yield self._evaluate, t, item, expected

    def testMetaMatch3(self):
        t = term.MetaDataMatch('m2', 444)
        for item, expected in [('a', False), ('A', False), ('b', False), ('B', False), ('lorem', True)]:
            yield self._evaluate, t, item, expected

    def testHasMeta1(self):
        t = term.HasMetaDataKey('m3')
        for item, expected in [('a', False), ('A', False), ('b', False), ('B', False), ('lorem', False)]:
            yield self._evaluate, t, item, expected

    def testHasMeta2(self):
        t = term.HasMetaDataKey('m1')
        for item, expected in [('a', True), ('A', True), ('b', True), ('B', True), ('lorem', True)]:
            yield self._evaluate, t, item, expected

    def testNameFn(self):
        t = term.NameFn(lambda x: x in ['a', 'b', 'lorem'])
        for item, expected in [('a', True), ('A', False), ('b', True), ('B', False), ('lorem', True)]:
            yield self._evaluate, t, item, expected

    def testWordCI(self):
        t = term.Word('Curabitur', False)
        for item, expected in [('B', False), ('Lorem', True), ('lorem', True), ('LOREM', True)]:
            yield self._evaluate, t, item, expected

    def testWord(self):
        t = term.Word('Curabitur', True)
        for item, expected in [('B', False), ('Lorem', True), ('lorem', False), ('LOREM', False)]:
            yield self._evaluate, t, item, expected

    def testWordStartCI(self):
        t = term.WordStart('Curabi', False)
        for item, expected in [('B', False), ('Lorem', True), ('lorem', True), ('LOREM', True)]:
            yield self._evaluate, t, item, expected

    def testWordStart(self):
        t = term.WordStart('Curabi', True)
        for item, expected in [('c', False), ('Lorem', True), ('lorem', False), ('LOREM', False)]:
            yield self._evaluate, t, item, expected

    def testWordStart2(self):
        t = term.WordStart('abitur', True)
        for item, expected in [('c', True), ('C', False), ('Lorem', False), ]:
            yield self._evaluate, t, item, expected

    def testWordStart2CI(self):
        t = term.WordStart('abitur', False)
        for item, expected in [('c', True), ('C', True), ('Lorem', False), ]:
            yield self._evaluate, t, item, expected

    def testWordEndCI(self):
        t = term.WordEnd('abitur', False)
        for item, expected in [('c', False), ('Lorem', True), ('lorem', True), ('LOREM', True)]:
            yield self._evaluate, t, item, expected

coverage_modules = ['MoinMoin.search.terms']
