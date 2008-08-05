from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except ImportError:
        raise InvalidCacheBackendError("Memcached cache backend requires either the 'memcache' or 'cmemcache' library")

class MemcachedNamespaceManager(NamespaceManager):
    clients = SyncDict()
    
    def __init__(self, namespace, url, data_dir=None, lock_dir=None, **params):
        NamespaceManager.__init__(self, namespace)
        
        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        else:
            self.lock_dir = data_dir + "/container_mcd_lock"
        
        verify_directory(self.lock_dir)            
        
        self.mc = MemcachedNamespaceManager.clients.get(url, 
            lambda: memcache.Client(url.split(';'), debug=0))

    def get_access_lock(self):
        return null_synchronizer()

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="memcachedcontainer/funclock/%s" % self.namespace,lock_dir = self.lock_dir)

    def open(self, *args, **params):
        pass
    def close(self, *args, **params):
        pass

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
    namespace_class = MemcachedNamespaceManager
