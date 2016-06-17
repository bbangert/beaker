# -*- coding: utf-8 -*-
from beaker._compat import u_, pickle

import shutil
import sys
import time
import unittest
import warnings

from nose import SkipTest

from beaker.container import MemoryNamespaceManager
from beaker.crypto import has_aes
from beaker.exceptions import BeakerException
from beaker.session import Session, SessionObject
from beaker.util import assert_raises


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session({}, **options)


def test_save_load():
    """Test if the data is actually persistent across requests"""
    session = get_session()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = get_session(id=session.id)
    assert u_('Suomi') in session
    assert u_('Great Britain') in session
    assert u_('Deutchland') in session

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')


def test_save_load_encryption():
    """Test if the data is actually persistent across requests"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = get_session(id=session.id, encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    assert u_('Suomi') in session
    assert u_('Great Britain') in session
    assert u_('Deutchland') in session

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')


def test_decryption_failure():
    """Test if the data fails without the right keys"""
    if not has_aes:
        raise SkipTest()
    session = get_session(encrypt_key='666a19cf7f61c64c',
                          validate_key='hoobermas')
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = get_session(id=session.id, encrypt_key='asfdasdfadsfsadf',
                          validate_key='hoobermas', invalidate_corrupt=True)
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session


def test_delete():
    """Test :meth:`Session.delete`"""
    session = get_session()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.delete()

    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


def test_revert():
    """Test :meth:`Session.revert`"""
    session = get_session()
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = get_session(id=session.id)
    del session[u_('Suomi')]
    session[u_('Great Britain')] = u_('Lewis Hamilton')
    session[u_('Deutchland')] = u_('Michael Schumacher')
    session[u_('España')] = u_('Fernando Alonso')
    session.revert()

    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')
    assert u_('España') not in session


def test_invalidate():
    """Test :meth:`Session.invalidate`"""
    session = get_session()
    id = session.id
    created = session.created
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.invalidate()

    assert session.id != id
    assert session.created != created
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


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


def test_timeout():
    """Test if the session times out properly"""
    session = get_session(timeout=2)
    id = session.id
    created = session.created
    session[u_('Suomi')] = u_('Kimi Räikkönen')
    session[u_('Great Britain')] = u_('Jenson Button')
    session[u_('Deutchland')] = u_('Sebastian Vettel')
    session.save()

    session = get_session(id=session.id, timeout=2)
    assert session.id == id
    assert session.created == created
    assert session[u_('Suomi')] == u_('Kimi Räikkönen')
    assert session[u_('Great Britain')] == u_('Jenson Button')
    assert session[u_('Deutchland')] == u_('Sebastian Vettel')

    time.sleep(2)
    session = get_session(id=session.id, timeout=2)
    assert session.id != id
    assert session.created != created
    assert u_('Suomi') not in session
    assert u_('Great Britain') not in session
    assert u_('Deutchland') not in session


def test_timeout_requires_accessed_time():
    """Test that it doesn't allow setting save_accessed_time to False with
    timeout enabled
    """
    get_session(timeout=None, save_accessed_time=True)  # is ok
    get_session(timeout=None, save_accessed_time=False)  # is ok
    assert_raises(BeakerException,
                  get_session,
                  timeout=2,
                  save_accessed_time=False)


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

    assert_raises(
        pickle.UnpicklingError,
        get_session,
        use_cookies=False, type='file',
                data_dir='./cache', id=session.id
    )

    session = get_session(use_cookies=False, type='file',
                            invalidate_corrupt=True,
                            data_dir='./cache', id=session.id)
    assert "foo" not in dict(session)


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
        self.assertGreater(session.last_accessed, last_accessed)


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
        self.assertGreater(session.last_accessed, last_accessed)


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
