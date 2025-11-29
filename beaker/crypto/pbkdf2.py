"""
PBKDF2 Implementation using the stdlib.

This is used to generate the encryption key for enciphered sessions.
"""
from beaker._compat import bytes_

import hashlib


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """
    Implements PBKDF2 using the stdlib.

    HMAC+SHA256 is used as the default pseudo random function.

    As of 2014, 100,000 iterations was the recommended default which took
    100ms on a 2.7Ghz Intel i7 with an optimized implementation. This is
    probably the bare minimum for security given 1000 iterations was
    recommended in 2001.
    """
    if digest is None:
        digest = hashlib.sha1
    if not dklen:
        dklen = None
    password = bytes_(password)
    salt = bytes_(salt)
    return hashlib.pbkdf2_hmac(
        digest().name, password, salt, iterations, dklen)
