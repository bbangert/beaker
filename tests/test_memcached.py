# coding: utf-8
import mock
import os

from beaker.cache import clsmap, Cache, CacheManager, util
from beaker.middleware import CacheMiddleware, SessionMiddleware
from beaker.exceptions import InvalidCacheBackendError
from beaker.util import parse_cache_config_options
from nose import SkipTest
import unittest

try:
    from webtest import TestApp
except ImportError:
    TestApp = None

try:
    from beaker.ext import memcached
    client = memcached._load_client()
except InvalidCacheBackendError:
    raise SkipTest("an appropriate memcached backend is not installed")

mc_url = '127.0.0.1:11211'

c =client.Client([mc_url])
c.set('x', 'y')
if not c.get('x'):
    raise SkipTest("Memcached is not running at %s" % mc_url)

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def simple_session_app(environ, start_response):
    session = environ['beaker.session']
    sess_id = environ.get('SESSION_ID')
    if environ['PATH_INFO'].startswith('/invalid'):
        # Attempt to access the session
        id = session.id
        session['value'] = 2
    else:
        if sess_id:
            session = session.get_by_id(sess_id)
        if not session:
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ["No session id of %s found." % sess_id]
        if not session.has_key('value'):
            session['value'] = 0
        session['value'] += 1
        if not environ['PATH_INFO'].startswith('/nosave'):
            session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session['value'],
                                                            session.id)]

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

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_session():
    app = TestApp(SessionMiddleware(simple_session_app, data_dir='./cache', type='ext:memcached', url=mc_url))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res


@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_session_invalid():
    app = TestApp(SessionMiddleware(simple_session_app, data_dir='./cache', type='ext:memcached', url=mc_url))
    res = app.get('/invalid', headers=dict(Cookie='beaker.session.id=df7324911e246b70b5781c3c58328442; Path=/'))
    assert 'current value is: 2' in res


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

def test_dropping_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value('test', 20)
    cache.set_value('fred', 10)
    assert cache.has_key('test')
    assert 'test' in cache
    assert cache.has_key('fred')

    # Directly nuke the actual key, to simulate it being removed by memcached
    cache.namespace.mc.delete('test_test')
    assert not cache.has_key('test')
    assert cache.has_key('fred')

    # Nuke the keys dict, it might die, who knows
    cache.namespace.mc.delete('test:keys')
    assert cache.has_key('fred')

    # And we still need clear to work, even if it won't work well
    cache.clear()

def test_deleting_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    cache.set_value('test', 20)

    # Nuke the keys dict, it might die, who knows
    cache.namespace.mc.delete('test:keys')

    assert cache.has_key('test')

    # make sure we can still delete keys even though our keys dict got nuked
    del cache['test']

    assert not cache.has_key('test')

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

def test_long_unicode_keys():
    cache = Cache('test', data_dir='./cache', url=mc_url, type='ext:memcached')
    o = object()
    long_str = u'Очень длинная строка, которая не влезает в сто двадцать восемь байт и поэтому не проходит ограничение в check_key, что очень прискорбно, не правда ли, друзья? Давайте же скорее исправим это досадное недоразумение!'
    cache.set_value(long_str, o)
    assert long_str in cache
    cache.remove_value(long_str)
    assert long_str not in cache

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

@util.skip_if(lambda: TestApp is None, "webtest not installed")
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

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_cache_manager():
    app = TestApp(CacheMiddleware(cache_manager_app))
    res = app.get('/')
    assert 'test_key is: test value' in res
    assert 'test_key cleared' in res

@util.skip_if(lambda: TestApp is None, "webtest not installed")
def test_store_none():
    app = TestApp(CacheMiddleware(using_none_app))
    res = app.get('/', extra_environ={'beaker.clear':True})
    assert 'current value is: 10' in res
    res = app.get('/')
    assert 'current value is: None' in res

class TestPylibmcInit(unittest.TestCase):
    def setUp(self):

        from beaker.ext import memcached
        try:
            import pylibmc as memcache
        except:
            import memcache
            memcached._client_libs['pylibmc'] = memcached.pylibmc = memcache
            from contextlib import contextmanager
            class ThreadMappedPool(dict):
                "a mock of pylibmc's ThreadMappedPool"

                def __init__(self, master):
                    self.master = master

                @contextmanager
                def reserve(self):
                    yield self.master
            memcache.ThreadMappedPool = ThreadMappedPool

    def test_uses_pylibmc_client(self):
        from beaker.ext import memcached
        cache = Cache('test', data_dir='./cache', 
                            memcache_module='pylibmc', 
                            url=mc_url, type="ext:memcached")
        assert isinstance(cache.namespace, memcached.PyLibMCNamespaceManager)

    def test_dont_use_pylibmc_client(self):
        from beaker.ext.memcached import _load_client
        load_mock = mock.Mock()
        load_mock.return_value = _load_client('memcache')
        with mock.patch('beaker.ext.memcached._load_client', load_mock):
            cache = Cache('test', data_dir='./cache', url=mc_url, type="ext:memcached")
            assert not isinstance(cache.namespace, memcached.PyLibMCNamespaceManager)
            assert isinstance(cache.namespace, memcached.MemcachedNamespaceManager)

    def test_client(self):
        cache = Cache('test', data_dir='./cache', url=mc_url, type="ext:memcached", 
                      protocol='binary')
        o = object()
        cache.set_value("test", o)
        assert cache.has_key("test")
        assert "test" in cache
        assert not cache.has_key("foo")
        assert "foo" not in cache
        cache.remove_value("test")
        assert not cache.has_key("test")

    def test_client_behaviors(self):
        config = {
            'cache.lock_dir':'./lock', 
            'cache.data_dir':'./cache',  
            'cache.type':'ext:memcached', 
            'cache.url':mc_url,
            'cache.memcache_module':'pylibmc', 
            'cache.protocol':'binary', 
            'cache.behavior.ketama': 'True', 
            'cache.behavior.cas':False, 
            'cache.behavior.receive_timeout':'3600',
            'cache.behavior.send_timeout':1800, 
            'cache.behavior.tcp_nodelay':1,
            'cache.behavior.auto_eject':"0"
        }
        cache_manager = CacheManager(**parse_cache_config_options(config))
        cache = cache_manager.get_cache('test_behavior', expire=6000)
        
        with cache.namespace.pool.reserve() as mc:
            assert "ketama" in mc.behaviors
            assert mc.behaviors["ketama"] == 1
            assert "cas" in mc.behaviors
            assert mc.behaviors["cas"] == 0
            assert "receive_timeout" in mc.behaviors
            assert mc.behaviors["receive_timeout"] == 3600
            assert "send_timeout" in mc.behaviors
            assert mc.behaviors["send_timeout"] == 1800
            assert "tcp_nodelay" in mc.behaviors
            assert mc.behaviors["tcp_nodelay"] == 1
            assert "auto_eject" in mc.behaviors
            assert mc.behaviors["auto_eject"] == 0
            