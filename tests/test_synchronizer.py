from beaker.synchronization import synchronizer, FileSynchronizer


def test_reentrant():
    sync1 = synchronizer('test', FileSynchronizer, lock_dir='./')
    sync2 = synchronizer('test', FileSynchronizer, lock_dir='./')
    sync1.acquire_write_lock()
    sync2.acquire_write_lock()
    sync2.release_write_lock()
    sync1.release_write_lock()
        
