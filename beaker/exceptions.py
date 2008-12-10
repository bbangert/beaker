"""Beaker exception classes"""

class BeakerException(Exception):
    pass


class CreationAbortedError(Exception):
    """deprecated."""

class InvalidCacheBackendError(BeakerException, ImportError):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass
