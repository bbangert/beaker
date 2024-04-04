from beaker.cache import Cache
from . import base


class TestRedis(base.CacheManagerBaseTests):
    CACHE_ARGS = {
        'type': 'ext:rediscluster',
        'urls': 'redis://localhost:6379'
    }

    def test_client_reuse(self):
        cache1 = Cache('test1', **self.CACHE_ARGS)
        cli1 = cache1.namespace.client
        cache2 = Cache('test2', **self.CACHE_ARGS)
        cli2 = cache2.namespace.client
        self.assertTrue(cli1 is cli2)
