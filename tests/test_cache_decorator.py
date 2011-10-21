import time
from datetime import datetime

import beaker.cache as cache
from beaker.cache import CacheManager, cache_region, region_invalidate
from beaker import util

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

@cache_region('short_term')
def fred(x):
    return time.time()

@cache_region('short_term')
def george(x):
    return time.time()

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**util.parse_cache_config_options(opts))
    return cache

def make_cached_func(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache()
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return cache, load

def make_region_cached_func():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache_region('short_term', 'region_loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load

def make_region_cached_func_2():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache_region('short_term')
    def load_person(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load_person

def test_check_region_decorator():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2

    result3 = func('George')
    assert 'George' in result3
    result4 = func('George')
    assert result3 == result4

    time.sleep(2)
    result2 = func('Fred')
    assert result != result2

def test_different_default_names():
    result = fred(1)
    time.sleep(1)
    result2 = george(1)
    assert result != result2

def test_check_invalidate_region():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    region_invalidate(func, None, 'region_loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    region_invalidate(func, None, 'region_loader', 'Fredd')
    assert result3 == result2


def test_check_invalidate_region_2():
    func = make_region_cached_func_2()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    region_invalidate(func, None, 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    region_invalidate(func, None, 'Fredd')
    assert result3 == result2

def test_invalidate_cache():
    cache, func = make_cached_func()
    val = func('foo')
    time.sleep(.1)
    val2 = func('foo')
    assert val == val2

    cache.invalidate(func, 'foo')
    val3 = func('foo')
    assert val3 != val

def test_class_key_cache():
    cache = make_cache_obj()

    class Foo(object):
        @cache.cache('method')
        def go(self, x, y):
            return "hi foo"

    @cache.cache('standalone')
    def go(x, y):
        return "hi standalone"

    x = Foo().go(1, 2)
    y = go(1, 2)

    ns = go._arg_namespace
    assert cache.get_cache(ns).get('method 1 2') == x
    assert cache.get_cache(ns).get('standalone 1 2') == y

def test_func_namespace():
    def go(x, y):
        return "hi standalone"

    assert 'test_cache_decorator' in util.func_namespace(go)
    assert util.func_namespace(go).endswith('go')

def test_class_key_region():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @cache_region('short_term', 'method')
        def go(self, x, y):
            return "hi foo"

    @cache_region('short_term', 'standalone')
    def go(x, y):
        return "hi standalone"

    x = Foo().go(1, 2)
    y = go(1, 2)
    ns = go._arg_namespace
    assert cache.get_cache_region(ns, 'short_term').get('method 1 2') == x
    assert cache.get_cache_region(ns, 'short_term').get('standalone 1 2') == y

def test_classmethod_key_region():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @classmethod
        @cache_region('short_term', 'method')
        def go(cls, x, y):
            return "hi"

    x = Foo.go(1, 2)
    ns = Foo.go._arg_namespace
    assert cache.get_cache_region(ns, 'short_term').get('method 1 2') == x

def test_class_key_region_invalidate():
    opts = {}
    opts['cache.regions'] = 'short_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    class Foo(object):
        @cache_region('short_term', 'method')
        def go(self, x, y):
            now = datetime.now()
            return "hi %s" % now

        def invalidate(self, x, y):
            region_invalidate(self.go, None, "method", x, y)

    x = Foo().go(1, 2)
    time.sleep(1)
    y = Foo().go(1, 2)
    Foo().invalidate(1, 2)
    z = Foo().go(1, 2)

    assert x == y
    assert x != z
