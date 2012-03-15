from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from datetime import datetime

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 60, 'cache.regions': 'short_term'}

cache = CacheManager(**parse_cache_config_options(defaults))

def get_cached_value():
    @cache.region('short_term', 'test_namespacing')
    def get_value():
        return datetime.now()

    return get_value()

