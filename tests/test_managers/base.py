# coding: utf-8
import threading
import unittest

import time

import datetime

from beaker._compat import u_
from beaker.cache import Cache
from beaker.middleware import SessionMiddleware, CacheMiddleware
from webtest import TestApp as WebTestApp


class CacheManagerBaseTests(unittest.TestCase):
    SUPPORTS_EXPIRATION = True
    SUPPORTS_TIMEOUT = True
    CACHE_ARGS = {}

    @classmethod
    def setUpClass(cls):
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
                    return [("No session id of %s found." % sess_id).encode('utf-8')]
                if not session.has_key('value'):
                    session['value'] = 0
                session['value'] += 1
                if not environ['PATH_INFO'].startswith('/nosave'):
                    session.save()
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [('The current value is: %d, session id is %s' % (session['value'],
                                                                     session.id)).encode('utf-8')]

        def simple_app(environ, start_response):
            extra_args = cls.CACHE_ARGS
            clear = False
            if environ.get('beaker.clear'):
                clear = True
            cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
            if clear:
                cache.clear()
            try:
                value = cache.get_value('value')
            except:
                value = 0
            cache.set_value('value', value + 1)
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [('The current value is: %s' % cache.get_value('value')).encode('utf-8')]

        def using_none_app(environ, start_response):
            extra_args = cls.CACHE_ARGS
            clear = False
            if environ.get('beaker.clear'):
                clear = True
            cache = environ['beaker.cache'].get_cache('testcache', **extra_args)
            if clear:
                cache.clear()
            try:
                value = cache.get_value('value')
            except:
                value = 10
            cache.set_value('value', None)
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [('The current value is: %s' % value).encode('utf-8')]

        def cache_manager_app(environ, start_response):
            cm = environ['beaker.cache']
            cm.get_cache('test')['test_key'] = 'test value'

            start_response('200 OK', [('Content-type', 'text/plain')])
            yield ("test_key is: %s\n" % cm.get_cache('test')['test_key']).encode('utf-8')
            cm.get_cache('test').clear()

            try:
                test_value = cm.get_cache('test')['test_key']
            except KeyError:
                yield "test_key cleared".encode('utf-8')
            else:
                yield (
                    "test_key wasn't cleared, is: %s\n" % cm.get_cache('test')['test_key']
                ).encode('utf-8')

        cls.simple_session_app = staticmethod(simple_session_app)
        cls.simple_app = staticmethod(simple_app)
        cls.using_none_app = staticmethod(using_none_app)
        cls.cache_manager_app = staticmethod(cache_manager_app)

    def setUp(self):
        Cache('test', **self.CACHE_ARGS).clear()

    def test_session(self):
        app = WebTestApp(SessionMiddleware(self.simple_session_app, **self.CACHE_ARGS))
        res = app.get('/')
        assert 'current value is: 1' in res
        res = app.get('/')
        assert 'current value is: 2' in res
        res = app.get('/')
        assert 'current value is: 3' in res

    def test_session_invalid(self):
        app = WebTestApp(SessionMiddleware(self.simple_session_app, **self.CACHE_ARGS))
        res = app.get('/invalid', headers=dict(
            Cookie='beaker.session.id=df7324911e246b70b5781c3c58328442; Path=/'))
        assert 'current value is: 2' in res

    def test_session_timeout(self):
        app = WebTestApp(SessionMiddleware(self.simple_session_app, timeout=1, **self.CACHE_ARGS))

        session = app.app._get_session()
        session.save()
        if self.SUPPORTS_TIMEOUT:
            assert session.namespace.timeout == 121

        res = app.get('/')
        assert 'current value is: 1' in res
        res = app.get('/')
        assert 'current value is: 2' in res
        res = app.get('/')
        assert 'current value is: 3' in res

    def test_has_key(self):
        cache = Cache('test', **self.CACHE_ARGS)
        o = object()
        cache.set_value("test", o)
        assert cache.has_key("test")
        assert "test" in cache
        assert not cache.has_key("foo")
        assert "foo" not in cache
        cache.remove_value("test")
        assert not cache.has_key("test")

    def test_clear(self):
        cache = Cache('test', **self.CACHE_ARGS)
        cache.set_value('test', 20)
        cache.set_value('fred', 10)
        assert cache.has_key('test')
        assert 'test' in cache
        assert cache.has_key('fred')
        cache.clear()
        assert not cache.has_key("test")

    def test_has_key_multicache(self):
        cache = Cache('test', **self.CACHE_ARGS)
        o = object()
        cache.set_value("test", o)
        assert cache.has_key("test")
        assert "test" in cache
        cache = Cache('test', **self.CACHE_ARGS)
        assert cache.has_key("test")

    def test_unicode_keys(self):
        cache = Cache('test', **self.CACHE_ARGS)
        o = object()
        cache.set_value(u_('hiŏ'), o)
        assert u_('hiŏ') in cache
        assert u_('hŏa') not in cache
        cache.remove_value(u_('hiŏ'))
        assert u_('hiŏ') not in cache

    def test_long_unicode_keys(self):
        cache = Cache('test', **self.CACHE_ARGS)
        o = object()
        long_str = u_(
            'Очень длинная строка, которая не влезает в сто двадцать восемь байт и поэтому не проходит ограничение в check_key, что очень прискорбно, не правда ли, друзья? Давайте же скорее исправим это досадное недоразумение!'
        )
        cache.set_value(long_str, o)
        assert long_str in cache
        cache.remove_value(long_str)
        assert long_str not in cache

    def test_spaces_in_unicode_keys(self):
        cache = Cache('test', **self.CACHE_ARGS)
        o = object()
        cache.set_value(u_('hi ŏ'), o)
        assert u_('hi ŏ') in cache
        assert u_('hŏa') not in cache
        cache.remove_value(u_('hi ŏ'))
        assert u_('hi ŏ') not in cache

    def test_spaces_in_keys(self):
        cache = Cache('test', **self.CACHE_ARGS)
        cache.set_value("has space", 24)
        assert cache.has_key("has space")
        assert 24 == cache.get_value("has space")
        cache.set_value("hasspace", 42)
        assert cache.has_key("hasspace")
        assert 42 == cache.get_value("hasspace")

    def test_increment(self):
        app = WebTestApp(CacheMiddleware(self.simple_app))
        res = app.get('/', extra_environ={'beaker.clear': True})
        assert 'current value is: 1' in res
        res = app.get('/')
        assert 'current value is: 2' in res
        res = app.get('/')
        assert 'current value is: 3' in res

        app = WebTestApp(CacheMiddleware(self.simple_app))
        res = app.get('/', extra_environ={'beaker.clear': True})
        assert 'current value is: 1' in res
        res = app.get('/')
        assert 'current value is: 2' in res
        res = app.get('/')
        assert 'current value is: 3' in res

    def test_cache_manager(self):
        app = WebTestApp(CacheMiddleware(self.cache_manager_app))
        res = app.get('/')
        assert 'test_key is: test value' in res
        assert 'test_key cleared' in res

    def test_store_none(self):
        app = WebTestApp(CacheMiddleware(self.using_none_app))
        res = app.get('/', extra_environ={'beaker.clear': True})
        assert 'current value is: 10' in res
        res = app.get('/')
        assert 'current value is: None' in res

    def test_expiretime(self):
        cache = Cache('test', **self.CACHE_ARGS)
        cache.set_value("has space", 24, expiretime=1)
        assert cache.has_key("has space")
        time.sleep(1.1)
        assert not cache.has_key("has space")

    def test_expiretime_automatic(self):
        if not self.SUPPORTS_EXPIRATION:
            self.skipTest('NamespaceManager does not support automatic expiration')

        cache = Cache('test', **self.CACHE_ARGS)
        cache.set_value("has space", 24, expiretime=1)
        assert cache.namespace.has_key("has space")
        time.sleep(1.1)
        assert not cache.namespace.has_key("has space")

    def test_createfunc(self):
        cache = Cache('test', **self.CACHE_ARGS)

        def createfunc():
            createfunc.count += 1
            return createfunc.count
        createfunc.count = 0

        def keepitlocked():
            lock = cache.namespace.get_creation_lock('test')
            lock.acquire()
            keepitlocked.acquired = True
            time.sleep(1.0)
            lock.release()
        keepitlocked.acquired = False

        v0 = cache.get_value('test', createfunc=createfunc)
        self.assertEqual(v0, 1)

        v0 = cache.get_value('test', createfunc=createfunc)
        self.assertEqual(v0, 1)

        cache.remove_value('test')

        begin = datetime.datetime.utcnow()
        t = threading.Thread(target=keepitlocked)
        t.start()
        while not keepitlocked.acquired:
            # Wait for the thread that should lock the cache to start.
            time.sleep(0.001)

        v0 = cache.get_value('test', createfunc=createfunc)
        self.assertEqual(v0, 2)

        # Ensure that the `get_value` was blocked by the concurrent thread.
        assert datetime.datetime.utcnow() - begin > datetime.timedelta(seconds=1)

        t.join()
