import os

from beaker.crypto.pbkdf2 import PBKDF2, strxor

def generateCryptoKeys(master_key, salt, iterations):
    # NB: We XOR parts of the keystream into the randomly-generated parts, just
    # in case os.urandom() isn't as random as it should be.  Note that if
    # os.urandom() returns truly random data, this will have no effect on the
    # overall security.
    keystream = PBKDF2(master_key, salt, iterations=iterations)
    cipher_key = keystream.read(32)     # 256-bit AES key (for the payload)
    return cipher_key
