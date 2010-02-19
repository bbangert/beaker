import time
from datetime import datetime

import beaker.cache as cache
from beaker.cache import CacheManager, cache_region, region_invalidate
from beaker.util import parse_cache_config_options

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
    cache = CacheManager(**parse_cache_config_options(opts))
    return cache

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

def test_check_decorator():
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
