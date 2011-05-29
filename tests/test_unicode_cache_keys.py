# coding: utf-8
"""If we try to use a character not in ascii range as a cache key, we get an 
unicodeencode error. See 
https://bitbucket.org/bbangert/beaker/issue/31/cached-function-decorators-break-when-some
for more on this
"""

from nose.tools import *
from beaker.cache import CacheManager

memory_cache = CacheManager(type='memory')

@memory_cache.cache('foo')
def foo(whatever):
    return whatever

class bar(object):

    @memory_cache.cache('baz')
    def baz(self, qux):
        return qux

    @classmethod
    @memory_cache.cache('bar')
    def quux(cls, garply):
        return garply

def test_A_unicode_encode_key_str():
    eq_(foo('Espanol'), 'Espanol')
    eq_(foo(12334), 12334)
    eq_(foo(u'Espanol'), u'Espanol')
    eq_(foo(u'Español'), u'Español')
    b = bar()
    eq_(b.baz('Espanol'), 'Espanol')
    eq_(b.baz(12334), 12334)
    eq_(b.baz(u'Espanol'), u'Espanol')
    eq_(b.baz(u'Español'), u'Español')
    eq_(b.quux('Espanol'), 'Espanol')
    eq_(b.quux(12334), 12334)
    eq_(b.quux(u'Espanol'), u'Espanol')
    eq_(b.quux(u'Español'), u'Español')


def test_B_replacing_non_ascii():
    """we replace the offending character with other non ascii one. Since
    the function distinguishes between the two it should not return the
    past value
    """
    assert_false(foo(u'Espaáol')==u'Español') 
    eq_(foo(u'Espaáol'), u'Espaáol')

def test_C_more_unicode():
    """We again test the same stuff but this time we use 
    http://tools.ietf.org/html/draft-josefsson-idn-test-vectors-00#section-5
    as keys"""
    keys = [
        # arabic (egyptian)
        u"\u0644\u064a\u0647\u0645\u0627\u0628\u062a\u0643\u0644\u0645\u0648\u0634\u0639\u0631\u0628\u064a\u061f",
        # Chinese (simplified)
        u"\u4ed6\u4eec\u4e3a\u4ec0\u4e48\u4e0d\u8bf4\u4e2d\u6587",
        # Chinese (traditional)
        u"\u4ed6\u5011\u7232\u4ec0\u9ebd\u4e0d\u8aaa\u4e2d\u6587",
        # czech
        u"\u0050\u0072\u006f\u010d\u0070\u0072\u006f\u0073\u0074\u011b\u006e\u0065\u006d\u006c\u0075\u0076\u00ed\u010d\u0065\u0073\u006b\u0079",
        # hebrew
        u"\u05dc\u05de\u05d4\u05d4\u05dd\u05e4\u05e9\u05d5\u05d8\u05dc\u05d0\u05de\u05d3\u05d1\u05e8\u05d9\u05dd\u05e2\u05d1\u05e8\u05d9\u05ea",
        # Hindi (Devanagari)
        u"\u092f\u0939\u0932\u094b\u0917\u0939\u093f\u0928\u094d\u0926\u0940\u0915\u094d\u092f\u094b\u0902\u0928\u0939\u0940\u0902\u092c\u094b\u0932\u0938\u0915\u0924\u0947\u0939\u0948\u0902",
        # Japanese (kanji and hiragana)
        u"\u306a\u305c\u307f\u3093\u306a\u65e5\u672c\u8a9e\u3092\u8a71\u3057\u3066\u304f\u308c\u306a\u3044\u306e\u304b",
        # Russian (Cyrillic)
        u"\u043f\u043e\u0447\u0435\u043c\u0443\u0436\u0435\u043e\u043d\u0438\u043d\u0435\u0433\u043e\u0432\u043e\u0440\u044f\u0442\u043f\u043e\u0440\u0443\u0441\u0441\u043a\u0438",
        # Spanish
        u"\u0050\u006f\u0072\u0071\u0075\u00e9\u006e\u006f\u0070\u0075\u0065\u0064\u0065\u006e\u0073\u0069\u006d\u0070\u006c\u0065\u006d\u0065\u006e\u0074\u0065\u0068\u0061\u0062\u006c\u0061\u0072\u0065\u006e\u0045\u0073\u0070\u0061\u00f1\u006f\u006c",
        # Vietnamese
        u"\u0054\u1ea1\u0069\u0073\u0061\u006f\u0068\u1ecd\u006b\u0068\u00f4\u006e\u0067\u0074\u0068\u1ec3\u0063\u0068\u1ec9\u006e\u00f3\u0069\u0074\u0069\u1ebf\u006e\u0067\u0056\u0069\u1ec7\u0074",
        # Japanese
        u"\u0033\u5e74\u0042\u7d44\u91d1\u516b\u5148\u751f",
        # Japanese
        u"\u5b89\u5ba4\u5948\u7f8e\u6075\u002d\u0077\u0069\u0074\u0068\u002d\u0053\u0055\u0050\u0045\u0052\u002d\u004d\u004f\u004e\u004b\u0045\u0059\u0053",
        # Japanese
        u"\u0048\u0065\u006c\u006c\u006f\u002d\u0041\u006e\u006f\u0074\u0068\u0065\u0072\u002d\u0057\u0061\u0079\u002d\u305d\u308c\u305e\u308c\u306e\u5834\u6240",
        # Japanese
        u"\u3072\u3068\u3064\u5c4b\u6839\u306e\u4e0b\u0032",
        # Japanese
        u"\u004d\u0061\u006a\u0069\u3067\u004b\u006f\u0069\u3059\u308b\u0035\u79d2\u524d",
        # Japanese
        u"\u30d1\u30d5\u30a3\u30fc\u0064\u0065\u30eb\u30f3\u30d0",
        # Japanese
        u"\u305d\u306e\u30b9\u30d4\u30fc\u30c9\u3067",
        # greek
        u"\u03b5\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac",
        # Maltese (Malti)
        u"\u0062\u006f\u006e\u0121\u0075\u0073\u0061\u0127\u0127\u0061",
        # Russian (Cyrillic)
        u"\u043f\u043e\u0447\u0435\u043c\u0443\u0436\u0435\u043e\u043d\u0438\u043d\u0435\u0433\u043e\u0432\u043e\u0440\u044f\u0442\u043f\u043e\u0440\u0443\u0441\u0441\u043a\u0438"
    ]
    for i in keys:
        eq_(foo(i),i)

def test_D_invalidate():
    """Invalidate cache"""
    memory_cache.invalidate(foo)
    eq_(foo('Espanol'), 'Espanol')
