from beaker.synchronization import Synchronizer
import test_base

class SynchronizerTest(test_base.MyghtyTest):
    def test_reentrant(self):
        sync1 = Synchronizer(identifier='test', use_files=True, lock_dir='./')
        sync2 = Synchronizer(identifier='test', use_files=True, lock_dir='./')
        sync1.acquire_write_lock()
        sync2.acquire_write_lock()
        sync2.release_write_lock()
        sync1.release_write_lock()
        
