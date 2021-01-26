"""Encryption module that uses cryptodomex, pycryptopp, or pycrypto, whichever is
available first.

cryptodomex is preferred over Pycryptopp because (as of 2021-01-26) it
is more actively maintained.

"""

try:
    import Cryptodome
    have_cryptodome = True
except ImportError:
    have_cryptodome = False

try:
    import pycryptopp
    have_pycryptopp = True
except ImportError:
    have_pycryptopp = False

try:
    import Crypto
    have_pycrypto = True
except ImportError:
    have_pycrypto = False

if have_cryptodome:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util import Counter

    def aesEncrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))

        return cipher.encrypt(data)

    def aesDecrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))
        return cipher.decrypt(data)
elif have_pycryptopp:
    from pycryptopp.cipher import aes

    def aesEncrypt(data, key):
        cipher = aes.AES(key)
        return cipher.process(data)

    # magic.
    aesDecrypt = aesEncrypt
elif have_pycrypto:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter

    def aesEncrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))

        return cipher.encrypt(data)

    def aesDecrypt(data, key):
        cipher = AES.new(key, AES.MODE_CTR,
                         counter=Counter.new(128, initial_value=0))
        return cipher.decrypt(data)
else:
    raise Exception("Could not find a suitable module to implement beaker.crypto.pycrypto")

has_aes = True

def getKeyLength():
    return 32
