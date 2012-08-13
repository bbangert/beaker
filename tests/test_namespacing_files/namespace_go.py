from __future__ import print_function
import time


def go():
    import namespace_get
    a = namespace_get.get_cached_value()
    time.sleep(0.3)
    b = namespace_get.get_cached_value()

    time.sleep(0.3)

    import test_namespacing_files.namespace_get
    c = test_namespacing_files.namespace_get.get_cached_value()
    time.sleep(0.3)
    d = test_namespacing_files.namespace_get.get_cached_value()

    print(a)
    print(b)
    print(c)
    print(d)

    assert a == b, 'Basic caching problem - should never happen'
    assert c == d, 'Basic caching problem - should never happen'
    assert a == c, 'Namespaces not consistent when using different import paths'
