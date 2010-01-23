from beaker.middleware import SessionMiddleware
from beaker.session import Session
from nose.tools import *
import webob
import datetime
import re

def test_cookie_expires():
    """Explore valid arguments for cookie_expires."""
    def app(*args, **kw):
        pass

    key = 'beaker.session.cookie_expires'
    now = datetime.datetime.now()
    request = webob.Request.blank('/')

    values = ['300', 300,
        True,  'True',  'true',  't', '1', 1, 
        False, 'False', 'false', 'f', '0', 0,
        datetime.timedelta(minutes=5), now,]

    expected = [None, True, True, True, True, True, True, True,
            False, False, False, False, False, False,
            datetime.timedelta(minutes=5), now]

    actual = []

    for v in values:
        try:
            s = SessionMiddleware(app, config={key:v})
            actual.append(s.options['cookie_expires'])
        except:
            actual.append(None)

    for a, e in zip(actual, expected):
        assert_equal(a, e)

def test_cookie_exprires_2():
    """Exhibit Set-Cookie: values."""
    expires = Session(
            webob.Request.blank('/').environ, cookie_expires=True
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; Path=/', expires), expires
    no_expires = Session(
            webob.Request.blank('/').environ, cookie_expires=False
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; expires=Mon, 18-Jan-2038 22:14:07 GMT; Path=/', no_expires), no_expires

