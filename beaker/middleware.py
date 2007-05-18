from datetime import datetime, timedelta
import sys

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    pass

from beaker.cache import CacheManager
from beaker.converters import asbool
from beaker.session import Session

class SessionObject(object):
    """Session proxy/lazy creator
    
    This object proxies access to the actual session object, so that in the
    case that the session hasn't been used before, it will be setup. This
    avoid creating and loading the session from persistent storage unless
    its actually used during the request.
    
    """
    def __init__(self, environ, **params):
        self.__dict__['_params'] = params
        self.__dict__['_environ'] = environ
        self.__dict__['_sess'] = None
        self.__dict__['_headers'] = []
    
    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out':None}
            req['cookie'] = environ.get('HTTP_COOKIE')
            self.__dict__['_sess'] = Session(req, use_cookies=True, **params)
        return self.__dict__['_sess']
    
    def __getattr__(self, attr):
        return getattr(self._session(), attr)
    
    def __setattr__(self, attr, value):
        setattr(self._session(), attr, value)
    
    def __delattr__(self, name):
        self._session().__delattr__(name)
    
    def __getitem__(self, key):
        return self._session()[key]
    
    def __setitem__(self, key, value):
        self._session()[key] = value
    
    def __delitem__(self, key):
        self._session().__delitem__(key)
    
    def __repr__(self):
        return self._session().__repr__()
    
    def __iter__(self):
        """Only works for proxying to a dict"""
        return iter(self._session().keys())
    
    def __contains__(self, key):
        return self._session().has_key(key)

class SessionMiddleware(object):
    def __init__(self, wrap_app, config=None, environ_key='beaker.session', **kwargs):
        """Initialize the Session Middleware
        
        The Session middleware will make a lazy session instance available 
        every request under the ``environ['beaker.cache']`` key by default. The location in
        environ can be changed by setting ``environ_key``.
        
        ``config``
            dict  All settings should be prefixed by 'cache.'. This method of
            passing variables is intended for Paste and other setups that
            accumulate multiple component settings in a single dictionary. If
            config contains *no cache. prefixed args*, then *all* of the config
            options will be used to intialize the Cache objects.
        
        ``environ_key``
            Location where the Session instance will keyed in the WSGI environ
        
        ``**kwargs``
            All keyword arguments are assumed to be cache settings and will
            override any settings found in ``config``
        """
        config = config or {}
        
        # Load up the default params
        self.options= dict(invalidate_corrupt=False, type=None, 
                           data_dir=None, key='beaker.session.id', 
                           timeout=None, secret=None, log_file=None)

        # Pull out any config args meant for beaker session. if there are any
        for key, val in config.iteritems():
            if key.startswith('beaker.session.'):
                self.options[key[15:]] = val
        
        # Coerce and validate session params
        coerce_session_params(config)
        
        # Update the params with the ones passed in
        self.options.update(config)
        self.options.update(kwargs)
        
        self.wrap_app = wrap_app
        self.environ_key = environ_key
        
    def __call__(self, environ, start_response):
        session = SessionObject(environ, **self.options)
        if environ.get('paste.registry'):
            environ['paste.registry'].register(beaker_session, session)
        environ[self.environ_key] = session
        
        def session_start_response(status, headers, exc_info = None):
            if session.__dict__['_sess'] is not None:
                cookie = session.__dict__['_headers']['cookie_out']
                if cookie:
                    headers.append(('Set-cookie', cookie))
            return start_response(status, headers, exc_info)
        try:
            response = self.wrap_app(environ, session_start_response)
        except:
            ty, val = sys.exc_info()[:2]
            if isinstance(ty, str):
                raise ty, val, sys.exc_info()[2]
            if ty.__name__ == 'HTTPFound' and \
                    session.__dict__['_sess'] is not None:
                cookie = session.__dict__['_headers']['cookie_out']
                if cookie:
                    val.headers.append(('Set-cookie', cookie))
            raise ty, val, sys.exc_info()[2]
        else:
            return response

class CacheMiddleware(object):
    def __init__(self, app, config=None, environ_key='beaker.cache', **kwargs):
        """Initialize the Cache Middleware
        
        The Cache middleware will make a Cache instance available every request
        under the ``environ['beaker.cache']`` key by default. The location in
        environ can be changed by setting ``environ_key``.
        
        ``config``
            dict  All settings should be prefixed by 'cache.'. This method of
            passing variables is intended for Paste and other setups that
            accumulate multiple component settings in a single dictionary. If
            config contains *no cache. prefixed args*, then *all* of the config
            options will be used to intialize the Cache objects.
        
        ``environ_key``
            Location where the Cache instance will keyed in the WSGI environ
        
        ``**kwargs``
            All keyword arguments are assumed to be cache settings and will
            override any settings found in ``config``
        """
        self.app = app
        config = config or {}

        # Load up the default params
        self.options= dict(type='memory', data_dir=None, timeout=None, 
                           log_file=None)
        
        # Pull out any config args starting with beaker cache. if there are any
        for key, val in config.iteritems():
            if key.startswith('beaker.cache.'):
                self.options[key[13:]] = val
        
        # Coerce and validate cache params
        coerce_cache_params(self.options)
        
        # Assume all keys are intended for cache if none are prefixed with 'cache.'
        if not self.options and not config:
            self.options = config
        
        self.options.update(kwargs)
        self.cache_manager = CacheManager(**self.options)
        self.environ_key = environ_key
    
    def __call__(self, environ, start_response):
        if environ.get('paste.registry'):
            environ['paste.registry'].register(beaker_cache, self.cache_manager)
        environ[self.environ_key] = self.cache_manager
        return self.app(environ, start_response)

def verify_options(opt, types, error):
    if not isinstance(opt, types):
        if not isinstance(types, tuple):
            types = (types,)
        coerced = False
        for typ in types:
            try:
                if typ == bool:
                    typ = asbool
                opt = typ(opt)
                coerced = True
            except:
                pass
            if coerced:
                break
        if not coerced:
            raise Exception(error)
    return opt

def verify_rules(params, ruleset):
    for key, types, message in ruleset:
        if key in params:
            params[key] = verify_options(params[key], types, message)
    return params

def coerce_session_params(params):
    rules = [
        ('data_dir', (str,), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str,), "lock_dir must be a string referring to a directory."),
        ('type', (str,), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta), "Cookie expires was not a boolean, datetime, or timedelta instance."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str,), "Session secret must be a string."),
        ('timeout', (int,), "Session timeout must be an integer."),
    ]
    return verify_rules(params, rules)

def coerce_cache_params(params):
    rules = [
        ('data_dir', (str,), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str,), "lock_dir must be a string referring to a directory."),
        ('type', (str,), "Session type must be a string."),
    ]
    return verify_rules(params, rules)

def session_filter_factory(global_conf, **kwargs):
    def filter(app):
        return SessionMiddleware(app, global_conf, **kwargs)
    return filter

def session_filter_app_factory(app, global_conf, **kwargs):
    return SessionMiddleware(app, global_conf, **kwargs)

