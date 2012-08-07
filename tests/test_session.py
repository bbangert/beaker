# -*- coding: utf-8 -*-
import sys
import time
import warnings

from nose import SkipTest

from beaker.crypto import has_aes
from beaker.session import Session
from beaker import util


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session({}, **options)


def test_save_load():
    """Test if the data is actually persistent across requests"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id)
    assert u'Suomi' in session
    assert u'Great Britain' in session
    assert u'Deutchland' in session

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'


def test_save_load_encryption():
    """Test if the data is actually persistent across requests"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    assert u'Suomi' in session
    assert u'Great Britain' in session
    assert u'Deutchland' in session

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'


def test_decryption_failure():
    """Test if the data fails without the right keys"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, encrypt_key='asfdasdfadsfsadf',
                          validate_key='hoobermas', invalidate_corrupt=True)
    assert u'Suomi' not in session
    assert u'Great Britain' not in session


def test_delete():
    """Test :meth:`Session.delete`"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.delete()

    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


def test_revert():
    """Test :meth:`Session.revert`"""
    session = get_session()
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id)
    del session[u'Suomi']
    session[u'Great Britain'] = u'Lewis Hamilton'
    session[u'Deutchland'] = u'Michael Schumacher'
    session[u'España'] = u'Fernando Alonso'
    session.revert()

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'
    assert u'España' not in session


def test_invalidate():
    """Test :meth:`Session.invalidate`"""
    session = get_session()
    id = session.id
    created = session.created
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.invalidate()

    assert session.id != id
    assert session.created != created
    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


def test_regenerate_id():
    """Test :meth:`Session.regenerate_id`"""
    # new session & save
    session = get_session()
    orig_id = session.id
    session[u'foo'] = u'bar'
    session.save()

    # load session
    session = get_session(id=session.id)
    # data should still be there
    assert session[u'foo'] == u'bar'

    # regenerate the id
    session.regenerate_id()

    assert session.id != orig_id

    # data is still there
    assert session[u'foo'] == u'bar'

    # should be the new id
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    # get a new session before calling save
    bunk_sess = get_session(id=session.id)
    assert u'foo' not in bunk_sess

    # save it
    session.save()

    # make sure we get the data back
    session = get_session(id=session.id)
    assert session[u'foo'] == u'bar'


def test_timeout():
    """Test if the session times out properly"""
    session = get_session(timeout=2)
    id = session.id
    created = session.created
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, timeout=2)
    assert session.id == id
    assert session.created == created
    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'

    time.sleep(2)
    session = get_session(id=session.id, timeout=2)
    assert session.id != id
    assert session.created != created
    assert u'Suomi' not in session
    assert u'Great Britain' not in session
    assert u'Deutchland' not in session


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
    assert 'secure' in session.request['cookie_out']

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
        assert 'httponly' in session.request['cookie_out']
    warnings.showwarning = orig_sw

def test_cookies_disabled():
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


def test_invalidate_corrupt():
    session = get_session(use_cookies=False, type='file',
                            data_dir='./cache')
    session['foo'] = 'bar'
    session.save()

    f = open(session.namespace.file, 'w')
    f.write("crap")
    f.close()

    util.assert_raises(
        util.pickle.UnpicklingError,
        get_session,
        use_cookies=False, type='file',
                data_dir='./cache', id=session.id
    )

    session = get_session(use_cookies=False, type='file',
                            invalidate_corrupt=True,
                            data_dir='./cache', id=session.id)
    assert "foo" not in dict(session)
