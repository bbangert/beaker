"""Beaker utilities"""
import uuid
import socket

import binascii

from ._compat import dictkeyslist, im_class, im_func, pickle, func_signature, \
    default_im_func

try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading

from datetime import datetime, timedelta
import os
import re
import string
import types
import weakref
import warnings
import sys
import inspect
import json
import zlib

from beaker.converters import asbool
from beaker import exceptions
from threading import local as _tlocal

DEFAULT_CACHE_KEY_LENGTH = 250

__all__ = ["ThreadLocal", "WeakValuedRegistry", "SyncDict", "encoded_path",
           "verify_directory",
           "serialize", "deserialize"]


def function_named(fn, name):
    """Return a function with a given __name__.

    Will assign to __name__ and return the original function if possible on
    the Python implementation, otherwise a new function will be constructed.

    """
    fn.__name__ = name
    return fn


def skip_if(predicate, reason=None):
    """Skip a test if predicate is true."""
    reason = reason or predicate.__name__

    from unittest import SkipTest

    def decorate(fn):
        fn_name = fn.__name__

        def maybe(*args, **kw):
            if predicate():
                msg = "'%s' skipped: %s" % (
                    fn_name, reason)
                raise SkipTest(msg)
            else:
                return fn(*args, **kw)
        return function_named(maybe, fn_name)
    return decorate


def assert_raises(except_cls, callable_, *args, **kw):
    """Assert the given exception is raised by the given function + arguments."""

    try:
        callable_(*args, **kw)
        success = False
    except except_cls:
        success = True

    # assert outside the block so it works for AssertionError too !
    assert success, "Callable did not raise an exception"


def verify_directory(dir):
    """verifies and creates a directory.  tries to
    ignore collisions with other threads and processes."""

    tries = 0
    while not os.access(dir, os.F_OK):
        try:
            tries += 1
            os.makedirs(dir)
        except:
            if tries > 5:
                raise


def has_self_arg(func):
    """Return True if the given function has a 'self' argument."""
    args = list(func_signature(func).parameters)
    if args and args[0] in ('self', 'cls'):
        return True
    else:
        return False


def warn(msg, stacklevel=3):
    """Issue a warning."""
    if isinstance(msg, str):
        warnings.warn(msg, exceptions.BeakerWarning, stacklevel=stacklevel)
    else:
        warnings.warn(msg, stacklevel=stacklevel)


def deprecated(message):
    def wrapper(fn):
        def deprecated_method(*args, **kargs):
            warnings.warn(message, DeprecationWarning, 2)
            return fn(*args, **kargs)
        # TODO: use decorator ?  functools.wrapper ?
        deprecated_method.__name__ = fn.__name__
        deprecated_method.__doc__ = "%s\n\n%s" % (message, fn.__doc__)
        return deprecated_method
    return wrapper


class ThreadLocal(object):
    """stores a value on a per-thread basis"""

    __slots__ = '_tlocal'

    def __init__(self):
        self._tlocal = _tlocal()

    def put(self, value):
        self._tlocal.value = value

    def has(self):
        return hasattr(self._tlocal, 'value')

    def get(self, default=None):
        return getattr(self._tlocal, 'value', default)

    def remove(self):
        del self._tlocal.value


class SyncDict(object):
    """
    An efficient/threadsafe singleton map algorithm, a.k.a.
    "get a value based on this key, and create if not found or not
    valid" paradigm:

        exists && isvalid ? get : create

    Designed to work with weakref dictionaries to expect items
    to asynchronously disappear from the dictionary.

    Use python 2.3.3 or greater !  a major bug was just fixed in Nov.
    2003 that was driving me nuts with garbage collection/weakrefs in
    this section.

    """
    def __init__(self):
        self.mutex = _threading.Lock()
        self.dict = {}

    def get(self, key, createfunc, *args, **kwargs):
        try:
            if key in self.dict:
                return self.dict[key]
            else:
                return self.sync_get(key, createfunc, *args, **kwargs)
        except KeyError:
            return self.sync_get(key, createfunc, *args, **kwargs)

    def sync_get(self, key, createfunc, *args, **kwargs):
        self.mutex.acquire()
        try:
            try:
                if key in self.dict:
                    return self.dict[key]
                else:
                    return self._create(key, createfunc, *args, **kwargs)
            except KeyError:
                return self._create(key, createfunc, *args, **kwargs)
        finally:
            self.mutex.release()

    def _create(self, key, createfunc, *args, **kwargs):
        self[key] = obj = createfunc(*args, **kwargs)
        return obj

    def has_key(self, key):
        return key in self.dict

    def __contains__(self, key):
        return self.dict.__contains__(key)

    def __getitem__(self, key):
        return self.dict.__getitem__(key)

    def __setitem__(self, key, value):
        self.dict.__setitem__(key, value)

    def __delitem__(self, key):
        return self.dict.__delitem__(key)

    def clear(self):
        self.dict.clear()


class WeakValuedRegistry(SyncDict):
    def __init__(self):
        self.mutex = _threading.RLock()
        self.dict = weakref.WeakValueDictionary()

sha1 = None


def encoded_path(root, identifiers, extension=".enc", depth=3,
                 digest_filenames=True):

    """Generate a unique file-accessible path from the given list of
    identifiers starting at the given root directory."""
    ident = "_".join(identifiers)

    global sha1
    if sha1 is None:
        from beaker.crypto import sha1

    if digest_filenames:
        if isinstance(ident, str):
            ident = sha1(ident.encode('utf-8')).hexdigest()
        else:
            ident = sha1(ident).hexdigest()

    ident = os.path.basename(ident)

    tokens = []
    for d in range(1, depth):
        tokens.append(ident[0:d])

    dir = os.path.join(root, *tokens)
    verify_directory(dir)

    return os.path.join(dir, ident + extension)


def asint(obj):
    if isinstance(obj, int):
        return obj
    elif isinstance(obj, str) and re.match(r'^\d+$', obj):
        return int(obj)
    else:
        raise Exception("This is not a proper int")


def verify_options(opt, types, error):
    if not isinstance(opt, types):
        if not isinstance(types, tuple):
            types = (types,)
        coerced = False
        for typ in types:
            try:
                if typ in (list, tuple):
                    opt = [x.strip() for x in opt.split(',')]
                else:
                    if typ == bool:
                        typ = asbool
                    elif typ == int:
                        typ = asint
                    elif typ in (timedelta, datetime):
                        if not isinstance(opt, typ):
                            raise Exception("%s requires a timedelta type", typ)
                    opt = typ(opt)
                coerced = True
            except:
                pass
            if coerced:
                break
        if not coerced:
            raise Exception(error)
    elif isinstance(opt, str) and not opt.strip():
        raise Exception("Empty strings are invalid for: %s" % error)
    return opt


def verify_rules(params, ruleset):
    for key, types, message in ruleset:
        if key in params:
            params[key] = verify_options(params[key], types, message)
    return params


def coerce_session_params(params):
    rules = [
        ('data_dir', (str, type(None)), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str, type(None)), "lock_dir must be a string referring to a directory."),
        ('type', (str, type(None)), "Session type must be a string."),
        ('cookie_expires', (bool, datetime, timedelta, int),
         "Cookie expires was not a boolean, datetime, int, or timedelta instance."),
        ('cookie_domain', (str, type(None)), "Cookie domain must be a string."),
        ('cookie_path', (str, type(None)), "Cookie path must be a string."),
        ('id', (str,), "Session id must be a string."),
        ('key', (str,), "Session key must be a string."),
        ('secret', (str, type(None)), "Session secret must be a string."),
        ('validate_key', (str, type(None)), "Session validate_key must be a string."),
        ('encrypt_key', (str, type(None)), "Session encrypt_key must be a string."),
        ('encrypt_nonce_bits', (int, type(None)), "Session encrypt_nonce_bits must be a number"),
        ('secure', (bool, type(None)), "Session secure must be a boolean."),
        ('httponly', (bool, type(None)), "Session httponly must be a boolean."),
        ('timeout', (int, type(None)), "Session timeout must be an integer."),
        ('save_accessed_time', (bool, type(None)),
         "Session save_accessed_time must be a boolean (defaults to true)."),
        ('auto', (bool, type(None)), "Session is created if accessed."),
        ('webtest_varname', (str, type(None)), "Session varname must be a string."),
        ('data_serializer', (str,), "data_serializer must be a string.")
    ]
    opts = verify_rules(params, rules)
    cookie_expires = opts.get('cookie_expires')
    if cookie_expires and isinstance(cookie_expires, int) and \
       not isinstance(cookie_expires, bool):
        opts['cookie_expires'] = timedelta(seconds=cookie_expires)

    if opts.get('timeout') is not None and not opts.get('save_accessed_time', True):
        raise Exception("save_accessed_time must be true to use timeout")

    return opts


def coerce_cache_params(params):
    rules = [
        ('data_dir', (str, type(None)), "data_dir must be a string referring to a directory."),
        ('lock_dir', (str, type(None)), "lock_dir must be a string referring to a directory."),
        ('type', (str,), "Cache type must be a string."),
        ('enabled', (bool, type(None)), "enabled must be true/false if present."),
        ('expire', (int, type(None)),
         "expire must be an integer representing how many seconds the cache is valid for"),
        ('regions', (list, tuple, type(None)),
         "Regions must be a comma separated list of valid regions"),
        ('key_length', (int, type(None)),
         "key_length must be an integer which indicates the longest a key can be before hashing"),
    ]
    return verify_rules(params, rules)


def parse_cache_config_options(config, include_defaults=True):
    """Parse configuration options and validate for use with the
    CacheManager"""

    # Load default cache options
    if include_defaults:
        options = dict(type='memory', data_dir=None, expire=None,
                           log_file=None)
    else:
        options = {}
    for key, val in config.items():
        if key.startswith('beaker.cache.'):
            options[key[13:]] = val
        if key.startswith('cache.'):
            options[key[6:]] = val
    coerce_cache_params(options)

    # Set cache to enabled if not turned off
    if 'enabled' not in options and include_defaults:
        options['enabled'] = True

    # Configure region dict if regions are available
    regions = options.pop('regions', None)
    if regions:
        region_configs = {}
        for region in regions:
            if not region:  # ensure region name is valid
                continue
            # Setup the default cache options
            region_options = dict(data_dir=options.get('data_dir'),
                                  lock_dir=options.get('lock_dir'),
                                  type=options.get('type'),
                                  enabled=options['enabled'],
                                  expire=options.get('expire'),
                                  key_length=options.get('key_length', DEFAULT_CACHE_KEY_LENGTH))
            region_prefix = '%s.' % region
            region_len = len(region_prefix)
            for key in dictkeyslist(options):
                if key.startswith(region_prefix):
                    region_options[key[region_len:]] = options.pop(key)
            coerce_cache_params(region_options)
            region_configs[region] = region_options
        options['cache_regions'] = region_configs
    return options


def func_namespace(func):
    """Generates a unique namespace for a function"""
    kls = None
    if hasattr(func, 'im_func') or hasattr(func, '__func__'):
        kls = im_class(func)
        func = im_func(func)

    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__)
    else:
        return '%s|%s' % (inspect.getsourcefile(func), func.__name__)


class PickleSerializer(object):
    def loads(self, data_string):
        return pickle.loads(data_string)

    def dumps(self, data):
        return pickle.dumps(data, 2)


class JsonSerializer(object):
    def loads(self, data_string):
        return json.loads(zlib.decompress(data_string).decode('utf-8'))

    def dumps(self, data):
        return zlib.compress(json.dumps(data).encode('utf-8'))


def serialize(data, method):
    if method == 'json':
        serializer = JsonSerializer()
    else:
        serializer = PickleSerializer()
    return serializer.dumps(data)


def deserialize(data_string, method):
    if method == 'json':
        serializer = JsonSerializer()
    else:
        serializer = PickleSerializer()
    return serializer.loads(data_string)


def machine_identifier():
    # UUID1 includes a unique machine identifier
    return uuid.uuid1().hex


def safe_write (filepath, contents):
    if os.name == 'posix':
        tempname = '%s.temp' % (filepath)
        fh = open(tempname, 'wb')
        fh.write(contents)
        fh.close()
        os.rename(tempname, filepath)
    else:
        fh = open(filepath, 'wb')
        fh.write(contents)
        fh.close()
