from paste.fixture import TestApp
from beaker.middleware import SessionMiddleware

def simple_app(environ, start_response):
    session = environ['beaker.session']
    if not session.has_key('value'):
        session['value'] = 0
    session['value'] += 1
    if not environ['PATH_INFO'].startswith('/nosave'):
        session.save()
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['The current value is: %d' % session['value']]

def test_increment():
    app = TestApp(SessionMiddleware(simple_app))
    res = app.get('/')
    assert 'current value is: 1' in res
    res = app.get('/')
    assert 'current value is: 2' in res
    res = app.get('/')
    assert 'current value is: 3' in res

def test_different_sessions():
    app = TestApp(SessionMiddleware(simple_app))
    app2 = TestApp(SessionMiddleware(simple_app))
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
    app = TestApp(SessionMiddleware(simple_app))
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    assert [] == res.all_headers('Set-Cookie')
    res = app.get('/nosave')
    assert 'current value is: 1' in res
    
    res = app.get('/')
    assert 'current value is: 1' in res
    assert len(res.all_headers('Set-Cookie')) > 0
    res = app.get('/')
    assert [] == res.all_headers('Set-Cookie')
    assert 'current value is: 2' in res


if __name__ == '__main__':
    from paste import httpserver
    wsgi_app = SessionMiddleware(simple_app, {})
    httpserver.serve(wsgi_app, host='127.0.0.1', port=8080)
