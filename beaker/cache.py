import beaker.container as container
from beaker.exceptions import InvalidCacheBackendError
import beaker.util as util

clsmap = {
          'memory':container.MemoryNamespaceManager,
          'dbm':container.DBMNamespaceManager,
          'file':container.FileNamespaceManager,
          }

try:
    import beaker.ext.memcached as memcached
    clsmap['ext:memcached'] = memcached.MemcachedNamespaceManager
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.database as database
    clsmap['ext:database'] = database.DatabaseNamespaceManager
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.sqla as sqla
    clsmap['ext:sqla'] = sqla.SqlaNamespaceManager
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.google as google
    clsmap['ext:google'] = google.GoogleNamespaceManager
except (InvalidCacheBackendError, SyntaxError):
    pass

class Cache(object):
    """Front-end to the containment API implementing a data cache."""
    def __init__(self, namespace, **kwargs):
        self.namespace = namespace
        self.context = container.ContainerContext()
        self._values = {}
        self.kwargs = kwargs
        self.kwargs.setdefault('type', 'memory')
    
    def put(self, key, value, **kwargs):
        self._values.pop(key, None)
        self._get_value(key, **kwargs).set_value(value)
    set_value = put
    
    def get(self, key, **kwargs):
        return self._get_value(key, **kwargs).get_value()
    get_value = get
    
    def remove_value(self, key, **kwargs):
        mycontainer = self._get_value(key, **kwargs)
        if mycontainer.has_current_value():
            mycontainer.clear_value()

    def _get_value(self, key, **kwargs):
        if isinstance(key, unicode):
            key = key.encode('ascii', 'backslashreplace')
            
        if not kwargs:
            value = self._values.get(key)
        else:
            value = None
            
        if not value:
            kw = self.kwargs.copy()
            kw.update(kwargs)
            type = kw.pop('type')
            self._values[key] = value = container.Value(key, self.context, self.namespace, clsmap[type], **kw)
        return value
    
    def _get_namespace(self, **kwargs):
        type = kwargs['type']
        return self.context.get_namespace(self.namespace, clsmap[type], **kwargs)
    
    def _get_namespaces(self):
        """return a collection of all distinct ``Namespace`` instances 
        referenced by this ``Cache``."""
        
        return util.Set(
            [v.namespacemanager for v in self._values.values()]).\
            union([self._get_namespace(**self.kwargs)])
    
    def clear(self):
        """clear this Cache's default namespace, as well as any other 
        Namespaces that have been referenced by this Cache."""
        for namespace in self._get_namespaces():
            namespace.remove()
        self._values = {}
    
    # public dict interface
    def __getitem__(self, key):
        return self.get(key)
    
    def __contains__(self, key):
        return self.has_key(key)
    
    def has_key(self, key):
        mycontainer = self._get_value(key)
        return mycontainer.has_current_value()
    
    def __delitem__(self, key):
        self.remove_value(key)
    
    def __setitem__(self, key, value):
        self.put(key, value)

class CacheManager(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.caches = {}
    
    def get_cache(self, name, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return self.caches.setdefault(name + str(kw), Cache(name, **kw))
