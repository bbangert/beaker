from beaker.middleware import SessionMiddleware
from beaker.session import Session
from nose.tools import *
import datetime
import re

def test_cookie_expires():
    """Explore valid arguments for cookie_expires."""
    def app(*args, **kw):
        pass

    key = 'beaker.session.cookie_expires'
    now = datetime.datetime.now()

    values = ['300', 300,
        True,  'True',  'true',  't',
        False, 'False', 'false', 'f',
        datetime.timedelta(minutes=5), now]

    expected = [datetime.timedelta(seconds=300),
            datetime.timedelta(seconds=300), 
            True, True, True, True,
            False, False, False, False,
            datetime.timedelta(minutes=5), now]

    actual = []

    for pos, v in enumerate(values):
        try:
            s = SessionMiddleware(app, config={key:v})
            val = s.options['cookie_expires']
        except:
            val = None
        assert_equal(val, expected[pos])


def test_cookie_exprires_2():
    """Exhibit Set-Cookie: values."""
    expires = Session(
            {}, cookie_expires=True
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; Path=/', expires), expires
    no_expires = Session(
            {}, cookie_expires=False
            ).cookie.output()

    assert re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}; expires=(Mon|Tue), 1[89]-Jan-2038 [0-9:]{8} GMT; Path=/', no_expires), no_expires

