from beaker.synchronization import *

# TODO: spawn threads, test locking.


def teardown():
    import shutil
    shutil.rmtree('./cache', True)

def test_reentrant_file():
    sync1 = file_synchronizer('test', lock_dir='./cache')
    sync2 = file_synchronizer('test', lock_dir='./cache')
    sync1.acquire_write_lock()
    sync2.acquire_write_lock()
    sync2.release_write_lock()
    sync1.release_write_lock()

def test_null():
    sync = null_synchronizer()
    assert sync.acquire_write_lock()
    sync.release_write_lock()

def test_mutex():
    sync = mutex_synchronizer('someident')
    sync.acquire_write_lock()
    sync.release_write_lock()

