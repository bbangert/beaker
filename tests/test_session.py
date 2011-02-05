# -*- coding: utf-8 -*-
import time

import webob
from beaker.session import Session


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session(webob.Request.blank('/').environ, **options)


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
