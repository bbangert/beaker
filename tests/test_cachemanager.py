import time
from datetime import datetime

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**parse_cache_config_options(opts))
    return cache

def make_region_cached_func():
    global _cache_obj
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)

    @cache.region('short_term', 'region_loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    _cache_obj = cache
    return load

def make_cached_func():
    global _cache_obj
    cache = make_cache_obj()

    @cache.cache('loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    _cache_obj = cache
    return load

def test_parse_doesnt_allow_none():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    for region, params in parse_cache_config_options(opts)['cache_regions'].iteritems():
        for k, v in params.iteritems():
            assert v != 'None', k

def test_decorators():
    for func in (make_region_cached_func, make_cached_func):
        yield check_decorator, func()

def check_decorator(func):
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

def test_check_invalidate_region():
    func = make_region_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    _cache_obj.region_invalidate(func, None, 'region_loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    _cache_obj.region_invalidate(func, None, 'region_loader', 'Fredd')
    assert result3 == result2

def test_check_invalidate():
    func = make_cached_func()
    result = func('Fred')
    assert 'Fred' in result

    result2 = func('Fred')
    assert result == result2
    _cache_obj.invalidate(func, 'loader', 'Fred')

    result3 = func('Fred')
    assert result3 != result2

    result2 = func('Fred')
    assert result3 == result2

    # Invalidate a non-existent key
    _cache_obj.invalidate(func, 'loader', 'Fredd')
    assert result3 == result2
