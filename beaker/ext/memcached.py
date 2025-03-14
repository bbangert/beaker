from .._compat import PY2

from beaker.container import NamespaceManager, Container
from beaker.crypto.util import sha1
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer
from beaker.util import verify_directory, SyncDict, parse_memcached_behaviors
import warnings

MAX_KEY_LENGTH = 250

_client_libs = {}


def _load_client(name='auto'):
    if name in _client_libs:
        return _client_libs[name]

    def _cmemcache():
        global cmemcache
        import cmemcache
        warnings.warn("cmemcache is known to have serious "
                    "concurrency issues; consider using 'memcache' ")
        return cmemcache

    def _memcache():
        global memcache
        import memcache
        return memcache

    def _bmemcached():
        global bmemcached
        import bmemcached
        return bmemcached

    def _auto():
        for _client in (_cmemcache, _memcache, _bmemcached):
            try:
                return _client()
            except ImportError:
                pass
        else:
            raise InvalidCacheBackendError(
                    "Memcached cache backend requires one "
                    "of: 'pylibmc' or 'memcache' to be installed.")

    clients = {
        'cmemcache': _cmemcache,
        'memcache': _memcache,
        'bmemcached': _bmemcached,
        'auto': _auto
    }
    _client_libs[name] = clib = clients[name]()
    return clib


class MemcachedNamespaceManager(NamespaceManager):
    """Provides the :class:`.NamespaceManager` API over a memcache client library."""

    clients = SyncDict()

    def __init__(self, namespace, url,
                        memcache_module='auto',
                        data_dir=None, lock_dir=None,
                        **kw):
        NamespaceManager.__init__(self, namespace)

        _memcache_module = _load_client(memcache_module)

        if not url:
            raise MissingCacheParameter("url is required")

        self.lock_dir = None

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_mcd_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        self.mc = MemcachedNamespaceManager.clients.get(
                    (memcache_module, url),
                    _memcache_module.Client,
                    url.split(';'))

    def get_creation_lock(self, key):
        return file_synchronizer(
            identifier="memcachedcontainer/funclock/%s/%s" %
                    (self.namespace, key), lock_dir=self.lock_dir)

    def _format_key(self, key):
        if not isinstance(key, str):
            key = key.decode('ascii')
        formated_key = (self.namespace + '_' + key).replace(' ', '\302\267')
        if len(formated_key) > MAX_KEY_LENGTH:
            if not PY2:
                formated_key = formated_key.encode('utf-8')
            formated_key = sha1(formated_key).hexdigest()
        return formated_key

    def __getitem__(self, key):
        return self.mc.get(self._format_key(key))

    def __contains__(self, key):
        value = self.mc.get(self._format_key(key))
        return value is not None

    def has_key(self, key):
        return key in self

    def set_value(self, key, value, expiretime=None):
        if expiretime:
            self.mc.set(self._format_key(key), value, time=expiretime)
        else:
            self.mc.set(self._format_key(key), value)

    def __setitem__(self, key, value):
        self.set_value(key, value)

    def __delitem__(self, key):
        self.mc.delete(self._format_key(key))

    def do_remove(self):
        self.mc.flush_all()

    def keys(self):
        raise NotImplementedError(
                "Memcache caching does not "
                "support iteration of all cache keys")


class MemcachedContainer(Container):
    """Container class which invokes :class:`.MemcacheNamespaceManager`."""
    namespace_class = MemcachedNamespaceManager
