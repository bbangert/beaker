from . import base


class TestMongoDB(base.CacheManagerBaseTests):
    CACHE_ARGS = {
        'type': 'ext:mongodb',
        'url': 'mongodb://localhost:27017/beaker_testdb'
    }