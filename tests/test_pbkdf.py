# -*- coding: utf-8 -*-

from beaker.crypto.pbkdf2 import PBKDF2, crypt
from binascii import a2b_hex


# Test vectors from RFC 3962

def test_1():
    result = PBKDF2(u"password", "ATHENA.MIT.EDUraeburn", 1).read(16)
    expected = a2b_hex("cdedb5281bb2f801565a1122b2563515")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_2():
    result = PBKDF2(u"password", "ATHENA.MIT.EDUraeburn", 1200).hexread(32)
    expected = (b"5c08eb61fdf71e4e4ec3cf6ba1f5512b"
                b"a7e52ddbc5e5142f708a31e2e62b1e13")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_3():
    result = PBKDF2(u"X"*64, "pass phrase equals block size", 1200).hexread(32)
    expected = (b"139c30c0966bc32ba55fdbf212530ac9"
                b"c5ec59f1a452f5cc9ad940fea0598ed1")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_4():
    result = PBKDF2(u"X"*65, "pass phrase exceeds block size", 1200).hexread(32)
    expected = (b"9ccad6d468770cd51b10e6a68721be61"
                b"1a8b4d282601db3b36be9246915ec82a")
    if result != expected:
        print repr(result), repr(expected)
        raise RuntimeError("self-test failed")


def test_chunked():
    # Chunked read
    f = PBKDF2(u"kickstart", "workbench", 256)
    result = f.read(17)
    result += f.read(17)
    result += f.read(1)
    result += f.read(2)
    result += f.read(3)
    expected = PBKDF2("kickstart", "workbench", 256).read(40)
    if result != expected:
        raise RuntimeError("self-test failed")


def test_crypt_1():
    result = crypt("cloadm", "exec")
    expected = b'$p5k2$$exec$r1EWMCMk7Rlv3L/RNcFXviDefYa0hlql'
    if result != expected:
        raise RuntimeError("self-test failed")


def test_crypt_2():
    result = crypt("cloadm", "exec")
    result = crypt("gnu", '$p5k2$c$u9HvcT4d$.....')
    expected = b'$p5k2$c$u9HvcT4d$Sd1gwSVCLZYAuqZ25piRnbBEoAesaa/g'
    print(repr(result))
    print(repr(expected))
    if result != expected:
        raise RuntimeError("self-test failed")


def test_crypt_3():
    result = crypt("cloadm", "exec")
    result = crypt("dcl", "tUsch7fU", iterations=13)
    expected = b"$p5k2$d$tUsch7fU$nqDkaxMDOFBeJsTSfABsyn.PYUXilHwL"
    if result != expected:
        raise RuntimeError("self-test failed")


def test_crypt_4():
    result = crypt("cloadm", "exec")
    result = crypt(u'\u0399\u03c9\u03b1\u03bd\u03bd\u03b7\u03c2',
        '$p5k2$$KosHgqNo$9mjN8gqjt02hDoP0c2J0ABtLIwtot8cQ')
    expected = b'$p5k2$$KosHgqNo$9mjN8gqjt02hDoP0c2J0ABtLIwtot8cQ'
    if result != expected:
        raise RuntimeError("self-test failed")
