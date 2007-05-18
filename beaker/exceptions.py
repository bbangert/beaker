class BeakerException(Exception):
    pass

class InvalidCacheBackendError(BeakerException):
    pass

class MissingCacheParameter(BeakerException):
    pass

class LockError(BeakerException):
    pass
