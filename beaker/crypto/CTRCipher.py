#!/usr/bin/python
# -*- coding: ascii -*-
###########################################################################
# CTRCipher.py - Make PyCrypto CTR-mode properly as stream ciphers
#
# Copyright (C) 2007 Dwayne C. Litzenberger <dlitz@dlitz.net>
# All rights reserved.
# 
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation.
# 
# THE AUTHOR PROVIDES THIS SOFTWARE ``AS IS'' AND ANY EXPRESSED OR 
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Country of origin: Canada
#
###########################################################################
# History:
#
#  2007-07-28 Dwayne C. Litzenberger <dlitz@dlitz.net>
#   - Pre-release (v0.0)
#
###########################################################################

from struct import pack

class CTRCounter(object):
    def __init__(self, nonce):
        if len(nonce) != 8:
            raise ValueError("nonce must be 8 bytes")
        self.nonce = nonce
        self.counter = 0
        self._ctr_mask = ((1<<64)-1)
    def __call__(self):
        self.counter = (self.counter + 1) & self._ctr_mask
        if self.counter == 0:
            raise OverflowError("Counter overflowed")
        return self.nonce + pack("!Q", self.counter)

    def setNext(self, counter):
        self.counter = counter - 1

class CTRCipher(object):
    
    block_size = 0      # behaves like a stream cipher

    def __init__(self, key, nonce, ciphermodule):
        self._counter = CTRCounter(nonce)
        self._cipher = ciphermodule.new(key, ciphermodule.MODE_CTR, counter=self._counter)
        self._offset = 0

    def encrypt(self, plaintext):
        assert(self._offset >= 0)
        if len(plaintext) == 0:
            return ""
        if self._offset != 0:
            self._counter.setNext(self._counter.counter)
        beforePad = self._offset + len(plaintext)
        pad_size = self._cipher.block_size - (self._offset + len(plaintext)) % self._cipher.block_size
        if pad_size == self._cipher.block_size:
            pad_size = 0
        ciphertext = self._cipher.encrypt("\0" * self._offset + plaintext + "\0" * pad_size)
        ciphertext = ciphertext[self._offset:beforePad]
        self._offset = beforePad % self._cipher.block_size
        return ciphertext

    def decrypt(self, ciphertext):
        return self.encrypt(ciphertext)

# vim:set ts=4 sw=4 sts=4 expandtab:
