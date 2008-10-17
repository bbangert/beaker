"""Beaker exception classes"""

class BeakerException(Exception):
    pass


class CreationAbortedError(Exception):
    """deprecated."""

class InvalidCacheBackendError(BeakerException):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass
