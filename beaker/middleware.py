import sys

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    beaker_cache = None
    beaker_session = None

from beaker.cache import CacheMiddleware as DeprecatedCacheMiddleware
from beaker.converters import asbool
from beaker.session import SessionMiddleware as DeprecatedSessionMiddleware

class CacheMiddleware(DeprecatedCacheMiddleware):
    deprecated = False
    cache = beaker_cache

class SessionMiddleware(DeprecatedSessionMiddleware):
    deprecated = False
    session = beaker_session

def session_filter_factory(global_conf, **kwargs):
    def filter(app):
        return SessionMiddleware(app, global_conf, **kwargs)
    return filter

def session_filter_app_factory(app, global_conf, **kwargs):
    return SessionMiddleware(app, global_conf, **kwargs)
