from beaker.cache import CacheManager
from beaker import util

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown_module():
    import shutil
    shutil.rmtree('./cache', True)

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**util.parse_cache_config_options(opts))
    return cache

def make_cached_func1(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache(args_to_ignore=['b'])
    def compute(a, b):
        return "Hi there, my result is %d" % (a+b)
    return cache, compute

def test_invalidate_cache1():
    cache, func = make_cached_func1()
    val = func(1, 2)
    val2 = func(1, 3)
    assert val == val2

    cache.invalidate(func, 1)
    val3 = func(1, 3)
    assert val3 != val


def make_cached_func2(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache(args_to_ignore=['b'])
    def compute(a, b=4):
        return "Hi there, my result is %d" % (a+b)
    return cache, compute

def test_invalidate_cache2():
    cache, func = make_cached_func2()
    val = func(1)
    val2 = func(1, 3)
    assert val == val2

    cache.invalidate(func, 1)
    val3 = func(1, 4)
    assert val3 != val

