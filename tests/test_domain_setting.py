import re
import os

from beaker.middleware import SessionMiddleware
from nose import SkipTest
try:
    from webtest import TestApp
except ImportError:
    raise SkipTest("webtest not installed")

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def simple_app(environ, start_response):
    session = environ['beaker.session']
    domain = environ.get('domain')
    if domain:
        session.domain = domain
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d, session id is %s' % (session['value'],
                                                            session.id)]


def test_domain():
    options = {'session.data_dir':'./cache', 'session.secret':'blah', 'session.cookie_domain': '.test.com'}
    app = TestApp(SessionMiddleware(simple_app, **options))
    res = app.get('/', extra_environ=dict(domain='.hoop.com'))
    assert 'current value is: 1' in res
    assert 'Domain=.hoop.com' in res.headers['Set-Cookie']
    res = app.get('/')
    assert 'current value is: 2' in res
    assert [] == res.headers.getall('Set-Cookie')
    res = app.get('/', extra_environ=dict(domain='.hoop.co.uk'))
    assert 'current value is: 3' in res
    assert 'Domain=.hoop.co.uk' in res.headers['Set-Cookie']



if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
