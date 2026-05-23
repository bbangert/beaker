"""Compatibility utilities for Beaker.

This module provides utility functions that are used throughout Beaker.
"""
from base64 import b64decode as _b64decode, b64encode as _b64encode
from inspect import signature

try:
    import dbm.gnu as anydbm
except ImportError:
    import dbm.dumb as anydbm


def b64decode(b):
    """Base64 decode a string, returning bytes."""
    return _b64decode(b.encode('ascii'))


def b64encode(s):
    """Base64 encode bytes, returning a string."""
    return _b64encode(s).decode('ascii')


def bytes_(s):
    """Convert to bytes."""
    if isinstance(s, bytes):
        return s
    return str(s).encode('ascii', 'strict')


def bindfuncargs(arginfo, args, kwargs):
    """Bind function arguments to their parameters."""
    boundargs = arginfo.bind(*args, **kwargs)
    return boundargs.args, boundargs.kwargs
