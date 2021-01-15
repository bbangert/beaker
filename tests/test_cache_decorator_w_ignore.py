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

def make_cached_func_excluded(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache(args_to_exclude=['b'])
    def compute(a, b):
        return "Hi there, my result is %d" % (a+b)
    return cache, compute

def test_invalidate_cache_excluded():
    cache, func = make_cached_func_excluded()
    val = func(1, 2)
    val2 = func(1, 3)
    assert val == val2

    cache.invalidate(func, 1)
    val3 = func(1, 3)
    assert val3 != val

def make_cached_func_included(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache(args_to_include=['b'])
    def compute(a, b=4):
        return "Hi there, my result is %d" % (a+b)
    return cache, compute

def test_invalidate_cache_excluded():
    cache, func = make_cached_func_included()
    val = func(1)
    val2 = func(4, 4)
    assert val == val2

    cache.invalidate(func, 4)
    val3 = func(2, 4)
    assert val3 != val


def test_both_include_exclude():
    cache = make_cache_obj()

    try:
        @cache.cache(args_to_include=[], args_to_exclude=[])
        def f():
            pass
        assert False
    except TypeError:
        pass

def make_cached_method():
    cache = make_cache_obj()

    class Computer:
        def __init__(self, a):
            self.a = a

        @cache.cache(exclude_self=False)
        def add(self, b):
            return "Hi there, my result is %d" % (self.a+b)

    return cache, Computer


def test_dont_exclude_self():
    cache, Computer = make_cached_method()

    c1 = Computer(1)
    c2 = Computer(2)

    val1 = c1.add(1)
    val2 = c2.add(1)
    assert val1 != val2
