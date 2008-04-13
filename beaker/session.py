import cPickle
import Cookie
import hmac
import md5
import os
import random
import sha
import sys
import time
import UserDict
from datetime import datetime, timedelta

# Determine if strong crypto is available
crypto_ok = False

# Check for pycryptopp encryption for AES
try:
    from pycryptopp.cipher import aes
    from beaker.crypto import generateCryptoKeys
    crypto_ok = True
except:
    pass

from beaker.container import namespace_registry
from beaker.exceptions import BeakerException
from beaker.util import b64decode, b64encode, coerce_session_params

__all__ = ['SignedCookie', 'Session']

class SignedCookie(Cookie.BaseCookie):
    "extends python cookie to give digital signature support"
    def __init__(self, secret, input=None):
        self.secret = secret
        Cookie.BaseCookie.__init__(self, input)
    
    def value_decode(self, val):
        val = val.strip('"')
        sig = hmac.new(self.secret, val[40:], sha).hexdigest()
        if sig != val[:40]:
            return None, val
        else:
            return val[40:], val
    
    def value_encode(self, val):
        sig = hmac.new(self.secret, val, sha).hexdigest()
        return str(val), ("%s%s" % (sig, val))


class Session(UserDict.DictMixin):
    "session object that uses container package for storage"

    def __init__(self, request, id=None, invalidate_corrupt=False, 
                 use_cookies=True, type=None, data_dir=None, 
                 key='beaker.session.id', timeout=None, cookie_expires=True,
                 cookie_domain=None, secret=None, secure=False, log_file=None, 
                 namespace_class=None, **kwargs):
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
        self.cookie_domain = cookie_domain
        self.log_file = log_file
        self.was_invalidated = False
        self.secret = secret
        self.secure = secure
        
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
        if hasattr(os, 'getpid'):
            pid = os.getpid()
        else:
            pid = ''
        
        self.id = md5.new(
            md5.new("%f%s%f%s" % (time.time(), id({}), random.random(), pid) ).hexdigest(), 
        ).hexdigest()
        self.is_new = True
        if self.use_cookies:
            self.cookie[self.key] = self.id
            if self.cookie_domain:
                self.cookie[self.key]['domain'] = self.cookie_domain
            if self.secure:
                self.cookie[self.key]['secure'] = True
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
            self.namespace.remove()
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
                
            self.namespace['_accessed_time'] = self.dict['_accessed_time'] \
                = time.time()
            self.namespace['_creation_time'] = self.dict['_creation_time'] \
                = time.time()
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


class CookieSession(Session):
    """Pure cookie-based session
    
    Options recognized when using cookie-based sessions are slightly
    more restricted than general sessions.
    
    ``key``
        The name the cookie should be set to.
    ``timeout``
        How long session data is considered valid. This is used 
        regardless of the cookie being present or not to determine
        whether session data is still valid.
    ``encrypt_key``
        The key to use for the session encryption, if not provided the session
        will not be encrypted.
    ``validate_key``
        The key used to sign the encrypted session
    ``cookie_domain``
        Domain to use for the cookie.
    ``secure``
        Whether or not the cookie should only be sent over SSL.
    
    """
    def __init__(self, request, key='beaker.session.id', timeout=None,
                 cookie_expires=True, cookie_domain=None, encrypt_key=None,
                 validate_key=None, secure=False, **kwargs):
        if not crypto_ok and encrypt_key:
            raise BeakerException("pycryptopp is not installed, can't use "
                                  "encrypted cookie-only Session.")
        
        self.request = request
        self.key = key
        self.timeout = timeout
        self.cookie_expires = cookie_expires
        self.cookie_domain = cookie_domain
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.request['set_cookie'] = False
        self.secure = secure
        
        try:
            cookieheader = request['cookie']
        except KeyError:
            cookieheader = ''
        
        if validate_key is None:
            raise BeakerException("No validate_key specified for Cookie only Session.")
        
        try:
            self.cookie = SignedCookie(validate_key, input=cookieheader)
        except Cookie.CookieError:
            self.cookie = SignedCookie(validate_key, input=None)
        
        self.dict = {}
        self.dict['_id'] = self._make_id()
        self.is_new = True
        
        # If we have a cookie, load it
        if self.key in self.cookie and self.cookie[self.key].value is not None:
            self.is_new = False
            try:
                self.dict = self._decrypt_data()
            except:
                self.dict = {}
            if self.timeout is not None and time.time() - self.dict['_accessed_time'] > self.timeout:
                self.dict = {}
            self._create_cookie()
    
    created = property(lambda self: self.dict['_creation_time'])
    id = property(lambda self: self.dict['_id'])
    
    def _encrypt_data(self):
        """Cerealize, encipher, and base64 the session dict"""
        if self.encrypt_key:
            nonce = b64encode(os.urandom(40))[:8]
            encrypt_key = generateCryptoKeys(self.encrypt_key, self.validate_key + nonce, 1)
            ctrcipher = aes.AES(encrypt_key)
            data = cPickle.dumps(self.dict, protocol=2)
            return nonce + b64encode(ctrcipher.process(data))
        else:
            data = cPickle.dumps(self.dict, protocol=2)
            return b64encode(data)
    
    def _decrypt_data(self):
        """Bas64, decipher, then un-cerealize the data for the session dict"""
        if self.encrypt_key:
            nonce = self.cookie[self.key].value[:8]
            encrypt_key = generateCryptoKeys(self.encrypt_key, self.validate_key + nonce, 1)
            ctrcipher = aes.AES(encrypt_key)
            payload = b64decode(self.cookie[self.key].value[8:])
            data = ctrcipher.process(payload)
            return cPickle.loads(data)
        else:
            data = b64decode(self.cookie[self.key].value)
            return cPickle.loads(data)
    
    def _make_id(self):
        return md5.new(md5.new(
            "%f%s%f%d" % (time.time(), id({}), random.random(), os.getpid())
            ).hexdigest()
        ).hexdigest()
    
    def save(self):
        "saves the data for this session to persistent storage"
        self._create_cookie()
    
    def _create_cookie(self):
        if '_creation_time' not in self.dict:
            self.dict['_creation_time'] = time.time()
        if '_id' not in self.dict:
            self.dict['_id'] = self._make_id()
        self.dict['_accessed_time'] = time.time()
        val = self._encrypt_data()
        if len(val) > 4064:
            raise BeakerException("Cookie value is too long to store")
        
        self.cookie[self.key] = val
        if self.cookie_domain:
            self.cookie[self.key]['domain'] = self.cookie_domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        
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
        self.request['set_cookie'] = True
    
    def delete(self):
        # Clear out the cookie contents, best we can do
        self.dict = {}
        self._create_cookie()
    
    # Alias invalidate to delete
    invalidate = delete


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
            if params.get('type') == 'cookie':
                self.__dict__['_sess'] = CookieSession(req, **params)
            else:
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
