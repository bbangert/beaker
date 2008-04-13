__all__  = ["ThreadLocal", "Registry", "WeakValuedRegistry", "SyncDict", "encoded_path", "verify_directory"]

try:
    import thread as _thread
    import threading as _threading
except ImportError:
    import dummy_thread as _thread
    import dummy_threading as _threading

from datetime import datetime, timedelta
import os
import sha
import string
import types
import weakref

try:
    Set = set
except NameError:
    from sets import Set

from beaker.converters import asbool

try:
    from base64 import b64encode, b64decode
except ImportError:
    import binascii

    _translation = [chr(_x) for _x in range(256)]

    # From Python 2.5 base64.py
    def _translate(s, altchars):
        translation = _translation[:]
        for k, v in altchars.items():
            translation[ord(k)] = v
        return s.translate(''.join(translation))

    def b64encode(s, altchars=None):
        """Encode a string using Base64.

        s is the string to encode.  Optional altchars must be a string of at least
        length 2 (additional characters are ignored) which specifies an
        alternative alphabet for the '+' and '/' characters.  This allows an
        application to e.g. generate url or filesystem safe Base64 strings.

        The encoded string is returned.
        """
        # Strip off the trailing newline
        encoded = binascii.b2a_base64(s)[:-1]
        if altchars is not None:
            return _translate(encoded, {'+': altchars[0], '/': altchars[1]})
        return encoded

    def b64decode(s, altchars=None):
        """Decode a Base64 encoded string.

        s is the string to decode.  Optional altchars must be a string of at least
        length 2 (additional characters are ignored) which specifies the
        alternative alphabet used instead of the '+' and '/' characters.

        The decoded string is returned.  A TypeError is raised if s were
        incorrectly padded or if there are non-alphabet characters present in the
        string.
        """
        if altchars is not None:
            s = _translate(s, {altchars[0]: '+', altchars[1]: '/'})
        try:
            return binascii.a2b_base64(s)
        except binascii.Error, msg:
            # Transform this exception for consistency
            raise TypeError(msg)


def verify_directory(dir):
    """verifies and creates a directory.  tries to
    ignore collisions with other threads and processes."""

    tries = 0
    while not os.access(dir, os.F_OK):
        try:
            tries += 1
            os.makedirs(dir, 0750)
        except:
            if tries > 5:
                raise

    
class ThreadLocal(object):
    """stores a value on a per-thread basis"""
    def __init__(self, value = None, default = None, creator = None):
        self.dict = {}
        self.default = default
        self.creator = creator
        if value:
            self.put(value)

    def __call__(self, *arg):
        if len(arg):
            self.put(arg[0])
        else:
            return self.get()

    def __str__(self):
        return str(self.get())
    
    def assign(self, value):
        self.dict[_thread.get_ident()] = value
    
    def put(self, value):
        self.assign(value)
    
    def exists(self):
        return self.dict.has_key(_thread.get_ident())
            
    def get(self, *args, **params):
        if not self.dict.has_key(_thread.get_ident()):
            if self.default is not None: 
                self.put(self.default)
            elif self.creator is not None: 
                self.put(self.creator(*args, **params))
        
        return self.dict[_thread.get_ident()]
            
    def remove(self):
        del self.dict[_thread.get_ident()]
        
    
class SyncDict(object):
    """
    an efficient/threadsafe singleton map algorithm, a.k.a.
    "get a value based on this key, and create if not found or not valid" paradigm:
    
        exists && isvalid ? get : create

    works with weakref dictionaries and the LRUCache to handle items asynchronously 
    disappearing from the dictionary.  

    use python 2.3.3 or greater !  a major bug was just fixed in Nov. 2003 that
    was driving me nuts with garbage collection/weakrefs in this section.
    """
    
    def __init__(self, mutex, dictionary):
        self.mutex = mutex
        self.dict = dictionary
        
    def clear(self):
        self.dict.clear()
        
    def get(self, key, createfunc, isvalidfunc = None):
        """regular get method.  returns the object asynchronously, if present
        and also passes the optional isvalidfunc,
        else defers to the synchronous get method which will create it."""
        try:
            if self.has_key(key):
                return self._get_obj(key, createfunc, isvalidfunc)
            else:
                return self.sync_get(key, createfunc, isvalidfunc)
        except KeyError:
            return self.sync_get(key, createfunc, isvalidfunc)

    def sync_get(self, key, createfunc, isvalidfunc = None):
        self.mutex.acquire()
        try:
            try:
                if self.has_key(key):
                    return self._get_obj(key, createfunc, isvalidfunc, create = True)
                else:
                    return self._create(key, createfunc)
            except KeyError:
                return self._create(key, createfunc)
        finally:
            self.mutex.release()

    def _get_obj(self, key, createfunc, isvalidfunc, create = False):
        obj = self[key]
        if isvalidfunc is not None and not isvalidfunc(obj):
            if create:
                return self._create(key, createfunc)
            else:
                return self.sync_get(key, createfunc, isvalidfunc)
        else:
            return obj
    
    def _create(self, key, createfunc):
        obj = createfunc()
        self[key] = obj
        return obj

    def has_key(self, key):
        return self.dict.has_key(key)
    def __contains__(self, key):
        return self.dict.__contains__(key)
    def __getitem__(self, key):
        return self.dict.__getitem__(key)
    def __setitem__(self, key, value):
        self.dict.__setitem__(key, value)
    def __delitem__(self, key):
        return self.dict.__delitem__(key)
    

class Registry(SyncDict):
    """a registry object."""
    def __init__(self):
        SyncDict.__init__(self, _threading.Lock(), {})

class WeakValuedRegistry(SyncDict):
    """a registry that stores objects only as long as someone has a reference to them."""
    def __init__(self):
        # weakrefs apparently can trigger the __del__ method of other
        # unreferenced objects, when you create a new reference.  this can occur
        # when you place new items into the WeakValueDictionary.  if that __del__
        # method happens to want to access this same registry, well, then you need
        # the RLock instead of a regular lock, since at the point of dictionary
        # insertion, we are already inside the lock.
        SyncDict.__init__(self, _threading.RLock(), weakref.WeakValueDictionary())

            
def encoded_path(root, identifiers, extension = ".enc", depth = 3, digest = True):
    """generate a unique file-accessible path from the given list of identifiers
    starting at the given root directory."""
    ident = string.join(identifiers, "_")

    if digest:
        ident = sha.new(ident).hexdigest()
    
    ident = os.path.basename(ident)

    tokens = []
    for d in range(1, depth):
        tokens.append(ident[0:d])
    
    dir = os.path.join(root, *tokens)
    verify_directory(dir)
    
    return os.path.join(dir, ident + extension)

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
        ('data_dir', (str, types.NoneType), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str,), "lock_dir must be a string referring to a directory."),
        ('type', (str, types.NoneType), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta), "Cookie expires was not a boolean, datetime, or timedelta instance."),
        ('cookie_domain', (str, types.NoneType), "Cookie domain must be a string."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str, types.NoneType), "Session secret must be a string."),
        ('validate_key', (str, types.NoneType), "Session encrypt_key must be a string."),
        ('encrypt_key', (str, types.NoneType), "Session validate_key must be a string."),
        ('secure', (bool, types.NoneType), "Session secure must be a boolean."),
        ('timeout', (int, types.NoneType), "Session timeout must be an integer."),
    ]
    return verify_rules(params, rules)

def coerce_cache_params(params):
    rules = [
        ('data_dir', (str, types.NoneType), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str,), "lock_dir must be a string referring to a directory."),
        ('type', (str,), "Session type must be a string."),
    ]
    return verify_rules(params, rules)
