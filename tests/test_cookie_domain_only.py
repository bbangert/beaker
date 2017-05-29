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
if not crypto.get_crypto_module('default').has_aes:
    raise SkipTest("No AES library is installed, can't test cookie-only "
                   "Sessions")

def simple_app(environ, start_response):
    session = environ['beaker.session']
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    msg = 'The current value is: %d and cookie is %s' % (session['value'], session)
    return [msg.encode('utf-8')]


def test_increment():
    options = {'session.validate_key':'hoobermas',
               'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res

    res = app.get('/', extra_environ=dict(domain='.hoop.com',
                                          HTTP_HOST='www.hoop.com'))
    assert 'current value is: 1' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']

    res = app.get('/', extra_environ=dict(HTTP_HOST='www.hoop.com'))
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    assert 'current value is: 2' in res


def test_cookie_attributes_are_preserved():
    options = {'session.type': 'memory',
               'session.httponly': True,
               'session.secure': True,
               'session.cookie_path': '/app',
               'session.cookie_domain': 'localhost'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/app', extra_environ=dict(
        HTTP_COOKIE='beaker.session.id=oldsessid', domain='.hoop.com'))
    cookie = res.headers['Set-Cookie']
    assert 'Domain=.hoop.com' in cookie
    assert 'Path=/app' in cookie
    assert 'secure' in cookie
    assert 'httponly' in cookie


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
