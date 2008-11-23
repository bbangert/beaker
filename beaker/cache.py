"""Cache object

The Cache object is used to manage a set of cache files and their
associated backend. The backends can be rotated on the fly by
specifying an alternate type when used.

"""
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
except InvalidCacheBackendError, e:
    clsmap['ext:memcached'] = e

try:
    import beaker.ext.database as database
    clsmap['ext:database'] = database.DatabaseNamespaceManager
except InvalidCacheBackendError, e:
    clsmap['ext:database'] = e

try:
    import beaker.ext.sqla as sqla
    clsmap['ext:sqla'] = sqla.SqlaNamespaceManager
except InvalidCacheBackendError, e:
    clsmap['ext:sqla'] = e

try:
    import beaker.ext.google as google
    clsmap['ext:google'] = google.GoogleNamespaceManager
except (InvalidCacheBackendError, SyntaxError), e:
    clsmap['ext:google'] = e


class Cache(object):
    """Front-end to the containment API implementing a data cache."""

    def __init__(self, namespace, type='memory', expiretime=None, starttime=None, **nsargs):
        try:
            cls = clsmap[type]
            if isinstance(cls, InvalidCacheBackendError):
                raise cls
        except KeyError:
            raise TypeError("Unknown cache implementation %r" % type)
            
        self.namespace = cls(namespace, **nsargs)
        self.expiretime = expiretime
        self.starttime = starttime
        self.nsargs = nsargs
        
    def put(self, key, value, **kw):
        self._get_value(key, **kw).set_value(value)
    set_value = put
    
    def get(self, key, **kw):
        return self._get_value(key, **kw).get_value()
    get_value = get
    
    def remove_value(self, key, **kw):
        mycontainer = self._get_value(key, **kw)
        if mycontainer.has_current_value():
            mycontainer.clear_value()

    def _get_value(self, key, **kw):
        if isinstance(key, unicode):
            key = key.encode('ascii', 'backslashreplace')

        if 'type' in kw:
            return self._legacy_get_value(key, **kw)

        kw.setdefault('expiretime', self.expiretime)
        kw.setdefault('starttime', self.starttime)
        
        return container.Value(key, self.namespace, **kw)
    
    def _legacy_get_value(self, key, type, **kw):
        expiretime = kw.pop('expiretime', self.expiretime)
        starttime = kw.pop('starttime', None)
        createfunc = kw.pop('createfunc', None)
        kwargs = self.nsargs.copy()
        kwargs.update(kw)
        c = Cache(self.namespace.namespace, type=type, **kwargs)
        return c._get_value(key, expiretime=expiretime, createfunc=createfunc, starttime=starttime)
    _legacy_get_value = util.deprecated(_legacy_get_value, "Specifying a 'type' and other namespace configuration with cache.get()/put()/etc. is depreacted.  Specify 'type' and other namespace configuration to cache_manager.get_cache() and/or the Cache constructor instead.")
    
    def clear(self):
        self.namespace.remove()
    
    # dict interface
    def __getitem__(self, key):
        return self.get(key)
    
    def __contains__(self, key):
        return self._get_value(key).has_current_value()
    
    def has_key(self, key):
        return key in self
    
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
