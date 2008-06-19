# coding: utf-8
from beaker.cache import clsmap, Cache
from beaker.middleware import CacheMiddleware
from nose import SkipTest
from webtest import TestApp

if 'ext:memcached' not in clsmap:
    raise SkipTest("'memcache' or 'cmemcache' is not installed, can't test "
                   "memcached backend")

mc_url = '127.0.0.1:11211'

def simple_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:memcached'
    extra_args['url'] = mc_url
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 0
    cache.set_value('value', value+1)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % cache.get_value('value')]

def using_none_app(environ, start_response):
    extra_args = {}
    clear = False
    if environ.get('beaker.clear'):
        clear = True
    extra_args['type'] = 'ext:memcached'
    extra_args['url'] = mc_url
    extra_args['data_dir'] = './cache'
    cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
    if clear:
        cache.clear()
    try:
        value = cache.get_value('value')
    except:
        value = 10
    cache.set_value('value', None)
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %s' % value]


def cache_manager_app(environ, start_response):
    cm = environ['beaker.cache']
    cm.get_cache('test')['test_key'] = 'test value'

    start_response('200 OK', [('Content-type', 'text/plain')])
    yield "test_key is: %s\n" % cm.get_cache('test')['test_key']
    cm.get_cache('test').clear()

    try:
        test_value = cm.get_cache('test')['test_key']
    except KeyError:
        yield "test_key cleared"
    else:
        yield "test_key wasn't cleared, is: %s\n" % \
            cm.get_cache('test')['test_key']

def test_has_key():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    assert not cache.has_key("foo")
    assert "foo" not in cache
    cache.remove_value("test")
    assert not cache.has_key("test")

def test_has_key_multicache():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value("test", o)
    assert cache.has_key("test")
    assert "test" in cache
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    assert cache.has_key("test")

def test_unicode_keys():    
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value(u'hiŏ', o)
    assert u'hiŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hiŏ')
    assert u'hiŏ' not in cache

def test_spaces_in_unicode_keys():    
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    cache.set_value(u'hi ŏ', o)
    assert u'hi ŏ' in cache
    assert u'hŏa' not in cache
    cache.remove_value(u'hi ŏ')
    assert u'hi ŏ' not in cache

def test_spaces_in_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value("has space", 24)
    assert cache.has_key("has space")
    assert 24 == cache.get_value("has space")
    cache.set_value("hasspace", 42)
    assert cache.has_key("hasspace")
    assert 42 == cache.get_value("hasspace")

def test_increment():
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res
    
    app = TestApp(CacheMiddleware(simple_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

def test_store_none():
    app = TestApp(CacheMiddleware(using_none_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 10' in res
    res = app.get('/')
    assert 'current value is: None' in res
