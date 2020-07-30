from beaker.middleware import SessionMiddleware
from beaker.session import Session
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
        assert val == expected[pos]


def cookie_expiration(session):
    cookie = session.cookie.output()
    expiry_m = re.match('Set-Cookie: beaker.session.id=[0-9a-f]{32}(; expires=[^;]+)?; Path=/', cookie)
    assert expiry_m
    expiry = expiry_m.group(1)
    if expiry is None:
        return True
    if re.match('; expires=(Mon|Tue), 1[89]-Jan-2038 [0-9:]{8} GMT', expiry):
        return False
    else:
        return expiry[10:]


def test_cookie_exprires_2():
    """Exhibit Set-Cookie: values."""
    expires = cookie_expiration(Session({}, cookie_expires=True))

    assert expires is True, expires
    no_expires = cookie_expiration(Session({}, cookie_expires=False))

    assert no_expires is False, no_expires

def test_cookie_expires_different_locale():
    from locale import setlocale, LC_TIME
    expires_date = datetime.datetime(2019, 5, 22)
    setlocale(LC_TIME, 'it_IT.UTF-8')
    # if you get locale.Error: unsupported locale setting. you have to enable that locale in your OS.
    assert expires_date.strftime("%a, %d-%b-%Y %H:%M:%S GMT").startswith('mer,')
    session = Session({}, cookie_expires=True, validate_key='validate_key')
    assert session._set_cookie_expires(expires_date)
    expires = cookie_expiration(session)
    assert expires == 'Wed, 22-May-2019 00:00:00 GMT', expires
    setlocale(LC_TIME, '')  # restore default locale for further tests

def test_set_cookie_expires():
    """Exhibit Set-Cookie: values."""
    session = Session({}, cookie_expires=True)
    assert cookie_expiration(session) is True
    session._set_cookie_expires(False)
    assert cookie_expiration(session) is False
    session._set_cookie_expires(True)
    assert cookie_expiration(session) is True
