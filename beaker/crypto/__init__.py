import os

from Crypto.Hash import SHA256

from PBKDF2 import PBKDF2, strxor

def generateCryptoKeys(master_key, salt, iterations):
    # NB: We XOR parts of the keystream into the randomly-generated parts, just
    # in case os.urandom() isn't as random as it should be.  Note that if
    # os.urandom() returns truly random data, this will have no effect on the
    # overall security.
    keystream = PBKDF2(master_key, salt, iterations=iterations, digestmodule=SHA256)
    cipher_key = keystream.read(32)     # 256-bit AES key (for the payload)
    cipher_nonce = strxor(keystream.read(8), os.urandom(8))     # 64-bit nonce
    return (cipher_key, cipher_nonce)
