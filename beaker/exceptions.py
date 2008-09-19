"""Beaker exception classes"""

class BeakerException(Exception):
    pass


class CreationAbortedError(Exception):
    """an exception that allows a creation function to abort what it's
    doing"""


class InvalidCacheBackendError(BeakerException):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass
