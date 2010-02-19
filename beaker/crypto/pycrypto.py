"""
Encryption module that uses pycryptopp or pycrypto

"""

try:
    # TODO: why is pycryptopp preferred over Crypto.Cipher ?
    
    from pycryptopp.cipher import aes

    def aesEncrypt(data, key):
        cipher = aes.AES(key)
        return cipher.process(data)
    
    # magic.
    aesDecrypt = aesEncrypt
    
except ImportError:
    from Crypto.Cipher import AES

    def aesEncrypt(data, key):
        cipher = AES.new(key)
        
        data = data + (" " * (16 - (len(data) % 16)))
        return cipher.encrypt(data)

    def aesDecrypt(data, key):
        cipher = AES.new(key)

        return cipher.decrypt(data).rstrip()

def getKeyLength():
    return 32
