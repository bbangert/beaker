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
        
        self.mc = MemcachedNamespaceManager.clients.get(url, 
            lambda: memcache.Client(url.split(';'), debug=0))

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
        ns_key = self.namespace + '_' + key.replace(' ', '\302\267')
        all_key = self.namespace + ':keys'
        keys = [ns_key, all_key]
        key_dict = self.mc.get_multi(keys)
        if ns_key not in key_dict:
            raise KeyError(key)
        return key_dict[ns_key]

    def __contains__(self, key):
        return self.has_key(key)

    def has_key(self, key):
        ns_key = self.namespace + '_' + key.replace(' ', '\302\267')
        all_key = self.namespace + ':keys'
        keys = [ns_key, all_key]
        key_dict = self.mc.get_multi(keys)
        return ns_key in key_dict

    def __setitem__(self, key, value):
        key = key.replace(' ', '\302\267')
        keys = self.mc.get(self.namespace + ':keys')
        if keys is None:
            keys = {}
        keys[key] = True
        self.mc.set(self.namespace + ':keys', keys)
        self.mc.set(self.namespace + "_" + key, value)

    def __delitem__(self, key):
        cache_key = key.replace(' ', '\302\267')
        ns_key = self.namespace + '_' + cache_key
        all_key = self.namespace + ':keys'
        keys = [ns_key, all_key]
        key_dict = self.mc.get_multi(keys)
        if ns_key in key_dict:
            self.mc.delete(ns_key)
            mem_keys = key_dict.get(all_key, {})
            if cache_key in mem_keys:
                del mem_keys[cache_key]
                self.mc.set(all_key, mem_keys)
        else:
            raise KeyError

    def do_remove(self):
        keys = self.mc.get(self.namespace + ':keys')
        if keys is not None:
            delete_keys = [self.namespace + '_' + x for x in keys]
            delete_keys.append(self.namespace + ':keys')
            self.mc.delete_multi(delete_keys)
    
    def keys(self):
        keys = self.mc.get(self.namespace + ':keys')
        if keys is None:
            return []
        else:
            return [x.replace('\302\267', ' ') for x in keys.keys()]

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

