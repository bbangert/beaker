import os

from beaker.crypto.pbkdf2 import PBKDF2, strxor

try:
    from beaker.crypto.pycrypto import aesEncrypt, getKeyLength
except ImportError, e:
    try:
        from beaker.crypto.jcecrypto import aesEncrypt, getKeyLength
    except ImportError:
        raise e

key_length = getKeyLength()   # Key length in bytes

def generateCryptoKeys(master_key, salt, iterations):
    # NB: We XOR parts of the keystream into the randomly-generated parts, just
    # in case os.urandom() isn't as random as it should be.  Note that if
    # os.urandom() returns truly random data, this will have no effect on the
    # overall security.
    keystream = PBKDF2(master_key, salt, iterations=iterations)
    cipher_key = keystream.read(key_length)
    return cipher_key
