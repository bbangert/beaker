__all__  = ["Synchronizer", "NameLock", "_threading", "_thread"]

import os
import sys
import tempfile

try:
    import thread as _thread
    import threading as _threading
except ImportError:
    import dummy_thread as _thread
    import dummy_threading as _threading

# check for fcntl module
try:
    sys.getwindowsversion()
    has_flock = False
except:
    try:
        import fcntl
        has_flock = True
    except ImportError:
        has_flock = False

from beaker.util import ThreadLocal, WeakValuedRegistry, encoded_path
from beaker.exceptions import LockError

class NameLock(object):
    """a proxy for an RLock object that is stored in a name 
    based registry.  
    
    Multiple threads can get a reference to the same RLock based on 
    the name alone, and synchronize operations related to that name.
    """
     
    locks = WeakValuedRegistry()

    class NLContainer:
        """cant put Lock as a weakref"""
        def __init__(self, reentrant):
            if reentrant:
                self.lock = _threading.RLock()
            else:
                self.lock = _threading.Lock()
        def __call__(self):
            return self.lock

    def __init__(self, identifier = None, reentrant = False):
        self.lock = self._get_lock(identifier, reentrant)

    def acquire(self, wait = True):
        return self.lock().acquire(wait)

    def release(self):
        self.lock().release()

    def _get_lock(self, identifier, reentrant):
        
        if identifier is None:
            return NameLock.NLContainer(reentrant)
        
        return NameLock.locks.get(identifier, lambda: NameLock.NLContainer(reentrant))



synchronizers = WeakValuedRegistry()

    
def Synchronizer(identifier = None, use_files = False, lock_dir = None, digest_filenames = True):
    """
    returns an object that synchronizes a block against many simultaneous 
    read operations and several synchronized write operations. 

    Write operations
    are assumed to be much less frequent than read operations,
    and receive precedence when they request a write lock.

    uses strategies to determine if locking is performed via threading objects
    or file objects.
    
    the identifier identifies a name this Synchronizer is synchronizing against.
    All synchronizers of the same identifier will lock against each other, within
    the effective thread/process scope.
    
    use_files determines if this synchronizer will lock against thread mutexes
    or file locks.  this sets the effective scope of the synchronizer, i.e. 
    it will lock against other synchronizers in the same process, or against
    other synchronizers referencing the same filesystem referenced by lock_dir.
    
    the acquire/relase methods support nested/reentrant operation within a single 
    thread via a recursion counter, so that only the outermost call to 
    acquire/release has any effect.  
    """

    if not has_flock:
        use_files = False

    if use_files:
        # FileSynchronizer is one per thread
        return synchronizers.sync_get("file_%s_%s" % (identifier, _thread.get_ident()), lambda: FileSynchronizer(identifier, lock_dir, digest_filenames))
    else:
        # ConditionSynchronizer is shared among threads
        return synchronizers.sync_get("condition_%s" % identifier, lambda: ConditionSynchronizer(identifier))


class SyncState(object):
    """used to track the current thread's reading/writing state as well as reentrant block counting"""
    
    def __init__(self):
        self.reentrantcount = 0
        self.writing = False
        self.reading = False

class SynchronizerImpl(object):
    """base for the synchronizer implementations.  the acquire/release methods keep track of re-entrant
    calls within the current thread, and delegate to the do_XXX methods when appropriate."""
    
    def __init__(self, *args, **params):
        pass

    def release_read_lock(self):
        state = self.state

        if state.writing: raise LockError("lock is in writing state")
        if not state.reading: raise LockError("lock is not in reading state")
        
        if state.reentrantcount == 1:
            self.do_release_read_lock()
            state.reading = False

        state.reentrantcount -= 1
        
    def acquire_read_lock(self, wait = True):
        state = self.state

        if state.writing: raise LockError("lock is in writing state")
        
        if state.reentrantcount == 0:
            x = self.do_acquire_read_lock(wait)
            if (wait or x):
                state.reentrantcount += 1
                state.reading = True
            return x
        elif state.reading:
            state.reentrantcount += 1
            return True
            
    def release_write_lock(self):
        state = self.state

        if state.reading: raise LockError("lock is in reading state")
        if not state.writing: raise LockError("lock is not in writing state")

        if state.reentrantcount == 1:
            self.do_release_write_lock()
            state.writing = False

        state.reentrantcount -= 1
        
    def acquire_write_lock(self, wait  = True):
        state = self.state

        if state.reading: raise LockError("lock is in reading state")
        
        if state.reentrantcount == 0:
            x = self.do_acquire_write_lock(wait)
            if (wait or x): 
                state.reentrantcount += 1
                state.writing = True
            return x
        elif state.writing:
            state.reentrantcount += 1
            return True

    def do_release_read_lock(self):
        raise NotImplementedError()
    
    def do_acquire_read_lock(self):
        raise NotImplementedError()
    
    def do_release_write_lock(self):
        raise NotImplementedError()
    
    def do_acquire_write_lock(self):
        raise NotImplementedError()
    
class FileSynchronizer(SynchronizerImpl):
    """a synchronizer using lock files.   as it relies upon flock(), which
    is not safe to use with the same file descriptor among multiple threads (one file descriptor
    per thread is OK), 
    a separate FileSynchronizer must exist in each thread."""
    
    def __init__(self, identifier, lock_dir, digest_filenames):
        self.state = SyncState()

        if lock_dir is None:
            lock_dir = tempfile.gettempdir()
        else:
            lock_dir = lock_dir

        self.filename = encoded_path(lock_dir, [identifier], extension = '.lock', digest = digest_filenames)

        self.opened = False
        self.filedesc = None
    
    def _open(self, mode):
        if not self.opened:
            self.filedesc = os.open(self.filename, mode)
            self.opened = True
            
    def do_acquire_read_lock(self, wait):
        self._open(os.O_CREAT | os.O_RDONLY)

        if not wait:
            try:
                fcntl.flock(self.filedesc, fcntl.LOCK_SH | fcntl.LOCK_NB)
                ret = True
            except IOError:
                ret = False
                
            return ret
        else:
            fcntl.flock(self.filedesc, fcntl.LOCK_SH)
            return True
        
        
    def do_acquire_write_lock(self, wait):
        self._open(os.O_CREAT | os.O_WRONLY)

        if not wait:
            try:
                fcntl.flock(self.filedesc, fcntl.LOCK_EX | fcntl.LOCK_NB)
                ret  = True
            except IOError:
                ret = False
                
            return ret
        else:
            fcntl.flock(self.filedesc, fcntl.LOCK_EX);
            return True
    
    def do_release_read_lock(self):
        self.release_all_locks()
    
    def do_release_write_lock(self):
        self.release_all_locks()
    
    def release_all_locks(self):
        if self.opened:
            fcntl.flock(self.filedesc, fcntl.LOCK_UN)
            os.close(self.filedesc)
            self.opened = False

    def __del__(self):
        if os.access(self.filename, os.F_OK):
            try:
                os.remove(self.filename)
            except OSError:
                # occasionally another thread beats us to it
                pass                    


class ConditionSynchronizer(SynchronizerImpl):
    """a synchronizer using a Condition.  this synchronizer is based on threading.Lock() objects and
    therefore must be shared among threads."""
    
    def __init__(self, identifier):
        self.tlocalstate = ThreadLocal(creator = lambda: SyncState())

        # counts how many asynchronous methods are executing
        self.async = 0

        # pointer to thread that is the current sync operation
        self.current_sync_operation = None

        # condition object to lock on
        self.condition = _threading.Condition(_threading.Lock())

    state = property(lambda self: self.tlocalstate())
        
    def do_acquire_read_lock(self, wait = True):    
        self.condition.acquire()

        # see if a synchronous operation is waiting to start
        # or is already running, in which case we wait (or just
        # give up and return)
        if wait:
            while self.current_sync_operation is not None:
                self.condition.wait()
        else:
            if self.current_sync_operation is not None:
                self.condition.release()
                return False

        self.async += 1
        
        self.condition.release()

        if not wait: return True
        
    def do_release_read_lock(self):
        self.condition.acquire()

        self.async -= 1
        
        # check if we are the last asynchronous reader thread 
        # out the door.
        if self.async == 0:
            # yes. so if a sync operation is waiting, notifyAll to wake
            # it up
            if self.current_sync_operation is not None:
                self.condition.notifyAll()
        elif self.async < 0:
            raise LockError("Synchronizer error - too many release_read_locks called")
            
        self.condition.release()

    
    def do_acquire_write_lock(self, wait = True):
        self.condition.acquire()

        # here, we are not a synchronous reader, and after returning,
        # assuming waiting or immediate availability, we will be.
        
        if wait:
            # if another sync is working, wait
            while self.current_sync_operation is not None:
                self.condition.wait()
        else:
            # if another sync is working,
            # we dont want to wait, so forget it
            if self.current_sync_operation is not None:
                self.condition.release()
                return False
            
        # establish ourselves as the current sync 
        # this indicates to other read/write operations
        # that they should wait until this is None again
        self.current_sync_operation = _threading.currentThread()

        # now wait again for asyncs to finish
        if self.async > 0:
            if wait:
                # wait
                self.condition.wait()
            else:
                # we dont want to wait, so forget it
                self.current_sync_operation = None
                self.condition.release()
                return False
        
        self.condition.release()
        
        if not wait: return True

    def do_release_write_lock(self):
        self.condition.acquire()


        if self.current_sync_operation != _threading.currentThread():
            raise LockError("Synchronizer error - current thread doesnt have the write lock")

        # reset the current sync operation so 
        # another can get it
        self.current_sync_operation = None

        # tell everyone to get ready
        self.condition.notifyAll()

        # everyone go !!
        self.condition.release()
