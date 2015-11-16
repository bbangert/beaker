import datetime, time
import re
import os

import beaker.session
from beaker.middleware import SessionMiddleware
from nose import SkipTest
try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")

from beaker import crypto
if not crypto.has_aes:
    raise SkipTest("No AES library is installed, can't test cookie-only "
                   "Sessions")

def simple_app(environ, start_response):
    session = environ['beaker.session']
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    msg = 'The current value is: %d and cookie is %s' % (session['value'], session)
    return [msg.encode('UTF-8')]

def test_increment():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_expires():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie',
               'session.cookie_expires': datetime.timedelta(days=1)}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'expires=' in res.headers.getall('Set-Cookie')[0]
    assert 'current value is: 1' in res

def test_different_sessions():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    app2 = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_nosave():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/nosave')
    assert 'current value is: 1' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    assert len(res.headers.getall('Set-Cookie')) > 0
    res = app.get('/')
    assert 'current value is: 2' in res

def test_increment_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_different_sessions_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    app2 = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    assert 'current value is: 1' in res
    res = app2.get('/')
    res = app2.get('/')
    res = app2.get('/')
    res2 = app.get('/')
    assert 'current value is: 2' in res2
    assert 'current value is: 4' in res

def test_nosave_with_encryption():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/nosave')
    assert 'current value is: 1' in res

    res = app.get('/')
    assert 'current value is: 1' in res
    assert len(res.headers.getall('Set-Cookie')) > 0
    res = app.get('/')
    assert 'current value is: 2' in res

def test_cookie_id():
    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))

    res = app.get('/')
    assert "_id':" in res
    sess_id = re.sub(r".*'_id': '(.*?)'.*", r'\1', res.body.decode('utf-8'))
    res = app.get('/')
    new_id = re.sub(r".*'_id': '(.*?)'.*", r'\1', res.body.decode('utf-8'))
    assert new_id == sess_id

def test_invalidate_with_save_does_not_delete_session():
    def invalidate_session_app(environ, start_response):
        session = environ['beaker.session']
        session.invalidate()
        session.save()
        start_response('200 OK', [('Content-type', 'text/plain')])
        return [('Cookie is %s' % session).encode('UTF-8')]

    options = {'session.encrypt_key':'666a19cf7f61c64c', 'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(invalidate_session_app, **options))
    res = app.get('/')
    assert 'expires=' not in res.headers.getall('Set-Cookie')[0]


def test_changing_encrypt_key_with_timeout():
    COMMON_ENCRYPT_KEY = '666a19cf7f61c64c'
    DIFFERENT_ENCRYPT_KEY = 'hello-world'

    options = {'session.encrypt_key': COMMON_ENCRYPT_KEY,
               'session.timeout': 300,
               'session.validate_key': 'hoobermas',
               'session.type': 'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'The current value is: 1' in res, res

    # Get the session cookie, so we can reuse it.
    cookies = res.headers['Set-Cookie']

    # Check that we get the same session with the same cookie
    options = {'session.encrypt_key': COMMON_ENCRYPT_KEY,
               'session.timeout': 300,
               'session.validate_key': 'hoobermas',
               'session.type': 'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', headers={'Cookie': cookies})
    assert 'The current value is: 2' in res, res

    # Now that we are sure that it reuses the same session,
    # change the encrypt_key so that it is unable to understand the cookie.
    options = {'session.encrypt_key': DIFFERENT_ENCRYPT_KEY,
               'session.timeout': 300,
               'session.validate_key': 'hoobermas',
               'session.type': 'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', headers={'Cookie': cookies})

    # Let's check it created a new session as the old one is invalid
    # in the past it just crashed.
    assert 'The current value is: 1' in res, res


def test_cookie_properly_expires():
    COMMON_ENCRYPT_KEY = '666a19cf7f61c64c'

    options = {'session.encrypt_key': COMMON_ENCRYPT_KEY,
               'session.timeout': 1,
               'session.validate_key': 'hoobermas',
               'session.type': 'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'The current value is: 1' in res, res

    res = app.get('/')
    assert 'The current value is: 2' in res, res

    # Wait session to expire and check it starts with a clean one
    time.sleep(1)
    res = app.get('/')
    assert 'The current value is: 1' in res, res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
