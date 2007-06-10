import sys

from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import _threading, Synchronizer
from beaker.util import verify_directory, SyncDict

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except ImportError:
        raise InvalidCacheBackendError("Memcached cache backend requires either the 'memcache' or 'cmemcache' library")

class MemcachedNamespaceManager(NamespaceManager):
    clients = SyncDict(_threading.Lock(), {})
    
    def __init__(self, namespace, url, data_dir=None, lock_dir=None, **params):
        NamespaceManager.__init__(self, namespace, **params)
        
        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        else:
            self.lock_dir = data_dir + "/container_mcd_lock"
        
        verify_directory(self.lock_dir)            
        
        self.mc = MemcachedNamespaceManager.clients.get(url, lambda: memcache.Client(url.split(';'), debug=0))

    # memcached does its own locking.  override our own stuff
    def do_acquire_read_lock(self): pass
    def do_release_read_lock(self): pass
    def do_acquire_write_lock(self, wait = True): return True
    def do_release_write_lock(self): pass

    # override open/close to do nothing, keep memcache connection open as long
    # as possible
    def open(self, *args, **params):pass
    def close(self, *args, **params):pass

    def __getitem__(self, key):
        value = self.mc.get(self.namespace + "_" + key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key):
        return self.mc.get(self.namespace + "_" + key) is not None

    def has_key(self, key):
        return self.mc.get(self.namespace + "_" + key) is not None

    def __setitem__(self, key, value):
        keys = self.mc.get(self.namespace + ':keys')
        if keys is None:
            keys = {}
        keys[key] = True
        self.mc.set(self.namespace + ':keys', keys)
        self.mc.set(self.namespace + "_" + key, value)

    def __delitem__(self, key):
        keys = self.mc.get(self.namespace + ':keys')
        try:
            del keys[key]
            self.mc.delete(self.namespace + "_" + key)
            self.mc.set(self.namespace + ':keys', keys)
        except KeyError:
            raise

    def do_remove(self):
        keys = self.mc.get(self.namespace + ':keys')
        if keys is not None:
            for key in keys:
                self.mc.delete(self.namespace + '_' + key)
            self.mc.delete(self.namespace + ':keys')
    
    def keys(self):
        keys = self.mc.get(self.namespace + ':keys')
        if keys is None:
            return []
        else:
            return keys.keys()

class MemcachedContainer(Container):

    def do_init(self, data_dir=None, lock_dir=None, **params):
        self.funclock = None

    def create_namespace(self, namespace, url, **params):
        return MemcachedNamespaceManager(namespace, url, **params)
    create_namespace = classmethod(create_namespace)

    def lock_createfunc(self, wait = True):
        if self.funclock is None:
            self.funclock = Synchronizer(identifier =
"memcachedcontainer/funclock/%s" % self.namespacemanager.namespace,
use_files = True, lock_dir = self.namespacemanager.lock_dir)

        return self.funclock.acquire_write_lock(wait)

    def unlock_createfunc(self):
        self.funclock.release_write_lock()

