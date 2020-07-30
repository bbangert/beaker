from beaker.middleware import SessionMiddleware
from unittest import SkipTest
try:
    from webtest import TestApp as WebTestApp
except ImportError:
    raise SkipTest("webtest not installed")

def teardown_module():
    import shutil
    shutil.rmtree('./cache', True)

def simple_app(environ, start_response):
    session = environ['beaker.session']
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if 'value' not in session:
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    msg = 'The current value is: %s, session id is %s' % (session.get('value', 0),
                                                          session.id)
    return [msg.encode('utf-8')]


def test_same_domain():
    options = {'session.data_dir':'./cache',
               'session.secret':'blah',
               'session.cookie_domain': '.hoop.com'}
    app = WebTestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', extra_environ=dict(HTTP_HOST='subdomain.hoop.com'))
    assert 'current value is: 1' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    res = app.get('/', extra_environ=dict(HTTP_HOST='another.hoop.com'))
    assert 'current value is: 2' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/', extra_environ=dict(HTTP_HOST='more.subdomain.hoop.com'))
    assert 'current value is: 3' in res


def test_different_domain():
    options = {'session.data_dir':'./cache',
               'session.secret':'blah'}
    app = WebTestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', extra_environ=dict(domain='.hoop.com',
                                          HTTP_HOST='www.hoop.com'))
    res = app.get('/', extra_environ=dict(domain='.hoop.co.uk',
                                          HTTP_HOST='www.hoop.com'))
    assert 'Domain=.hoop.co.uk' in res.headers['Set-Cookie']
    assert 'current value is: 2' in res

    res = app.get('/', extra_environ=dict(domain='.hoop.co.uk',
                                          HTTP_HOST='www.test.com'))
    assert 'current value is: 1' in res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
