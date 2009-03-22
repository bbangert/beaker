import time
from datetime import datetime

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm'}

def make_cache_obj():
    opts = defaults.copy()
    opts['cache.regions'] = 'short_term, long_term'
    opts['cache.short_term.expire'] = '2'
    cache = CacheManager(**parse_cache_config_options(opts))
    return cache

def make_cached_func():
    cache = make_cache_obj()
    
    @cache.region('short_term', 'loader')
    def load(person):
        now = datetime.now()
        return "Hi there %s, its currently %s" % (person, now)
    return load

def test_region_decorator():
    func = make_cached_func()
    
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
