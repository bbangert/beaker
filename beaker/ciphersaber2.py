"""A CipherSaber-2 implementation

Updated Dec 12, 2007 by Ben Bangert <ben@groovie.org>
    - Removed command line usage.
    - Attempts to use os.urandom for the random IV as its more random
      than the Python random module.
Updated Feb 5, 2002 by Magnus Lie Hetland <magnus@hetland.org>
    - Unlike the original, ASCII armour is used, and getpass is used to
      read the password if it is not supplied on the commandline. 
      Therefore explicit filenames are used instead of stdin and 
      stdout.
Original by: Ka-Ping Yee <ping@lfw.org>

For more information about CipherSaber, see http://ciphersaber.gurus.com
"""
import os
import sys
import random
import getpass


def arcfour(input, key, n=20):
    '''Perform the ARCFOUR algorithm on a given input list of bytes with a
    key given as a list of bytes, and return the output as a list of bytes.'''
    i, j, state = 0, 0, range(256)
    for k in range(n):
        for i in range(256):
            j = (j + state[i] + key[i % len(key)]) % 256
            state[i], state[j] = state[j], state[i]
    i, j, output = 0, 0, []
    for byte in input:
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        n = (state[i] + state[j]) % 256
        output.append(byte ^ state[n])
    return output

def b2a(text):
    'Given a string of binary data, return an "armoured" string.'
    lines = []
    words = ['%02x' % o for o in map(ord, text)]
    while words:
        lines.append(' '.join(words[:23]))
        del words[:23]
    return '\n'.join(lines)

def a2b(text):
    'Given an "armoured" string, return a string of binary data.'
    return ''.join(map(chr, [int(w, 16) for w in text.split()]))

def encipher(plaintext, key, iv=""):
    'Given a plaintext string and key, return an enciphered string.'
    if hasattr(os, 'urandom'):
        iv = os.urandom(10)
    else:
        while len(iv) < 10: 
            iv = iv + chr(random.randrange(256))
    bytes = arcfour(map(ord, plaintext), map(ord, key + iv))
    return iv + ''.join(map(chr, bytes))

def decipher(ciphertext, key):
    'Given a ciphertext string and key, return the deciphered string.'
    iv, ciphertext = ciphertext[:10], ciphertext[10:]
    bytes = arcfour(map(ord, ciphertext), map(ord, key + iv))
    return ''.join(map(chr, bytes))
