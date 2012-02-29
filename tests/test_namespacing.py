import sys

def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def test_consistent_namespacing():
   sys.path.append('/Users/brianfrantz/Source/beaker/tests')
   from tests.test_namespacing_files.namespace_go import go
   go()

