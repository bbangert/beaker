import time
from datetime import datetime

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**parse_cache_config_options(opts))
    return cache

def make_region_cached_func():
    opts = {}
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = make_cache_obj(**opts)
    
    @cache.region('short_term', 'region_loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load

def make_cached_func():
    cache = make_cache_obj()

    @cache.cache('loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load

def test_decorators():
    for func in (make_region_cached_func, make_cached_func):
        yield check_decorator, func()

def check_decorator(func):
    result = func('Fred')
    assert 'Fred in result'
    
    result2 = func('Fred')
    assert result == result2
    
    result3 = func('George')
    assert 'George' in result3
    result4 = func('George')
    assert result3 == result4
    
    time.sleep(2)
    result2 = func('Fred')
    assert result != result2

