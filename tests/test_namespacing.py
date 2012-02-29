import os
import sys


def teardown():
    import shutil
    shutil.rmtree('./cache', True)


def test_consistent_namespacing():
    sys.path.append(os.path.dirname(__file__))
    from tests.test_namespacing_files.namespace_go import go
    go()
