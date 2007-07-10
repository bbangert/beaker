import warnings
import beaker.container as container
from beaker.exceptions import InvalidCacheBackendError
from beaker.util import coerce_cache_params
import beaker.util as util

try:
    from paste.registry import StackedObjectProxy
    beaker_cache = StackedObjectProxy(name="Cache Manager")
except:
    beaker_cache = None

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

class Cache(object):
    """Front-end to the containment API implementing a data cache."""
    def __init__(self, namespace, **kwargs):
        self.namespace = namespace
        self.context = container.ContainerContext()
        self._containers = {}
        self.kwargs = kwargs
        self.kwargs.setdefault('type', 'memory')
    
    def put(self, key, value, **kwargs):
        kw = self.kwargs
        kw.update(kwargs)
        kw.setdefault('type', 'memory')
        self._get_container(key, **kw).set_value(value)
    set_value = put
    
    def get(self, key, **kwargs):
        kw = self.kwargs
        kw.update(kwargs)
        kwargs.setdefault('type', 'memory')
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

class CacheMiddleware(object):
    deprecated = True
    cache = beaker_cache
    
    def __init__(self, app, config=None, environ_key='beaker.cache', **kwargs):
        """Initialize the Cache Middleware
        
        The Cache middleware will make a Cache instance available every request
        under the ``environ['beaker.cache']`` key by default. The location in
        environ can be changed by setting ``environ_key``.
        
        ``config``
            dict  All settings should be prefixed by 'cache.'. This method of
            passing variables is intended for Paste and other setups that
            accumulate multiple component settings in a single dictionary. If
            config contains *no cache. prefixed args*, then *all* of the config
            options will be used to intialize the Cache objects.
        
        ``environ_key``
            Location where the Cache instance will keyed in the WSGI environ
        
        ``**kwargs``
            All keyword arguments are assumed to be cache settings and will
            override any settings found in ``config``
        """
        if self.deprecated:
            warnings.warn('CacheMiddleware is moving to beaker.middleware in '
                          '0.8', DeprecationWarning, 2)
        
        self.app = app
        config = config or {}
        
        # Load up the default params
        self.options= dict(type='memory', data_dir=None, timeout=None, 
                           log_file=None)
        
        # Pull out any config args starting with beaker cache. if there are any
        for dct in [config, kwargs]:
            for key, val in dct.iteritems():
                if key.startswith('beaker.cache.'):
                    self.options[key[13:]] = val
                if key.startswith('cache.'):
                    self.options[key[6:]] = val
                if key.startswith('cache_'):
                    warnings.warn('Cache options should start with cache. '
                                  'instead of cache_', DeprecationWarning, 2)
                    self.options[key[6:]] = val
        
        # Coerce and validate cache params
        coerce_cache_params(self.options)
        
        # Assume all keys are intended for cache if none are prefixed with 'cache.'
        if not self.options and config:
            self.options = config
        
        self.options.update(kwargs)
        self.cache_manager = CacheManager(**self.options)
        self.environ_key = environ_key
    
    def __call__(self, environ, start_response):
        if environ.get('paste.registry'):
            environ['paste.registry'].register(self.cache, self.cache_manager)
        environ[self.environ_key] = self.cache_manager
        return self.app(environ, start_response)
