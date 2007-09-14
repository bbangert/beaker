import cPickle

from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import Synchronizer, _threading
from beaker.util import verify_directory, SyncDict

sa_version = None

try:
    import sqlalchemy as sa
    import sqlalchemy as types
    import sqlalchemy.pool as pool
    sa_version = '0.3'
except ImportError:
    from sqlalchemy import types
    raise InvalidCacheBackendError("Database cache backend requires the 'sqlalchemy' library")

if not hasattr(sa, 'BoundMetaData'):
    sa_version = '0.4'

class DatabaseNamespaceManager(NamespaceManager):
    metadatas = SyncDict(_threading.Lock(), {})
    tables = SyncDict(_threading.Lock(), {})
    
    def __init__(self, namespace, url=None, sa_opts=None, optimistic=False,
                 table_name='beaker_cache', data_dir=None, lock_dir=None,
                 **params):
        """Creates a database namespace manager
        
        ``sa_opts``
            A dictionary of SQLAlchemy keyword options to initialize the engine
            with.
        ``optimistic``
            Use optimistic session locking, note that this will result in an
            additional select when updating a cache value to compare version
            numbers.
        ``table_name``
            The table name to use in the database for the cache.
        """
        NamespaceManager.__init__(self, namespace, **params)
        
        if sa_opts is None:
            sa_opts = params
        
        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter("data_dir or lock_dir is required")
        else:
            self.lock_dir = data_dir + "/container_db_lock"
        
        verify_directory(self.lock_dir)
        
        # Check to see if the table's been created before
        url = url or sa_opts['sa.url']
        table_key = url + table_name
        def make_cache():
            # Check to see if we have a connection pool open already
            meta_key = url + table_name
            def make_meta():
                if sa_version == '0.3':
                    if url.startswith('mysql') and not sa_opts:
                        sa_opts['poolclass'] = pool.QueuePool
                    engine = sa.create_engine(url, **sa_opts)
                    meta = sa.BoundMetaData(engine)
                else:
                    engine = sa.engine_from_config(sa_opts, 'sa.')
                    meta = sa.MetaData()
                    meta.bind = engine
                return meta
            meta = DatabaseNamespaceManager.metadatas.get(meta_key, make_meta)
            # Create the table object and cache it now
            cache = sa.Table(table_name, meta,
                             sa.Column('id', types.Integer, primary_key=True),
                             sa.Column('namespace', types.String(255), nullable=False),
                             sa.Column('key', types.String(255), nullable=False),
                             sa.Column('value', types.BLOB(), nullable=False),
                             #sa.UniqueConstraint('namespace', 'key')
            )
            cache.create(checkfirst=True)
            return cache
        self._dict = None
        self.cache = DatabaseNamespaceManager.tables.get(table_key, make_cache)
    
    # The database does its own locking.  override our own stuff
    def do_acquire_read_lock(self): pass
    def do_release_read_lock(self): pass
    def do_acquire_write_lock(self, wait = True): return True
    def do_release_write_lock(self): pass

    # override open/close to do nothing, keep the connection open as long
    # as possible
    def open(self, *args, **params):pass
    def close(self, *args, **params):pass
    
    def _load_data(self):
        cache = self.cache
        self._dict = {}
        result = sa.select([cache.c.key, cache.c.value, cache.c.id], 
                           cache.c.namespace==self.namespace
                          ).execute()
        for row in result:
            self._dict[row['key']] = (row['value'], row['id'])
    
    def __getitem__(self, key):
        if self._dict is None:
            self._load_data()
        if key in self._dict:
            try:
                return cPickle.loads(str(self._dict[key][0]))
            except cPickle.UnpicklingError:
                return KeyError(key)
        else:
            raise KeyError(key)
        
    def __contains__(self, key):
        if self._dict is None:
            self._load_data()
        return key in self._dict

    def has_key(self, key):
        if self._dict is None:
            self._load_data()
        return key in self._dict

    def __setitem__(self, key, value):
        if self._dict is None:
            self._load_data()
        cache = self.cache
        
        if key in self._dict:
            id = self._dict[key][1]
        else:
            id = None
        
        value = cPickle.dumps(value)
        if id:
            cache.update(cache.c.id==id).execute(value=value)
        else:
            cache.insert().execute(namespace=self.namespace, key=key,
                                    value=value)
        self._dict[key] = value
    
    def __delitem__(self, key):
        cache = self.cache
        cache.delete(sa.and_(cache.c.namespace==self.namespace, 
                             cache.c.key==key)).execute()
        del self._dict[key]

    def do_remove(self):
        cache = self.cache
        cache.delete(cache.c.namespace==self.namespace).execute()
        self._dict = None

    def keys(self):
        if self._dict is None:
            self._load_data()
        return self._dict.keys()

class DatabaseContainer(Container):

    def do_init(self, data_dir=None, lock_dir=None, **params):
        self.funclock = None

    def create_namespace(self, namespace, url, **params):
        return DatabaseNamespaceManager(namespace, url, **params)
    create_namespace = classmethod(create_namespace)

    def lock_createfunc(self, wait = True):
        if self.funclock is None:
            self.funclock = Synchronizer(identifier =
"databasecontainer/funclock/%s" % self.namespacemanager.namespace,
use_files = True, lock_dir = self.namespacemanager.lock_dir)

        return self.funclock.acquire_write_lock(wait)

    def unlock_createfunc(self):
        self.funclock.release_write_lock()
