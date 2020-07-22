import pytest

from beaker.middleware import SessionMiddleware
from beaker import crypto

webtest = pytest.importorskip("webtest", reason="webtest not installed")

pytest.mark.skipif(not crypto.get_crypto_module('default').has_aes,
                   reason="No AES library is installed, can't test " +
                   "cookie-only Sessions")


def simple_app(environ, start_response):
    session = environ['beaker.session']
    if 'value' not in session:
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
    app = webtest.TestApp(SessionMiddleware(simple_app, **options))
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
    app = webtest.TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/app', extra_environ=dict(
        HTTP_COOKIE='beaker.session.id=oldsessid', domain='.hoop.com'))
    cookie = res.headers['Set-Cookie']
    assert 'domain=.hoop.com' in cookie.lower()
    assert 'path=/app' in cookie.lower()
    assert 'secure' in cookie.lower()
    assert 'httponly' in cookie.lower()
    assert 'samesite=lax' in cookie.lower()


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
