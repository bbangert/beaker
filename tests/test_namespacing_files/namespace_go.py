from __future__ import print_function
import time


def go():
    from . import namespace_get
    a = namespace_get.get_cached_value()
    time.sleep(0.3)
    b = namespace_get.get_cached_value()

    time.sleep(0.3)

    from ..test_namespacing_files import namespace_get as upper_ns_get
    c = upper_ns_get.get_cached_value()
    time.sleep(0.3)
    d = upper_ns_get.get_cached_value()

    print(a)
    print(b)
    print(c)
    print(d)

    assert a == b, 'Basic caching problem - should never happen'
    assert c == d, 'Basic caching problem - should never happen'
    assert a == c, 'Namespaces not consistent when using different import paths'
