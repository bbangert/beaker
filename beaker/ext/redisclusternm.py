import os
import threading
import time
import pickle

from beaker.container import NamespaceManager

try:
    import redis
except ImportError:
    redis = None

from beaker.ext.redisnm import RedisNamespaceManager, RedisSynchronizer
from beaker._compat import string_type


class RedisClusterNamespaceManager(RedisNamespaceManager):
    """Provides the :class:`.NamespaceManager` API over Redis cluster.

    Provided ``urls`` can be both multiple redis connection strings separated by a comma or
    an already existing RedisCluster instance.

    Unlike a StrictRedis connection string, a RedisCluster one does not support
    database indicators, it is zero by default.

    Example: `redis://node-1:7001,redis://node-2:7002`

    Additional options can be passed in kwargs (e.g. `username="redis", password="secure_password"`).

    The data will be stored into redis keys, with their name
    starting with ``beaker_cache:``.
    """

    def __init__(self, namespace, urls, timeout=None, **kwargs):
        super(RedisNamespaceManager, self).__init__(namespace)
        self.lock_dir = None  # Redis uses redis itself for locking.
        self.timeout = timeout
        self.nodes = []
        self.options = kwargs

        if redis is None:
            raise RuntimeError('redis is not available')

        if isinstance(urls, string_type):
            for url in urls.split(','):
                url_options = redis.connection.parse_url(url)
                if 'db' in url_options:
                    raise redis.exceptions.RedisClusterException(
                        "A ``db`` querystring option can only be 0 in cluster mode"
                    )
                self.nodes.append(redis.cluster.ClusterNode(
                    host=url_options.get('host'),
                    port=url_options.get('port')
                ))
            self.client = RedisClusterNamespaceManager.clients.get(
                urls, redis.cluster.RedisCluster, startup_nodes=self.nodes, **kwargs
            )
        else:
            self.client = urls

    def get_creation_lock(self, key):
        return RedisClusterSynchronizer(self._format_key(key), self.client, self.nodes, **self.options)


class RedisClusterSynchronizer(RedisSynchronizer):
    """Synchronizer based on redis cluster.

    Provided ``urls`` can be both multiple redis connection strings separated by a comma or
    an already existing RedisCluster instance.

    Unlike a StrictRedis connection string, a RedisCluster one does not support
    database indicators, it is zero by default.

    Example: ``redis://node-1:7001,redis://node-2:7002,

    This Synchronizer only supports 1 reader or 1 writer at time, not concurrent readers.
    """
    RELEASE_LOCK_LUA = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
    """

    def __init__(self, identifier, urls, nodes=None, **kwargs):
        super(RedisSynchronizer, self).__init__()
        self.identifier = 'beaker_lock:%s' % identifier
        if isinstance(urls, string_type):
            self.client = RedisClusterNamespaceManager.clients.get(
                urls, redis.cluster.RedisCluster, startup_nodes=nodes, **kwargs
            )
        else:
            self.client = urls
        self._release_lock = self.client.register_lua(self.RELEASE_LOCK_LUA)

    def do_release_write_lock(self):
        identifier = self.identifier
        owner_id = self._get_owner_id()
        self._release_lock(keys=[identifier], args=[owner_id])