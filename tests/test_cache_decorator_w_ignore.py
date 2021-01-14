import time
from datetime import datetime

from beaker.cache import CacheManager
from beaker import util
from unittest import SkipTest

defaults = {'cache.data_dir':'./cache', 'cache.type':'dbm', 'cache.expire': 2}

def teardown_module():
    import shutil
    shutil.rmtree('./cache', True)

def make_cache_obj(**kwargs):
    opts = defaults.copy()
    opts.update(kwargs)
    cache = CacheManager(**util.parse_cache_config_options(opts))
    return cache

def make_cached_func(**opts):
    cache = make_cache_obj(**opts)
    @cache.cache(args_to_ignore=['b'])
    def compute(a, b):
        print('Computing with', a, b)
        return "Hi there, my result is %d" % (a+b)
    return cache, compute

def test_invalidate_cache():
    cache, func = make_cached_func()
    val = func(1, 2)
    val2 = func(1, 3)
    assert val == val2

    cache.invalidate(func, 1)
    val3 = func(1, 3)
    assert val3 != val

# def test_class_key_cache():
#     cache = make_cache_obj()

#     class Foo(object):
#         @cache.cache('method')
#         def go(self, x, y):
#             return "hi foo"

#     @cache.cache('standalone')
#     def go(x, y):
#         return "hi standalone"

#     x = Foo().go(1, 2)
#     y = go(1, 2)

#     ns = go._arg_namespace
#     assert cache.get_cache(ns).get('method 1 2') == x
#     assert cache.get_cache(ns).get('standalone 1 2') == y

# def test_func_namespace():
#     def go(x, y):
#         return "hi standalone"

#     assert 'test_cache_decorator' in util.func_namespace(go)
#     assert util.func_namespace(go).endswith('go')


