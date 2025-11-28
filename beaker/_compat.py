"""Compatibility module for Python 3.8+.

This module provides compatibility aliases and utility functions
that were previously used to support both Python 2 and Python 3.
It is now simplified for Python 3.8+ only.
"""
import pickle
import http.cookies as http_cookies
from base64 import b64decode as _b64decode, b64encode as _b64encode
from urllib.parse import urlencode as url_encode
from urllib.parse import quote as url_quote
from urllib.parse import unquote as url_unquote
from urllib.parse import urlparse as url_parse
from urllib.request import url2pathname
from inspect import signature as func_signature

try:
    import dbm.gnu as anydbm
except ImportError:
    import dbm.dumb as anydbm

# Type aliases for backwards compatibility
NoneType = type(None)
string_type = str
unicode_text = str
byte_string = bytes


def b64decode(b):
    """Base64 decode a string, returning bytes."""
    return _b64decode(b.encode('ascii'))


def b64encode(s):
    """Base64 encode bytes, returning a string."""
    return _b64encode(s).decode('ascii')


def u_(s):
    """Convert to string (unicode)."""
    return str(s)


def bytes_(s):
    """Convert to bytes."""
    if isinstance(s, bytes):
        return s
    return str(s).encode('ascii', 'strict')


def dictkeyslist(d):
    """Return dictionary keys as a list."""
    return list(d.keys())


def im_func(f):
    """Get the function from a bound method."""
    return getattr(f, '__func__', None)


def default_im_func(f):
    """Get the function from a bound method, or return the function itself."""
    return getattr(f, '__func__', f)


def im_self(f):
    """Get the instance from a bound method."""
    return getattr(f, '__self__', None)


def im_class(f):
    """Get the class from a bound method."""
    self = im_self(f)
    if self is not None:
        return self.__class__
    return None


def bindfuncargs(arginfo, args, kwargs):
    """Bind function arguments to their parameters."""
    boundargs = arginfo.bind(*args, **kwargs)
    return boundargs.args, boundargs.kwargs
