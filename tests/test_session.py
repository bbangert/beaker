# -*- coding: utf-8 -*-
from beaker._compat import pickle, b64decode

import binascii
import shutil
import sys
import time
import unittest
import warnings

import pytest

from beaker.container import MemoryNamespaceManager
from beaker.crypto import get_crypto_module
from beaker.exceptions import BeakerException
from beaker.session import CookieSession, Session, SessionObject
from beaker.util import deserialize


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
        COOKIE_REQUEST['cookie'] = COOKIE_REQUEST.get('cookie_out')
    return CookieSession(COOKIE_REQUEST, **options)


def test_session():
    setup_cookie_request()
    for test_case in (
        check_save_load,
        check_save_load_encryption,
        check_save_load_encryption_cryptography,
        check_decryption_failure,
        check_delete,
        check_revert,
        check_invalidate,
        check_timeout,
    ):
        for session_getter in (get_session, get_cookie_session,):
            setup_cookie_request()
            test_case(session_getter)


def check_save_load(session_getter):
    """Test if the data is actually persistent across requests"""
    session = session_getter()
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(id=session.id)
    assert 'Suomi' in session
    assert 'Great Britain' in session
    assert 'Deutchland' in session

    assert session['Suomi'] == 'Kimi Räikkönen'
    assert session['Great Britain'] == 'Jenson Button'
    assert session['Deutchland'] == 'Sebastian Vettel'


@pytest.mark.skipif(not get_crypto_module('default').has_aes)
def check_save_load_encryption(session_getter):
    """Test if the data is actually persistent across requests"""
    session = session_getter(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(id=session.id, encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    assert 'Suomi' in session
    assert 'Great Britain' in session
    assert 'Deutchland' in session

    assert session['Suomi'] == 'Kimi Räikkönen'
    assert session['Great Britain'] == 'Jenson Button'
    assert session['Deutchland'] == 'Sebastian Vettel'


# cryptography only works for py3.3+, so skip for python 3.2
@pytest.mark.skipif(sys.version_info[0] == 3 and sys.version_info[1] < 3,
                    reason="Cryptography not supported on Python 3 lower than 3.3")
def check_save_load_encryption_cryptography(session_getter):
    """Test if the data is actually persistent across requests"""
    try:
        get_crypto_module('cryptography').has_aes
    except BeakerException:
        raise unittest.SkipTest()
    session = session_getter(
        encrypt_key='666a19cf7f61c64c',
        validate_key='hoobermas',
        crypto_type='cryptography')
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(
        id=session.id, encrypt_key='666a19cf7f61c64c',
        validate_key='hoobermas',
        crypto_type='cryptography')
    assert 'Suomi' in session
    assert 'Great Britain' in session
    assert 'Deutchland' in session

    assert session['Suomi'] == 'Kimi Räikkönen'
    assert session['Great Britain'] == 'Jenson Button'
    assert session['Deutchland'] == 'Sebastian Vettel'


@pytest.mark.skipif(not get_crypto_module('default').has_aes)
def check_decryption_failure(session_getter):
    """Test if the data fails without the right keys"""
    session = session_getter(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(id=session.id, encrypt_key='asfdasdfadsfsadf',
                          validate_key='hoobermas', invalidate_corrupt=True)
    assert 'Suomi' not in session
    assert 'Great Britain' not in session


def check_delete(session_getter):
    """Test :meth:`Session.delete`"""
    session = session_getter()
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.delete()

    assert 'Suomi' not in session
    assert 'Great Britain' not in session
    assert 'Deutchland' not in session


def check_revert(session_getter):
    """Test :meth:`Session.revert`"""
    session = session_getter()
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(id=session.id)
    del session['Suomi']
    session['Great Britain'] = 'Lewis Hamilton'
    session['Deutchland'] = 'Michael Schumacher'
    session['España'] = 'Fernando Alonso'
    session.revert()

    assert session['Suomi'] == 'Kimi Räikkönen'
    assert session['Great Britain'] == 'Jenson Button'
    assert session['Deutchland'] == 'Sebastian Vettel'
    assert 'España' not in session


def check_invalidate(session_getter):
    """Test :meth:`Session.invalidate`"""
    session = session_getter()
    session.save()
    id = session.id
    created = session.created
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.invalidate()
    session.save()

    assert session.id != id
    assert session.created != created
    assert 'Suomi' not in session
    assert 'Great Britain' not in session
    assert 'Deutchland' not in session


def test_regenerate_id():
    """Test :meth:`Session.regenerate_id`"""
    # new session & save
    setup_cookie_request()
    session = get_session()
    orig_id = session.id
    session['foo'] = 'bar'
    session.save()

    # load session
    session = get_session(id=session.id)
    # data should still be there
    assert session['foo'] == 'bar'

    # regenerate the id
    session.regenerate_id()

    assert session.id != orig_id

    # data is still there
    assert session['foo'] == 'bar'

    # should be the new id
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    # get a new session before calling save
    bunk_sess = get_session(id=session.id)
    assert 'foo' not in bunk_sess

    # save it
    session.save()

    # make sure we get the data back
    session = get_session(id=session.id)
    assert session['foo'] == 'bar'


def check_timeout(session_getter):
    """Test if the session times out properly"""
    session = session_getter(timeout=2)
    session.save()
    id = session.id
    created = session.created
    session['Suomi'] = 'Kimi Räikkönen'
    session['Great Britain'] = 'Jenson Button'
    session['Deutchland'] = 'Sebastian Vettel'
    session.save()

    session = session_getter(id=session.id, timeout=2)
    assert session.id == id
    assert session.created == created
    assert session['Suomi'] == 'Kimi Räikkönen'
    assert session['Great Britain'] == 'Jenson Button'
    assert session['Deutchland'] == 'Sebastian Vettel'

    time.sleep(2)
    session = session_getter(id=session.id, timeout=2)
    assert session.id != id
    assert session.created != created
    assert 'Suomi' not in session
    assert 'Great Britain' not in session
    assert 'Deutchland' not in session


def test_timeout_requires_accessed_time():
    """Test that it doesn't allow setting save_accessed_time to False with
    timeout enabled
    """
    setup_cookie_request()
    get_session(timeout=None, save_accessed_time=True)  # is ok
    get_session(timeout=None, save_accessed_time=False)  # is ok
    with pytest.raises(BeakerException):
        get_session(timeout=2, save_accessed_time=False)


def test_cookies_enabled():
    """
    Test if cookies are sent out properly when ``use_cookies``
    is set to ``True``
    """
    setup_cookie_request()
    session = get_session(use_cookies=True)
    assert 'cookie_out' in session.request
    assert not session.request['set_cookie']

    session.domain = 'example.com'
    session.path = '/example'
    assert session.request['set_cookie']
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']
    assert 'Domain=example.com' in session.request['cookie_out']
    assert 'Path=/' in session.request['cookie_out']

    session = get_session(use_cookies=True)
    session.save()
    assert session.request['set_cookie']
    assert 'beaker.session.id=%s' % session.id in session.request['cookie_out']

    session = get_session(use_cookies=True, id=session.id)
    session.delete()
    assert session.request['set_cookie']
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
    setup_cookie_request()

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

def test_use_json_serializer_without_encryption_key():
    setup_cookie_request()
    so = get_session(use_cookies=False, type='file', data_dir='./cache', data_serializer='json')
    so['foo'] = 'bar'
    so.save()
    session = get_session(id=so.id, use_cookies=False, type='file', data_dir='./cache', data_serializer='json')
    assert 'foo' in session
    serialized_session = open(session.namespace.file, 'rb').read()
    memory_state = pickle.loads(serialized_session)
    session_data = b64decode(memory_state.get('session'))
    data = deserialize(session_data, 'json')
    assert 'foo' in data


def test_invalidate_corrupt():
    setup_cookie_request()
    session = get_session(use_cookies=False, type='file',
                          data_dir='./cache')
    session['foo'] = 'bar'
    session.save()

    f = open(session.namespace.file, 'w')
    f.write("crap")
    f.close()

    with pytest.raises((pickle.UnpicklingError, EOFError, TypeError, binascii.Error,)):
        get_session(use_cookies=False, type='file',
                    data_dir='./cache', id=session.id)

    session = get_session(use_cookies=False, type='file',
                            invalidate_corrupt=True,
                            data_dir='./cache', id=session.id)
    assert "foo" not in dict(session)


def test_invalidate_empty_cookie():
    setup_cookie_request()
    kwargs = {'validate_key': 'test_key', 'encrypt_key': 'encrypt'}
    session = get_cookie_session(**kwargs)
    session['foo'] = 'bar'
    session.save()

    COOKIE_REQUEST['cookie_out'] = ' beaker.session.id='
    session = get_cookie_session(id=session.id, invalidate_corrupt=False, **kwargs)
    assert "foo" not in dict(session)


def test_unrelated_cookie():
    setup_cookie_request()
    kwargs = {'validate_key': 'test_key', 'encrypt_key': 'encrypt'}
    session = get_cookie_session(**kwargs)
    session['foo'] = 'bar'
    session.save()

    COOKIE_REQUEST['cookie_out'] = COOKIE_REQUEST['cookie_out'] + '; some.other=cookie'
    session = get_cookie_session(id=session.id, invalidate_corrupt=False, **kwargs)
    assert "foo" in dict(session)


def test_invalidate_invalid_signed_cookie():
    setup_cookie_request()
    kwargs = {'validate_key': 'test_key', 'encrypt_key': 'encrypt'}
    session = get_cookie_session(**kwargs)
    session['foo'] = 'bar'
    session.save()

    COOKIE_REQUEST['cookie_out'] = (
        COOKIE_REQUEST['cookie_out'][:20] +
        'aaaaa' +
        COOKIE_REQUEST['cookie_out'][25:]
    )

    with pytest.raises(BeakerException):
        get_cookie_session(id=session.id, invalidate_corrupt=False)


def test_invalidate_invalid_signed_cookie_invalidate_corrupt():
    setup_cookie_request()
    kwargs = {'validate_key': 'test_key', 'encrypt_key': 'encrypt'}
    session = get_cookie_session(**kwargs)
    session['foo'] = 'bar'
    session.save()

    COOKIE_REQUEST['cookie_out'] = (
        COOKIE_REQUEST['cookie_out'][:20] +
        'aaaaa' +
        COOKIE_REQUEST['cookie_out'][25:]
    )

    session = get_cookie_session(id=session.id, invalidate_corrupt=True, **kwargs)
    assert "foo" not in dict(session)


def test_load_deleted_from_storage_session__not_loaded():
    req = {'cookie': {'beaker.session.id': 123}}
    session = Session(req, timeout=1)

    session.delete()
    session.save()

    Session(req, timeout=1)


class TestSaveAccessedTime(unittest.TestCase):
    # These tests can't use the memory session type since it seems that loading
    # winds up with references to the underlying storage and makes changes to
    # sessions even though they aren't save()ed.
    def setUp(self):
        # Ignore errors because in most cases the dir won't exist.
        shutil.rmtree('./cache', ignore_errors=True)

    def tearDown(self):
        shutil.rmtree('./cache')

    def test_saves_if_session_written_and_accessed_time_false(self):
        session = get_session(data_dir='./cache', save_accessed_time=False)
        # New sessions are treated a little differently so save the session
        # before getting into the meat of the test.
        session.save()
        session = get_session(data_dir='./cache', save_accessed_time=False,
                              id=session.id)
        last_accessed = session.last_accessed
        session.save(accessed_only=False)
        session = get_session(data_dir='./cache', save_accessed_time=False,
                              id=session.id)
        # If the second save saved, we'll have a new last_accessed time.
        # Python 2.6 doesn't have assertGreater :-(
        assert session.last_accessed > last_accessed, (
            '%r is not greater than %r' %
            (session.last_accessed, last_accessed))

    def test_saves_if_session_not_written_and_accessed_time_true(self):
        session = get_session(data_dir='./cache', save_accessed_time=True)
        # New sessions are treated a little differently so save the session
        # before getting into the meat of the test.
        session.save()
        session = get_session(data_dir='./cache', save_accessed_time=True,
                              id=session.id)
        last_accessed = session.last_accessed
        session.save(accessed_only=True)  # this is the save we're really testing
        session = get_session(data_dir='./cache', save_accessed_time=True,
                              id=session.id)
        # If the second save saved, we'll have a new last_accessed time.
        # Python 2.6 doesn't have assertGreater :-(
        assert session.last_accessed > last_accessed, (
            '%r is not greater than %r' %
            (session.last_accessed, last_accessed))

    def test_doesnt_save_if_session_not_written_and_accessed_time_false(self):
        session = get_session(data_dir='./cache', save_accessed_time=False)
        # New sessions are treated a little differently so save the session
        # before getting into the meat of the test.
        session.save()
        session = get_session(data_dir='./cache', save_accessed_time=False,
                              id=session.id)
        last_accessed = session.last_accessed
        session.save(accessed_only=True)  # this shouldn't actually save
        session = get_session(data_dir='./cache', save_accessed_time=False,
                              id=session.id)
        self.assertEqual(session.last_accessed, last_accessed)


class TestSessionObject(unittest.TestCase):
    def setUp(self):
        # San check that we are in fact using the memory backend...
        assert get_session().namespace_class == MemoryNamespaceManager
        # so we can be sure we're clearing the right state.
        MemoryNamespaceManager.namespaces.clear()

    def test_no_autosave_saves_atime_without_save(self):
        so = SessionObject({}, auto=False)
        so['foo'] = 'bar'
        so.persist()
        session = get_session(id=so.id)
        assert '_accessed_time' in session
        assert 'foo' not in session  # because we didn't save()

    def test_no_autosave_saves_with_save(self):
        so = SessionObject({}, auto=False)
        so['foo'] = 'bar'
        so.save()
        so.persist()
        session = get_session(id=so.id)
        assert '_accessed_time' in session
        assert 'foo' in session

    def test_no_autosave_saves_with_delete(self):
        req = {'cookie': {'beaker.session.id': 123}}

        so = SessionObject(req, auto=False)
        so['foo'] = 'bar'
        so.save()
        so.persist()
        session = get_session(id=so.id)
        assert 'foo' in session

        so2 = SessionObject(req, auto=False)
        so2.delete()
        so2.persist()
        session = get_session(id=so2.id)
        assert 'foo' not in session

    def test_auto_save_saves_without_save(self):
        so = SessionObject({}, auto=True)
        so['foo'] = 'bar'
        # look ma, no save()!
        so.persist()
        session = get_session(id=so.id)
        assert 'foo' in session

    def test_accessed_time_off_saves_atime_when_saving(self):
        so = SessionObject({}, save_accessed_time=False)
        atime = so['_accessed_time']
        so['foo'] = 'bar'
        so.save()
        so.persist()
        session = get_session(id=so.id, save_accessed_time=False)
        assert 'foo' in session
        assert '_accessed_time' in session
        self.assertEqual(session.last_accessed, atime)

    def test_accessed_time_off_doesnt_save_without_save(self):
        req = {'cookie': {'beaker.session.id': 123}}
        so = SessionObject(req, save_accessed_time=False)
        so.persist()  # so we can do a set on a non-new session

        so2 = SessionObject(req, save_accessed_time=False)
        so2['foo'] = 'bar'
        # no save()
        so2.persist()

        session = get_session(id=so.id, save_accessed_time=False)
        assert 'foo' not in session
