from .base import CacheManagerBaseTests


class TestMongoDB(CacheManagerBaseTests):
    CACHE_ARGS = {
        'url': 'localhost:27017/beaker_testdb'
    }