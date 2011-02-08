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
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d and cookie is %s' % (session['value'], session)]

def test_increment():
    options = {'session.validate_key':'hoobermas', 'session.type':'cookie'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/', extra_environ=dict(domain='.hoop.com'))
    assert 'current value is: 2' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    res = app.get('/')
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    assert 'current value is: 3' in res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
