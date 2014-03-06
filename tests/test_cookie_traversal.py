# -*- coding: utf-8 -*-
import sys
import time
import warnings
import os

from beaker.session import Session


def get_session(**kwargs):
    """A shortcut for creating :class:`Session` instance"""
    options = {}
    options.update(**kwargs)
    return Session({}, **options)

def test_file_traversal_cookie():
    session = get_session(id='..traversed', type='file', data_dir='.')
    session[u'traversal'] = u'True'
    session.save()
    assert not os.path.exists('./..traversed.cache') 


def test_save_load():
    """Test if the data is actually persistent across requests"""
    session = get_session(type='file', data_dir='.')
    session[u'Suomi'] = u'Kimi Räikkönen'
    session[u'Great Britain'] = u'Jenson Button'
    session[u'Deutchland'] = u'Sebastian Vettel'
    session.save()

    session = get_session(id=session.id, type='file', data_dir='.')
    assert u'Suomi' in session
    assert u'Great Britain' in session
    assert u'Deutchland' in session

    assert session[u'Suomi'] == u'Kimi Räikkönen'
    assert session[u'Great Britain'] == u'Jenson Button'
    assert session[u'Deutchland'] == u'Sebastian Vettel'

test_save_load()
test_file_traversal_cookie()

