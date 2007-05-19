import sys

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    pass

from beaker.converters import asbool

import warnings
warnings.simplefilter('ignore', DeprecationWarning)
from beaker.cache import CacheMiddleware
from beaker.session import SessionMiddleware
warnings.simplefilter('default', DeprecationWarning)

def session_filter_factory(global_conf, **kwargs):
    def filter(app):
        return SessionMiddleware(app, global_conf, **kwargs)
    return filter

def session_filter_app_factory(app, global_conf, **kwargs):
    return SessionMiddleware(app, global_conf, **kwargs)
