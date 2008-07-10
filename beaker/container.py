import anydbm
import cPickle
import logging
import os.path
import string
import sys
import time

from beaker.exceptions import MissingCacheParameter
import beaker.util as util
from beaker.synchronization import _threading, _thread, file_synchronizer, mutex_synchronizer, NameLock

__all__ = ['ContainerContext', 'Value', 'Container', 
           'MemoryContainer', 'DBMContainer', 'NamespaceManager',
           'MemoryNamespaceManager', 'DBMNamespaceManager', 'FileContainer',
           'FileNamespaceManager', 'CreationAbortedError', 
           'container_registry', 'namespace_registry']

def namespace_registry(name):
    """Given the string name of a Namespace 'type', 
    return the NamespaceManager subclass corresponding to that type.
    
    """
    return _cls_registry(name, 'NamespaceManager')

# deprecated
def container_registry(name):
    """Given the string name of a Container 'type', 
    return the Container subclass corresponding to that type.
    
    """
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
if logger.isEnabledFor(logging.DEBUG):
    debug = logger.debug
else:
    def debug(message):
        pass
     
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
    def __init__(self, namespace):
        self.namespace = namespace
        self.openers = 0
        self.mutex = _threading.Lock()
        self.access_lock = self.get_access_lock()
        
    def get_creation_lock(self, key):
        raise NotImplementedError()

    def get_access_lock(self):
        raise NotImplementedError()
        
    def do_open(self, flags): 
        raise NotImplementedError()
        
    def do_close(self): 
        raise NotImplementedError()

    def do_remove(self):
        raise NotImplementedError()

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
        self.access_lock.acquire_read_lock()
        try:
            self.open('r', checkcount = True)
        except:
            self.do_release_read_lock()
            raise
            
    def release_read_lock(self):
        try:
            self.close(checkcount = True)
        finally:
            self.access_lock.release_read_lock()
        
    def acquire_write_lock(self, wait=True): 
        r = self.access_lock.acquire_write_lock(wait)
        try:
            if (wait or r): 
                self.open('c', checkcount = True)
            return r
        except:
            self.access_lock.release_write_lock()
            raise
            
    def release_write_lock(self): 
        try:
            self.close(checkcount=True)
        finally:
            self.access_lock.release_write_lock()

    def open(self, flags, checkcount=False):
        self.mutex.acquire()
        try:
            if checkcount:
                if self.openers == 0: 
                    self.do_open(flags)
                self.openers += 1
            else:
                self.do_open(flags)
                self.openers = 1
        finally:
            self.mutex.release()

    def close(self, checkcount=False):
        self.mutex.acquire()
        try:
            if checkcount:
                self.openers -= 1
                if self.openers == 0: 
                    self.do_close()
            else:
                if self.openers > 0:
                    self.do_close()
                self.openers = 0
        finally:
            self.mutex.release()

    def remove(self):
        self.access_lock.acquire_write_lock()
        try:
            self.close(checkcount=False)
            self.do_remove()
        finally:
            self.access_lock.release_write_lock()

class ContainerContext(object):
    """initial context supplied to Containers. 
    
    Keeps track of namespacemangers keyed off of namespace names and container types.

    """
    def __init__(self):
        self.registry = {}
    
    def get_namespace(self, namespace, cls, **kwargs):
        key = (cls, namespace)
        try:
            return self.registry[key]
        except KeyError:
            self.registry[key] = ns = cls(namespace, **kwargs)
            return ns
    
    # deprecated
    def get_namespace_manager(self, namespace, container_class, **kwargs):
        nscls = namespace_classes[container_class]
        return self.get_namespace(namespace, nscls, **kwargs)

    # remove ?
    def clear(self):
        self.registry.clear()

class Value(object):
    __slots__ = 'key', 'createfunc', 'expiretime', 'starttime', 'storedtime', 'namespacemanager'

    def __init__(self, key, context, namespace, nscls, createfunc=None, expiretime=None, starttime=None, **kwargs):
        self.key = key
        self.createfunc = createfunc
        self.expiretime = expiretime
        self.starttime = starttime
        self.storedtime = -1
        self.namespacemanager = context.get_namespace(namespace, nscls, **kwargs)

    def has_value(self):
        """return true if the container has a value stored.

        This is regardless of it being expired or not.

        """
        self.namespacemanager.acquire_read_lock()
        try:    
            return self.namespacemanager.has_key(self.key)
        finally:
            self.namespacemanager.release_read_lock()

    def can_have_value(self):
        return self.has_current_value() or self.createfunc is not None  

    def has_current_value(self):
        return self.has_value() and not self.is_expired()

    def is_expired(self):
        """Return true if this container's value is expired."""

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
        self.namespacemanager.acquire_read_lock()
        try:
            has_value = self.has_value()
            if has_value:
                [self.storedtime, value] = self.namespacemanager[self.key]
                if not self.is_expired():
                    return value

            if not self.can_have_value():
                raise KeyError(self.key)
        finally:
            self.namespacemanager.release_read_lock()

        has_createlock = False
        creation_lock = self.namespacemanager.get_creation_lock(self.key)
        if has_value:
            if not creation_lock.acquire(wait=False):
                debug("get_value returning old value while new one is created")
                return value
            else:
                debug("lock_creatfunc (didnt wait)")
                has_createlock = True

        if not has_createlock:
            debug("lock_createfunc (waiting)")
            creation_lock.acquire()
            debug("lock_createfunc (waited)")

        try:
            # see if someone created the value already
            self.namespacemanager.acquire_read_lock()
            try:
                if self.has_value():
                    [self.storedtime, value] = self.namespacemanager[self.key]
                    if not self.is_expired():
                        return value
            finally:
                self.namespacemanager.release_read_lock()

            debug("get_value creating new value")
            try:
                v = self.createfunc()
            except CreationAbortedError, e:
                raise

            self.set_value(v)

            return v
        finally:
            creation_lock.release()
            debug("released create lock")

    def set_value(self, value):
        self.namespacemanager.acquire_write_lock()
        try:
            self.storedtime = time.time()
            debug("set_value stored time %d" % self.storedtime)
            self.namespacemanager[self.key] = [self.storedtime, value]
        finally:
            self.namespacemanager.release_write_lock()

    def clear_value(self):
        self.namespacemanager.acquire_write_lock()
        try:
            debug("clear_value")
            if self.namespacemanager.has_key(self.key):
                del self.namespacemanager[self.key]
            self.storedtime = -1
        finally:
            self.namespacemanager.release_write_lock()

class CreationAbortedError(Exception):
    """an exception that allows a creation function to abort what it's doing"""

class MemoryNamespaceManager(NamespaceManager):
    namespaces = util.SyncDict()

    def __init__(self, namespace):
        NamespaceManager.__init__(self, namespace)
        self.dictionary = MemoryNamespaceManager.namespaces.get(self.namespace, dict)
    
    def get_access_lock(self):
        return mutex_synchronizer(
            identifier="memorycontainer/namespacelock/%s" % self.namespace)
        
    def get_creation_lock(self, key):
        return NameLock(
            identifier="memorycontainer/funclock/%s/%s" % (self.namespace, key), 
            reentrant=True
        )
        
    def open(self, *args, **kwargs):
        pass
        
    def close(self, *args, **kwargs):
        pass
    
    def __getitem__(self, key): 
        return self.dictionary[key]

    def __contains__(self, key): 
        return self.dictionary.__contains__(key)

    def has_key(self, key): 
        return self.dictionary.__contains__(key)
        
    def __setitem__(self, key, value):
        self.dictionary[key] = value
    
    def __delitem__(self, key):
        del self.dictionary[key]

    def do_remove(self):
        self.dictionary.clear()
        
    def keys(self):
        return self.dictionary.keys()

class DBMNamespaceManager(NamespaceManager):

    def __init__(self, namespace, dbmmodule=None, data_dir=None, dbm_dir=None, lock_dir=None):

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
        NamespaceManager.__init__(self, namespace)

        self.file = util.encoded_path(root= self.dbm_dir, 
                                      identifiers=[self.namespace], extension='.dbm')
        
        debug("data file %s" % self.file)
        
        self._checkfile()

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace, lock_dir=self.lock_dir)
                                 
    def get_creation_lock(self, key):
        return file_synchronizer(
                    identifier = "dbmcontainer/funclock/%s" % self.namespace, 
                    lock_dir=self.lock_dir
                )

    def file_exists(self, file):
        if os.access(file, os.F_OK): 
            return True
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

    def do_open(self, flags):
        debug("opening dbm file %s" % self.file)
        try:
            self.dbm = self.dbmmodule.open(self.file, flags)
        except:
            self._checkfile()
            self.dbm = self.dbmmodule.open(self.file, flags)

    def do_close(self):
        if self.dbm is not None:
            debug("closing dbm file %s" % self.file)
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

class FileNamespaceManager(NamespaceManager):

    def __init__(self, namespace, data_dir=None, file_dir=None, lock_dir=None):
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
        NamespaceManager.__init__(self, namespace)
        self.file = util.encoded_path(root=self.file_dir, 
                                      identifiers=[self.namespace],
                                      extension='.cache')
        self.hash = {}
        
        debug("data file %s" % self.file)

    def get_access_lock(self):
        return file_synchronizer(identifier=self.namespace, lock_dir=self.lock_dir)
                                 
    def get_creation_lock(self, key):
        return file_synchronizer(
                identifier = "filecontainer/funclock/%s" % self.namespace, 
                lock_dir = self.lock_dir
                )
        
    def file_exists(self, file):
        return os.access(file, os.F_OK)

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
        if self.flags == 'c' or self.flags == 'w':
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


#### legacy stuff to support the old "Container" class interface

namespace_classes = {}
class ContainerMeta(type):
    def __init__(cls, classname, bases, dict_):
        namespace_classes[cls] = cls.namespace_class
        return type.__init__(cls, classname, bases, dict_)
    def __call__(self, key, context, namespace, createfunc=None, expiretime=None, starttime=None, **kwargs):
        nscls = namespace_classes[self]
        return Value(key, context, namespace, nscls, createfunc=createfunc, expiretime=expiretime, starttime=starttime, **kwargs)

class Container(object):
    __metaclass__ = ContainerMeta
    namespace_class = NamespaceManager

class FileContainer(Container):
    namespace_class = FileNamespaceManager

class MemoryContainer(Container):
    namespace_class = MemoryNamespaceManager

class DBMContainer(Container):
    namespace_class = DBMNamespaceManager

DbmContainer = DBMContainer