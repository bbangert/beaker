from binascii import b2a_hex, a2b_hex
from beaker.crypto.pbkdf2 import pbkdf2


def test_pbkdf2_test1():
    result = pbkdf2("password", "ATHENA.MIT.EDUraeburn", 1)[:16]
    expected = a2b_hex("cdedb5281bb2f801565a1122b2563515")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_pbkdf2_test2():
    result = b2a_hex(pbkdf2("password", "ATHENA.MIT.EDUraeburn", 1200)[:32])
    expected = ("5c08eb61fdf71e4e4ec3cf6ba1f5512b"
                "a7e52ddbc5e5142f708a31e2e62b1e13")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_pbkdf2_test3():
    result = b2a_hex(pbkdf2("X"*64, "pass phrase equals block size", 1200)[:32])
    expected = ("139c30c0966bc32ba55fdbf212530ac9"
                "c5ec59f1a452f5cc9ad940fea0598ed1")
    if result != expected:
        raise RuntimeError("self-test failed")


def test_pbkdf2_test4():
    result = b2a_hex(pbkdf2("X"*65, "pass phrase exceeds block size", 1200)[:32])
    expected = ("9ccad6d468770cd51b10e6a68721be61"
                "1a8b4d282601db3b36be9246915ec82a")
    if result != expected:
        raise RuntimeError("self-test failed")
