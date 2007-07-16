import Cookie
from datetime import datetime, timedelta
import hmac
import md5
import os
import random
import re
import sys
import time
import UserDict
import warnings

try:
    from paste.registry import StackedObjectProxy
    beaker_session = StackedObjectProxy(name="Beaker Session")
except:
    beaker_session = None

from beaker.container import namespace_registry
from beaker.util import coerce_session_params

__all__ = ['SignedCookie', 'Session']

class SignedCookie(Cookie.BaseCookie):
    "extends python cookie to give digital signature support"
    def __init__(self, secret, input=None):
        self.secret = secret
        Cookie.BaseCookie.__init__(self, input)
    
    def value_decode(self, val):
        sig = val[0:32]
        value = val[32:]
    
        if hmac.new(self.secret, value).hexdigest() != sig:
            return None, val
        
        return val[32:], val
    
    def value_encode(self, val):
        return val, ("%s%s" % (hmac.new(self.secret, val).hexdigest(), val))

                
class Session(UserDict.DictMixin):
    "session object that uses container package for storage"

    def __init__(self, request, id=None, invalidate_corrupt=False, 
                 use_cookies=True, type=None, data_dir=None, 
                 key='beaker.session.id', timeout=None, cookie_expires=True,
                 secret=None, log_file=None, namespace_class=None, **kwargs):
        if type is None:
            if data_dir is None:
                self.type = 'memory'
            else:
                self.type = 'file'
        else:
            self.type = type

        if namespace_class is None:
            self.namespace_class = namespace_registry(self.type)
        else:
            self.namespace_class = namespace_class

        self.kwargs = kwargs
        
        self.request = request
        self.data_dir = data_dir
        self.key = key
        self.timeout = timeout
        self.use_cookies = use_cookies
        self.cookie_expires = cookie_expires
        self.log_file = log_file
        self.was_invalidated = False
        self.secret = secret
        
        self.id = id
            
        if self.use_cookies:
            try:
                cookieheader = request['cookie']
            except KeyError:
                cookieheader = ''
                
            if secret is not None:
                try:
                    self.cookie = SignedCookie(secret, input = cookieheader)
                except Cookie.CookieError:
                    self.cookie = SignedCookie(secret, input = None)
            else:
                self.cookie = Cookie.SimpleCookie(input = cookieheader)

            if self.id is None and self.cookie.has_key(self.key):
                self.id = self.cookie[self.key].value
        
        if self.id is None:
            self._create_id()
        else:
            self.is_new = False
        
        if not self.is_new:
            try:
                self.load()
            except:
                if invalidate_corrupt:
                    self.invalidate()
                else:
                    raise
        else:
            self.dict = {}
        
    def _create_id(self):
        self.id = md5.new(
            md5.new("%f%s%f%d" % (time.time(), id({}), random.random(), os.getpid()) ).hexdigest(), 
        ).hexdigest()
        self.is_new = True
        if self.use_cookies:
            self.cookie[self.key] = self.id
            self.cookie[self.key]['path'] = '/'
            if self.cookie_expires is not True:
                if self.cookie_expires is False:
                    expires = datetime.fromtimestamp( 0x7FFFFFFF )
                elif isinstance(self.cookie_expires, timedelta):
                    expires = datetime.today() + self.cookie_expires
                elif isinstance(self.cookie_expires, datetime):
                    expires = self.cookie_expires
                else:
                    raise ValueError("Invalid argument for cookie_expires: %s"
                                     % repr(self.cookie_expires))
                self.cookie[self.key]['expires'] = \
                    expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT" )
            self.request['cookie_out'] = self.cookie[self.key].output(header='')
            self.request['set_cookie'] = False
    
    created = property(lambda self: self.dict['_creation_time'])

    def delete(self):
        """deletes the persistent storage for this session, but remains valid. """
        self.namespace.acquire_write_lock()
        try:
            for k in self.namespace.keys():
                if not re.match(r'_creation_time|_accessed_time', k):
                    del self.namespace[k]
                    
            self.namespace['_accessed_time'] = time.time()
        finally:
            self.namespace.release_write_lock()
    
    def __getitem__(self, key):
        return self.dict.__getitem__(key)
    def __setitem__(self, key, value):
        self.dict.__setitem__(key, value)
    def __delitem__(self, key):
        del self.dict[key]
    def keys(self):
        return self.dict.keys()
    def __contains__(self, key):
        return self.dict.has_key(key)
    def has_key(self, key):
        return self.dict.has_key(key)
    def __iter__(self):
        return iter(self.dict.keys())
    def iteritems(self):
        return self.dict.iteritems()
        
    def invalidate(self):
        "invalidates this session, creates a new session id, returns to the is_new state"
        namespace = self.namespace
        namespace.acquire_write_lock()
        try:
            namespace.remove()
        finally:
            namespace.release_write_lock()
            
        self.was_invalidated = True
        self._create_id()
        self.load()

                    
    def load(self):
        "loads the data from this session from persistent storage"

        self.namespace = self.namespace_class(self.id, data_dir=self.data_dir,
                                              digest_filenames=False, **self.kwargs)
        
        namespace = self.namespace
        self.request['set_cookie'] = True
        
        namespace.acquire_write_lock()
        try:
            self.debug("session loading keys")
            self.dict = {}
            now = time.time()
            
            if not namespace.has_key('_creation_time'):
                namespace['_creation_time'] = now
                self.is_new = True
            try:
                self.accessed = namespace['_accessed_time']
                namespace['_accessed_time'] = now
            except KeyError:
                namespace['_accessed_time'] = self.accessed = now
    
            if self.timeout is not None and now - self.accessed > self.timeout:
                self.invalidate()
            else:
                for k in namespace.keys():
                    self.dict[k] = namespace[k]
        
        finally:
            namespace.release_write_lock()
    
    def save(self):
        "saves the data for this session to persistent storage"
        if not hasattr(self, 'namespace'):
            curdict = self.dict
            self.load()
            self.dict = curdict
        
        self.namespace.acquire_write_lock()
        try:
            self.debug("session saving keys")
            todel = []
            for k in self.namespace.keys():
                if not self.dict.has_key(k):
                    todel.append(k)
            
            for k in todel:
                del self.namespace[k]
                    
            for k in self.dict.keys():
                self.namespace[k] = self.dict[k]
                
            self.namespace['_accessed_time'] = time.time()
        finally:
            self.namespace.release_write_lock()
        if self.is_new:
            self.request['set_cookie'] = True
    
    def lock(self):
        """locks this session against other processes/threads.  this is 
        automatic when load/save is called.
        
        ***use with caution*** and always with a corresponding 'unlock'
        inside a "finally:" block,
        as a stray lock typically cannot be unlocked
        without shutting down the whole application.
        """
        self.namespace.acquire_write_lock()
    

    def unlock(self):
        """unlocks this session against other processes/threads.  this is 
        automatic when load/save is called.

        ***use with caution*** and always within a "finally:" block,
        as a stray lock typically cannot be unlocked
        without shutting down the whole application.
        
        """
        self.namespace.release_write_lock()
    

    def debug(self, message):
        if self.log_file is not None:
            self.log_file.write(message)

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
    
    def get_by_id(self, id):
        params = self.__dict__['_params']
        session = Session({}, use_cookies=False, id=id, **params)
        if session.is_new:
            session.namespace.remove()
            return None
        return session


class SessionMiddleware(object):
    deprecated = True
    session = beaker_session
    
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
        if self.deprecated:
            warnings.warn('SessionMiddleware is moving to beaker.middleware in '
              '0.8', DeprecationWarning, 2)
        
        config = config or {}
        
        # Load up the default params
        self.options = dict(invalidate_corrupt=True, type=None, 
                           data_dir=None, key='beaker.session.id', 
                           timeout=None, secret=None, log_file=None)

        # Pull out any config args meant for beaker session. if there are any
        for dct in [config, kwargs]:
            for key, val in dct.iteritems():
                if key.startswith('beaker.session.'):
                    self.options[key[15:]] = val
                if key.startswith('session.'):
                    self.options[key[8:]] = val
                if key.startswith('session_'):
                    warnings.warn('Session options should start with session. '
                                  'instead of session_.', DeprecationWarning, 2)
                    self.options[key[8:]] = val
        
        # Coerce and validate session params
        coerce_session_params(self.options)
        
        # Assume all keys are intended for cache if none are prefixed with 'cache.'
        if not self.options and config:
            self.options = config
        
        self.options.update(kwargs)
        self.wrap_app = wrap_app
        self.environ_key = environ_key
        
    def __call__(self, environ, start_response):
        session = SessionObject(environ, **self.options)
        if environ.get('paste.registry'):
            environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session
        
        def session_start_response(status, headers, exc_info = None):
            if session.__dict__['_sess'] is not None:
                if session.__dict__['_headers']['set_cookie']:
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
    
    def _get_session(self):
        return Session({}, use_cookies=False, **self.options)
