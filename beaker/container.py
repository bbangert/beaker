import anydbm
import cPickle
import logging
import os.path
import string
import sys
import time

from beaker.exceptions import MissingCacheParameter
import beaker.util as util
from beaker.synchronization import _threading, _thread, Synchronizer, NameLock

__all__ = ['ContainerContext', 'Container', 
           'MemoryContainer', 'DBMContainer', 'NamespaceManager',
           'MemoryNamespaceManager', 'DBMNamespaceManager', 'FileContainer',
           'FileNamespaceManager', 'CreationAbortedError', 
           'container_registry', 'namespace_registry']

def namespace_registry(name):
    """given the string name of a Namespace 'type', return the NamespaceManager subclass corresponding to that type."""

    return _cls_registry(name, 'NamespaceManager')
    
def container_registry(name):
    """given the string name of a Container 'type', return the Container subclass corresponding to that type."""
    
    return _cls_registry(name, 'Container')

def _cls_registry(name, clsname):
    if name.startswith('ext:') \
            or name in ['memcached', 'database', 'sqla', 'google']:
        if name.startswith('ext:'):
            name = name[4:]
        modname = "beaker.ext." + name
        mod = getattr(__import__(modname).ext, name)
    else:
        mod = sys.modules[__name__]

    cname = string.capitalize(name) + clsname
    return getattr(mod, cname)

logger = logging.getLogger('beaker.container')

def debug(message, nsm, container=None):
    if logger.isEnabledFor(logging.DEBUG):
        if container is not None:
            message = "[%s:%s:%s] %s\n" % (container.__class__.__name__, 
                                           nsm.namespace, container.key, 
                                           message)
        else:
            message = "[%s] %s\n" % (nsm.namespace, message)
        logger.debug(message)
     
class NamespaceManager(object):
    """handles dictionary operations and locking for a namespace of values.  
    
    the implementation for setting and retrieving the namespace data is handled
    by subclasses.
    
    NamespaceManager may be used alone, or may be privately accessed by
    one or more Container objects.  Container objects provide per-key services
    like expiration times and automatic recreation of values.  
    
    multiple NamespaceManagers created with a particular name will all share
    access to the same underlying datasource and will attempt to synchronize
    against a common mutex object.  The scope of this sharing may be within 
    a single process or across multiple processes, depending on the type of
    NamespaceManager used.
    
    The NamespaceManager itself is generally threadsafe, except in the case
    of the DBMNamespaceManager in conjunction with the gdbm dbm implementation.
    """
    
    def __init__(self, namespace, **kwargs):
        self.namespace = namespace
        self.openers = 0
        self.mutex = _threading.Lock()
        
    def do_acquire_read_lock(self): raise NotImplementedError()
    def do_release_read_lock(self): raise NotImplementedError()
    def do_acquire_write_lock(self, wait = True): raise NotImplementedError()
    def do_release_write_lock(self): raise NotImplementedError()

    def do_open(self, flags): raise NotImplementedError()
    def do_close(self): raise NotImplementedError()

    def do_remove(self):
        """removes this namespace from wherever it is stored"""
        raise NotImplementedError()

    def debug(self, msg):
        debug(msg, self)
        
    def has_key(self, key):
        return self.__contains__(key)

    def __getitem__(self, key):
        raise NotImplementedError()
        
    def __setitem__(self, key, value):
        raise NotImplementedError()
        
    def __contains__(self, key):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()
    
    def keys(self):
        raise NotImplementedError()

    def acquire_read_lock(self): 
        """acquires a read lock for this namespace, and 
        insures that the datasource has been opened for reading
        if it is not already opened.
        
        acquire/release supports reentrant/nested operation."""
        
        self.do_acquire_read_lock()
        try:
            self.open('r', checkcount = True)
        except:
            self.do_release_read_lock()
            raise
            
    def release_read_lock(self):
        """releases the read lock for this namespace, and possibly
        closes the datasource, if it was opened as a product of
        the read lock's acquire/release block. 

        acquire/release supports reentrant/nested operation."""
    
        try:
            self.close(checkcount = True)
        finally:
            self.do_release_read_lock()
        
    def acquire_write_lock(self, wait = True): 
        """acquires a write lock for this namespace, and 
        insures that the datasource has been opened for writing if
        it is not already opened.

        acquire/release supports reentrant/nested operation."""
        
        r = self.do_acquire_write_lock(wait)
        try:
            if (wait or r): self.open('c', checkcount = True)
            return r
        except:
            self.do_release_write_lock()
            raise
            
    def release_write_lock(self): 
        """releases the write lock for this namespace, and possibly
        closes the datasource, if it was opened as a product of
        the write lock's acquire/release block. 

        acquire/release supports reentrant/nested operation."""

        try:
            self.close(checkcount = True)
        finally:
            self.do_release_write_lock()

    def open(self, flags, checkcount = False):
        """opens the datasource for this namespace.
        
        the checkcount flag indicates an "opened" counter
        should be checked for zero before performing the open operation,
        which is incremented by one regardless."""
        
        self.mutex.acquire()
        try:
            if checkcount:
                if self.openers == 0: self.do_open(flags)
                self.openers += 1
            else:
                self.do_open(flags)
                self.openers = 1
        finally:
            self.mutex.release()

    def close(self, checkcount = False):
        """closes the datasource for this namespace.
        
        the checkcount flag indicates an "opened" counter should be
        checked for zero before performing the close operation, which
        is otherwise decremented by one."""
        
        self.mutex.acquire()
        try:
            if checkcount:
                self.openers -= 1
                if self.openers == 0: self.do_close()
            else:
                if self.openers > 0:
                    self.do_close()
                self.openers = 0
        finally:
            self.mutex.release()

        
    def remove(self):
        self.do_acquire_write_lock()
        try:
            self.close(checkcount = False)
            self.do_remove()
        finally:
            self.do_release_write_lock()
            


class ContainerContext(object):
    """initial context supplied to Containers. 
    
    Keeps track of namespacemangers keyed off of namespace names and container types.
    """
    
    def __init__(self):
        self.registry = {}

    def get_namespace_manager(self, namespace, container_class, **kwargs):
        """return a NamespaceManager corresponding to the given namespace name and container class.
        
        if no NamespaceManager exists, one will be created.
        
            namespace
                string name of the namespace
            
            container_class
                a Container subclass
                
            \**kwargs
                additional keyword arguments will be used as constructor arguments for the
                Namespace, in the case that one does not exist already.
        """
        key = container_class.__name__ + "|" + namespace
        try:
            return self.registry[key]
        except KeyError:
            return self.registry.setdefault(key, container_class.create_namespace(namespace, **kwargs))
    
    def clear(self):
        self.registry.clear()
        
class Container(object):
    """represents a value, its stored time, and a value creation function corresponding to 
    a particular key in a particular namespace.
    
    handles storage and retrieval of its value via a single NamespaceManager, as well as handling
    expiration times and an optional creation function that can create or recreate its value
    when needed.
    
    the Container performs locking operations on the NamespaceManager, including a
    pretty intricate one for get_value with a creation function, so its best not
    to pass a NamespaceManager that is in a locked or opened state.
    
    Managing a set of Containers for a given set of keys allows each key to be
    stored with a distinct namespace implementation (i.e. memory for one, DBM for another), 
    expiration attribute and value-creation function.
    """
    
    def __init__(self, key, context, namespace, createfunc=None, expiretime=None, starttime=None, **kwargs):
        """create a container that stores one cached object.
        
        createfunc - a function that will create the value.  this function is called
        when value is None or expired.  the createfunc 
        call is also synchronized against any other threads or processes calling this 
        cache.
        expiretime - time in seconds that the item expires.
        """
        self.key = key
        self.createfunc = createfunc
        self.expiretime = expiretime
        self.starttime = starttime
        self.storedtime = -1
        # TODO: consume **kwargs for Namespace and do_init separately, raise errors for remaining kwargs
        self.namespacemanager = context.get_namespace_manager(namespace, self.__class__, **kwargs)
        self.do_init(**kwargs)

    def acquire_read_lock(self):
        self.namespacemanager.acquire_read_lock()
        
    def release_read_lock(self):
        self.namespacemanager.release_read_lock()
        
    def acquire_write_lock(self, wait = True):
        return self.namespacemanager.acquire_write_lock(wait)
        
    def release_write_lock(self):
        self.namespacemanager.release_write_lock()
    
    def debug(self, message):
        debug(message, self.namespacemanager, container=self)

    def create_namespace(cls, context, namespace, **kwargs): 
        """create a new instance of NamespaceManager corresponding to this Container's class."""
        raise NotImplementedError()
    create_namespace = classmethod(create_namespace)
    
    def do_init(self, **kwargs): 
        """subclasses can perform general initialization.
        
        optional template method."""
        pass

    def do_get_value(self):
        """retrieves the native stored value of this container, regardless of if its
        expired, or raise KeyError if no value is defined.
        optionally a template method."""
    
        return self.namespacemanager[self.key]  
    
    def do_set_value(self, value):
        """sets the raw value in this container.
        optionally a template method."""
        self.namespacemanager[self.key] = value
        
    def do_clear_value(self):
        """clears the value of this container.  
        
        subsequent do_get_value calls should raise KeyError.
        optionally a template method."""
        
        if self.namespacemanager.has_key(self.key):
            del self.namespacemanager[self.key]
            
        
    def has_value(self):
        """returns true if the container has a value stored, 
        regardless of it being expired or not.
        
        optionally a template method."""

        self.acquire_read_lock()
        try:    
            return self.namespacemanager.has_key(self.key)
        finally:
            self.release_read_lock()
    

    def lock_createfunc(self, wait = True): 
        """required template method that locks this container's namespace and key
        to allow a single execution of the creation function."""
        
        raise NotImplementedError()
        
    def unlock_createfunc(self): 
        """required template method that unlocks this container's namespace and key
        when the creation function is complete."""
        
        raise NotImplementedError()
    
    def can_have_value(self):
        """returns true if this container either has a non-expired value, or is capable of creating one
        via a creation function"""
        return self.has_current_value() or self.createfunc is not None  

    def has_current_value(self):
        """returns true if this container has a non-expired value"""
        return self.has_value() and not self.is_expired()

    def stored_time(self):
        return self.storedtime

    def get_namespace_manager(self):
        return self.namespacemanager
    
    def get_all_namespaces(self):
        return self.namespacemanager.context._container_namespaces.values()
        
    def is_expired(self):
        """returns true if this container's value is expired, based
        on the last time get_value was called."""
        return (
            (
                self.starttime is not None and
                self.storedtime < self.starttime
            )
            or
            (
                self.expiretime is not None and
                time.time() >= self.expiretime + self.storedtime
            )
        )

    def get_value(self):
        """get_value performs a get with expiration checks on its namespacemanager.
        if a creation function is specified, a new value will be created if the 
        existing value is nonexistent or has expired."""
        
        self.acquire_read_lock()
        try:
            has_value = self.has_value()
            if has_value:
                [self.storedtime, value] = self.do_get_value()
                if not self.is_expired():
                    return value
    
            if not self.can_have_value():
                raise KeyError(self.key)


        finally:
            self.release_read_lock()

        has_createlock = False
        if has_value:
            if not self.lock_createfunc(wait = False):
                self.debug("get_value returning old value while new one is created")
                return value
            else:
                self.debug("lock_creatfunc (didnt wait)")
                has_createlock = True

        if not has_createlock:
            self.debug("lock_createfunc (waiting)")
            self.lock_createfunc()
            self.debug("lock_createfunc (waited)")

        try:
            # see if someone created the value already
            self.acquire_read_lock()
            try:
                if self.has_value():
                    [self.storedtime, value] = self.do_get_value()
                    if not self.is_expired():
                        return value
            finally:
                self.release_read_lock()

            self.debug("get_value creating new value")
            try:
                v = self.createfunc()
            except CreationAbortedError, e:
                raise
                
            self.set_value(v)
            
            return v
        finally:
            self.unlock_createfunc()
            self.debug("unlock_createfunc")
                
            
    def set_value(self, value):
        self.acquire_write_lock()
        try:
            self.storedtime = time.time()
            self.debug("set_value stored time %d" % self.storedtime)
            self.do_set_value([self.storedtime, value])
        finally:
            self.release_write_lock()

    def clear_value(self):
        self.acquire_write_lock()
        try:
            self.debug("clear_value")
            self.do_clear_value()
            self.storedtime = -1
        finally:
            self.release_write_lock()
        
class CreationAbortedError(Exception):
    """an exception that allows a creation function to abort what its doing"""
    
    pass

class MemoryNamespaceManager(NamespaceManager):
    namespaces = util.SyncDict(_threading.Lock(), {})

    def __init__(self, namespace, **kwargs):
        NamespaceManager.__init__(self, namespace, **kwargs)

        self.lock = Synchronizer(identifier = "memorycontainer/namespacelock/%s" % self.namespace, use_files = False)
        
        self.dictionary = MemoryNamespaceManager.namespaces.get(self.namespace, lambda: {})
        
    def do_acquire_read_lock(self): self.lock.acquire_read_lock()
    def do_release_read_lock(self): self.lock.release_read_lock()
    def do_acquire_write_lock(self, wait = True): return self.lock.acquire_write_lock(wait)
    def do_release_write_lock(self): self.lock.release_write_lock()

    # the open and close methods are totally overridden to eliminate
    # the unnecessary "open count" computation involved
    def open(self, *args, **kwargs):pass
    def close(self, *args, **kwargs):pass
    
    def __getitem__(self, key): return self.dictionary[key]

    def __contains__(self, key): 
        return self.dictionary.__contains__(key)

    def has_key(self, key): 
        return self.dictionary.__contains__(key)
        
    def __setitem__(self, key, value):self.dictionary[key] = value
    
    def __delitem__(self, key):
        del self.dictionary[key]

    def do_remove(self):
        self.dictionary.clear()
        
    def keys(self):
        return self.dictionary.keys()

class MemoryContainer(Container):

    def do_init(self, **kwargs):
        self.funclock = None
    
    def create_namespace(cls, namespace, **kwargs):
        return MemoryNamespaceManager(namespace, **kwargs)
    create_namespace = classmethod(create_namespace)
        
    def lock_createfunc(self, wait = True): 
        if self.funclock is None:
            self.funclock = NameLock(identifier = "memorycontainer/funclock/%s/%s" % (self.namespacemanager.namespace, self.key), reentrant = True)
            
        return self.funclock.acquire(wait)

    def unlock_createfunc(self): self.funclock.release()


class DBMNamespaceManager(NamespaceManager):

    def __init__(self, namespace, dbmmodule = None, data_dir = None, dbm_dir = None, lock_dir = None, digest_filenames = True, **kwargs):
        NamespaceManager.__init__(self, namespace, **kwargs)

        if dbm_dir is not None:
            self.dbm_dir = dbm_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or dbm_dir is required")
        else:
            self.dbm_dir = data_dir + "/container_dbm"
        
        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        else:
            self.lock_dir = data_dir + "/container_dbm_lock"

        if dbmmodule is None:
            self.dbmmodule = anydbm
        else:
            self.dbmmodule = dbmmodule
        
        util.verify_directory(self.dbm_dir)
        util.verify_directory(self.lock_dir)

        self.dbm = None

        self.lock = Synchronizer(identifier=self.namespace, use_files=True, 
                                 lock_dir=self.lock_dir, 
                                 digest_filenames=digest_filenames)
        self.file = util.encoded_path(root= self.dbm_dir, 
                                      identifiers=[self.namespace], 
                                      digest=digest_filenames, 
                                      extension='.dbm')
        
        self.debug("data file %s" % self.file)
        
        self._checkfile()

    def file_exists(self, file):
        if os.access(file, os.F_OK): return True
        else:
            for ext in ('db', 'dat', 'pag', 'dir'):
                if os.access(file + os.extsep + ext, os.F_OK):
                    return True
                    
        return False
    
    def _checkfile(self):
        if not self.file_exists(self.file):
            g = self.dbmmodule.open(self.file, 'c') 
            g.close()
                
    def get_filenames(self):
        list = []
        if os.access(self.file, os.F_OK):
            list.append(self.file)
            
        for ext in ('pag', 'dir', 'db', 'dat'):
            if os.access(self.file + os.extsep + ext, os.F_OK):
                list.append(self.file + os.extsep + ext)
        return list
        

    def do_acquire_read_lock(self): 
        self.lock.acquire_read_lock()
        
    def do_release_read_lock(self): 
        self.lock.release_read_lock()
        
    def do_acquire_write_lock(self, wait = True): 
        return self.lock.acquire_write_lock(wait)
        
    def do_release_write_lock(self): 
        self.lock.release_write_lock()

    def do_open(self, flags):
        # caution: apparently gdbm handles arent threadsafe, they 
        # are using flock(), and i would rather not have knowledge
        # of the "unlock" 'u' option just for that one dbm module.
        # therefore, neither is an individual instance of
        # this namespacemanager (of course, multiple nsm's
        # can exist for each thread).
        self.debug("opening dbm file %s" % self.file)
        try:
            self.dbm = self.dbmmodule.open(self.file, flags)
        except:
            self._checkfile()
            self.dbm = self.dbmmodule.open(self.file, flags)

    def do_close(self):
        if self.dbm is not None:
            self.debug("closing dbm file %s" % self.file)
            self.dbm.close()
        
    def do_remove(self):
        for f in self.get_filenames():
            os.remove(f)
        
    def __getitem__(self, key): 
        return cPickle.loads(self.dbm[key])

    def __contains__(self, key): 
        return self.dbm.has_key(key)
        
    def __setitem__(self, key, value):
        self.dbm[key] = cPickle.dumps(value)

    def __delitem__(self, key):
        del self.dbm[key]

    def keys(self):
        return self.dbm.keys()
    
class DBMContainer(Container):

    def do_init(self, **kwargs):
        self.funclock = None
        
    def create_namespace(cls, namespace, **kwargs):
        return DBMNamespaceManager(namespace, **kwargs)
    create_namespace = classmethod(create_namespace)
    
    def lock_createfunc(self, wait = True): 
        if self.funclock is None:
            self.funclock = Synchronizer(identifier = "dbmcontainer/funclock/%s" % self.namespacemanager.namespace, use_files = True, lock_dir = self.namespacemanager.lock_dir)
        
        return self.funclock.acquire_write_lock(wait)

    def unlock_createfunc(self): self.funclock.release_write_lock()
    
DbmNamespaceManager = DBMNamespaceManager
DbmContainer = DBMContainer


class FileNamespaceManager(NamespaceManager):

    def __init__(self, namespace, data_dir = None, file_dir = None, lock_dir = None, digest_filenames = True, **kwargs):
        NamespaceManager.__init__(self, namespace, **kwargs)

        if file_dir is not None:
            self.file_dir = file_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or file_dir is required")
        else:
            self.file_dir = data_dir + "/container_file"
        
        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        else:
            self.lock_dir = data_dir + "/container_file_lock"

        util.verify_directory(self.file_dir)
        util.verify_directory(self.lock_dir)

        self.lock = Synchronizer(identifier=self.namespace, use_files=True, 
                                 lock_dir=self.lock_dir, 
                                 digest_filenames=digest_filenames)
        self.file = util.encoded_path(root=self.file_dir, 
                                      identifiers=[self.namespace], 
                                      digest=digest_filenames, 
                                      extension='.cache')
        self.hash = {}
        
        self.debug("data file %s" % self.file)
        
    def file_exists(self, file):
        if os.access(file, os.F_OK): return True
        else: return False
            

    def do_acquire_read_lock(self): 
        self.lock.acquire_read_lock()
        
    def do_release_read_lock(self): 
        self.lock.release_read_lock()
        
    def do_acquire_write_lock(self, wait = True): 
        return self.lock.acquire_write_lock(wait)
        
    def do_release_write_lock(self): 
        self.lock.release_write_lock()

    def do_open(self, flags):
        if self.file_exists(self.file):
            fh = open(self.file, 'rb')
            try:
                self.hash = cPickle.load(fh)
            except (IOError, OSError, EOFError, cPickle.PickleError):
                pass
            fh.close()
        self.flags = flags
        
    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            fh = open(self.file, 'wb')
            cPickle.dump(self.hash, fh)
            fh.close()

        self.flags = None
                
    def do_remove(self):
        os.remove(self.file)
        self.hash = {}
        
    def __getitem__(self, key): 
        return self.hash[key]

    def __contains__(self, key): 
        return self.hash.has_key(key)
        
    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()
        


class FileContainer(Container):

    def do_init(self, **kwargs):
        self.funclock = None
        
    def create_namespace(cls, namespace, **kwargs):
        return FileNamespaceManager(namespace, **kwargs)
    create_namespace = classmethod(create_namespace)
    
    def lock_createfunc(self, wait = True): 
        if self.funclock is None:
            self.funclock = Synchronizer(identifier = "filecontainer/funclock/%s" % self.namespacemanager.namespace, use_files = True, lock_dir = self.namespacemanager.lock_dir)
        
        return self.funclock.acquire_write_lock(wait)

    def unlock_createfunc(self): self.funclock.release_write_lock()
