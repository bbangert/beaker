# -*- coding: utf-8 -*-
from beaker._compat import u_, pickle

import binascii
import sys
import time
import warnings

from nose import SkipTest, with_setup

from beaker.crypto import has_aes
from beaker.session import CookieSession, Session
from beaker import util


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session({}, **options)


COOKIE_REQUEST = {}
def setup_cookie_request():
    COOKIE_REQUEST.clear()


def get_cookie_session(**kwargs):
    """A shortcut for creating :class:`CookieSession` instance"""
    options = {'validate_key': 'test_key'}
    options.update(**kwargs)
    if COOKIE_REQUEST.get('set_cookie'):
        cookie_out = COOKIE_REQUEST.get('cookie_out')
        key = 'beaker.session.id'
        cookie_out = cookie_out[cookie_out.index(key) + len(key) + 1:]
        cookie_out = cookie_out[:cookie_out.index(';')]

        COOKIE_REQUEST['cookie'] = {key: cookie_out}
    return CookieSession(COOKIE_REQUEST, **options)


@with_setup(setup_cookie_request)
def test_session():
    for test_case in (
        check_save_load,
        check_save_load_encryption,
        check_decryption_failure,
        check_delete,
        check_revert,
        check_invalidate,
        check_timeout,
    ):
      for session_getter in (get_session,):
            setup_cookie_request()
            yield test_case, session_getter


def check_save_load(session_getter):
    """Test if the data is actually persistent across requests"""
    session = session_getter()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = session_getter(id=session.id)
    assert u_('Suomi') in session
    assert u_('Great Britain') in session
    assert u_('Deutchland') in session

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')


def check_save_load_encryption(session_getter):
    """Test if the data is actually persistent across requests"""
    if not has_aes:
        raise SkipTest()
    session = session_getter(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = session_getter(id=session.id, encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    assert u_('Suomi') in session
    assert u_('Great Britain') in session
    assert u_('Deutchland') in session

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')


def check_decryption_failure(session_getter):
    """Test if the data fails without the right keys"""
    if not has_aes:
        raise SkipTest()
    session = session_getter(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = session_getter(id=session.id, encrypt_key='asfdasdfadsfsadf',
                          validate_key='hoobermas', invalidate_corrupt=True)
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session


def check_delete(session_getter):
    """Test :meth:`Session.delete`"""
    session = session_getter()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.delete()

    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


def check_revert(session_getter):
    """Test :meth:`Session.revert`"""
    session = session_getter()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = session_getter(id=session.id)
    del session[u_('Suomi')]
    session[u_('Great Britain')] = u_('Lewis Hamilton')
    session[u_('Deutchland')] = u_('Michael Schumacher')
    session[u_('España')] = u_('Fernando Alonso')
    session.revert()

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')
    assert u_('España') not in session


def check_invalidate(session_getter):
    """Test :meth:`Session.invalidate`"""
    session = session_getter()
    session.save()
    id = session.id
    created = session.created
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.invalidate()
    session.save()

    assert session.id != id
    assert session.created != created
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


@with_setup(setup_cookie_request)
def test_regenerate_id():
    """Test :meth:`Session.regenerate_id`"""
    # new session & save
    session = get_session()
    orig_id = session.id
    session[u_('foo')] = u_('bar')
    session.save()

    # load session
    session = get_session(id=session.id)
    # data should still be there
    assert session[u_('foo')] == u_('bar')

    # regenerate the id
    session.regenerate_id()

    assert session.id != orig_id

    # data is still there
    assert session[u_('foo')] == u_('bar')

    # should be the new id
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    # get a new session before calling save
    bunk_sess = get_session(id=session.id)
    assert u_('foo') not in bunk_sess

    # save it
    session.save()

    # make sure we get the data back
    session = get_session(id=session.id)
    assert session[u_('foo')] == u_('bar')


def check_timeout(session_getter):
    """Test if the session times out properly"""
    session = session_getter(timeout=2)
    session.save()
    id = session.id
    created = session.created
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = session_getter(id=session.id, timeout=2)
    assert session.id == id
    assert session.created == created
    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')

    time.sleep(2)
    session = session_getter(id=session.id, timeout=2)
    assert session.id != id
    assert session.created != created
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


@with_setup(setup_cookie_request)
def test_cookies_enabled():
    """
    Test if cookies are sent out properly when ``use_cookies``
    is set to ``True``
    """
    session = get_session(use_cookies=True)
    assert 'cookie_out' in session.request
    assert session.request['set_cookie'] == False

    session.domain = 'example.com'
    session.path = '/example'
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']
    assert 'Domain=example.com' in session.request['cookie_out']
    assert 'Path=/' in session.request['cookie_out']

    session = get_session(use_cookies=True)
    session.save()
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    session = get_session(use_cookies=True, id=session.id)
    session.delete()
    assert session.request['set_cookie'] == True
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']
    assert 'expires=' in session.request['cookie_out']

    # test for secure
    session = get_session(use_cookies=True, secure=True)
    cookie = session.request['cookie_out'].lower()  # Python3.4.3 outputs "Secure", while previous output "secure"
    assert 'secure' in cookie, cookie

    # test for httponly
    class ShowWarning(object):
        def __init__(self):
            self.msg = None
        def __call__(self, message, category, filename, lineno, file=None, line=None):
            self.msg = str(message)
    orig_sw = warnings.showwarning
    sw = ShowWarning()
    warnings.showwarning = sw
    session = get_session(use_cookies=True, httponly=True)
    if sys.version_info < (2, 6):
        assert sw.msg == 'Python 2.6+ is required to use httponly'
    else:
        # Python3.4.3 outputs "HttpOnly", while previous output "httponly"
        cookie = session.request['cookie_out'].lower()
        assert 'httponly' in cookie, cookie
    warnings.showwarning = orig_sw

def tes_cookies_disabled():
    """
    Test that no cookies are sent when ``use_cookies`` is set to ``False``
    """
    session = get_session(use_cookies=False)
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session.save()
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session = get_session(use_cookies=False, id=session.id)
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request

    session.delete()
    assert 'set_cookie' not in session.request
    assert 'cookie_out' not in session.request


@with_setup(setup_cookie_request)
def test_file_based_replace_optimization():
    """Test the file-based backend with session,
    which includes the 'replace' optimization.

    """

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache')

    session['foo'] = 'foo'
    session['bar'] = 'bar'
    session.save()

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache', id=session.id)
    assert session['foo'] == 'foo'
    assert session['bar'] == 'bar'

    session['bar'] = 'bat'
    session['bat'] = 'hoho'
    session.save()

    session.namespace.do_open('c', False)
    session.namespace['test'] = 'some test'
    session.namespace.do_close()

    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache', id=session.id)

    session.namespace.do_open('r', False)
    assert session.namespace['test'] == 'some test'
    session.namespace.do_close()

    assert session['foo'] == 'foo'
    assert session['bar'] == 'bat'
    assert session['bat'] == 'hoho'
    session.save()

    # the file has been replaced, so our out-of-session
    # key is gone
    session.namespace.do_open('r', False)
    assert 'test' not in session.namespace
    session.namespace.do_close()


@with_setup(setup_cookie_request)
def test_invalidate_corrupt():
    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache')
    session['foo'] = 'bar'
    session.save()

    f = open(session.namespace.file, 'w')
    f.write("crap")
    f.close()

    util.assert_raises(
        (pickle.UnpicklingError, EOFError, TypeError, binascii.Error),
        get_session,
        use_cookies=False, type='file',
                data_dir='./cache', id=session.id
    )

    session = get_session(use_cookies=False, type='file',
                            invalidate_corrupt=True,
                            data_dir='./cache', id=session.id)
    assert "foo" not in dict(session)


@with_setup(setup_cookie_request)
def test_invalidate_corrupt_cookie():
    session = get_cookie_session()
    session['foo'] = 'bar'
    session.save()

    COOKIE_REQUEST['cookie_out'] = ' beaker.session.id=fakecookie; Path=/'

    util.assert_raises(
        (pickle.UnpicklingError, EOFError, TypeError, binascii.Error),
        get_cookie_session,
        id=session.id
    )

    session = get_cookie_session(invalidate_corrupt=True, id=session.id)
    assert "foo" not in dict(session)
