import warnings
import beaker.container as container
from beaker.exceptions import InvalidCacheBackendError
from beaker.util import coerce_cache_params
import beaker.util as util

clsmap = {
          'memory':container.MemoryContainer,
          'dbm':container.DBMContainer,
          'file':container.FileContainer,
          }

try:
    import beaker.ext.memcached as memcached
    clsmap['ext:memcached'] = memcached.MemcachedContainer
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.database as database
    clsmap['ext:database'] = database.DatabaseContainer
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.sqla as sqla
    clsmap['ext:sqla'] = sqla.SQLAlchemyContainer
except InvalidCacheBackendError:
    pass

try:
    import beaker.ext.google as google
    clsmap['ext:google'] = google.GoogleContainer
except (InvalidCacheBackendError, SyntaxError):
    pass

class Cache(object):
    """Front-end to the containment API implementing a data cache."""
    def __init__(self, namespace, **kwargs):
        self.namespace = namespace
        self.context = container.ContainerContext()
        self._containers = {}
        self.kwargs = kwargs
        self.kwargs.setdefault('type', 'memory')
    
    def put(self, key, value, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        self._containers.pop(key, None)
        self._get_container(key, **kw).set_value(value)
    set_value = put
    
    def get(self, key, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return self._get_container(key, **kw).get_value()
    get_value = get
    
    def remove_value(self, key, **kwargs):
        mycontainer = self._get_container(key, **self.kwargs)
        if mycontainer.has_current_value():
            mycontainer.clear_value()

    def _get_container(self, key, type, **kwargs):
        if isinstance(key, unicode):
            key = key.encode('ascii', 'backslashreplace')
        mycontainer = self._containers.get(key)
        if not mycontainer:
            kw = self.kwargs.copy()
            kw.update(kwargs)
            mycontainer = clsmap[type](key, self.context, self.namespace, **kw)
            self._containers[key] = mycontainer
        return mycontainer
    
    def _get_namespace(self, **kwargs):
        type = kwargs['type']
        return self.context.get_namespace_manager(self.namespace, clsmap[type], **kwargs)
    
    def _get_namespaces(self):
        """return a collection of all distinct ``Namespace`` instances 
        referenced by this ``Cache``."""
        s = util.Set()
        s.add(self._get_namespace(**self.kwargs))
        for mycontainer in self._containers.values():
            s.add(mycontainer.namespacemanager)
        return s
    
    def clear(self):
        """clear this Cache's default namespace, as well as any other 
        Namespaces that have been referenced by this Cache."""
        for namespace in self._get_namespaces():
            namespace.remove()
        self._containers = {}
    
    # public dict interface
    def __getitem__(self, key):
        return self.get(key)
    
    def __contains__(self, key):
        return self.has_key(key)
    
    def has_key(self, key):
        mycontainer = self._get_container(key, **self.kwargs)
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
