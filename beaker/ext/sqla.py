import cPickle
import logging
from datetime import datetime

from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import Synchronizer, _threading
from beaker.util import verify_directory, SyncDict

try:
    import sqlalchemy as sa
except ImportError:
    raise InvalidCacheBackendError('SQLAlchemy, which is required by this backend, is not installed')

log = logging.getLogger(__name__)

class SQLAlchemyNamespaceManager(NamespaceManager):
    binds = SyncDict(_threading.Lock(), {})
    tables = SyncDict(_threading.Lock(), {})

    def __init__(self, namespace, bind, table, data_dir=None, lock_dir=None,
                 **kwargs):
        """Create a namespace manager for use with a database table via
        SQLAlchemy.

        ``bind``
            SQLAlchemy ``Engine`` or ``Connection`` object

        ``table``
            SQLAlchemy ``Table`` object in which to store namespace data.
            This should usually be something created by ``make_cache_table``.
        """
        NamespaceManager.__init__(self, namespace, **kwargs)

        if lock_dir is not None:
            self.lock_dir = lock_dir
        elif data_dir is None:
            raise MissingCacheParameter('data_dir or lock_dir is required')
        else:
            self.lock_dir = data_dir + '/container_db_lock'

        verify_directory(self.lock_dir)

        self.bind = self.__class__.binds.get(str(bind.url), lambda: bind)
        self.table = self.__class__.tables.get('%s:%s' % (bind.url, table.name),
                                               lambda: table)
        self.hash = {}
        self._is_new = False
        self.loaded = False

    def do_acquire_read_lock(self):
        pass

    def do_release_read_lock(self):
        pass

    def do_acquire_write_lock(self, wait=True):
        return True

    def do_release_write_lock(self):
        pass

    def do_open(self, flags):
        if self.loaded:
            self.flags = flags
            return
        select = sa.select([self.table.c.data],
                           (self.table.c.namespace == self.namespace))
        result = self.bind.execute(select).fetchone()
        if not result:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = cPickle.loads(str(result['data']))
            except (IOError, OSError, EOFError, cPickle.PickleError):
                log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True

    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            data = cPickle.dumps(self.hash)
            if self._is_new:
                insert = self.table.insert()
                self.bind.execute(insert, namespace=self.namespace, data=data,
                                  accessed=datetime.now(),
                                  created=datetime.now())
                self._is_new = False
            else:
                update = self.table.update(self.table.c.namespace == self.namespace)
                self.bind.execute(update, data=data, accessed=datetime.now())
        self.flags = None

    def do_remove(self):
        delete = self.table.delete(self.table.c.namespace == self.namespace)
        self.bind.execute(delete)
        self.hash = {}
        self._is_new = True

    def __getitem__(self, key):
        return self.hash[key]

    def __contains__(self, key):
        return self.hash.has_key(key)

    def __setitem__(self, key, value):
        self.hash[key] = value

    def __delitem__(self, key):
        del self.hash[key]

    def keys(self):
        return self.hash.keys()


class SQLAlchemyContainer(Container):
    def do_init(self, data_dir=None, lock_dir=None, **kwargs):
        self.funclock = None

    def create_namespace(self, namespace, bind, table, **kwargs):
        return SQLAlchemyNamespaceManager(namespace, bind, table, **kwargs)

    create_namespace = classmethod(create_namespace)

    def lock_createfunc(self, wait=True):
        if self.funclock is None:
            identifier = 'sqlalchemycontainer/funclock/%s' \
                % self.namespacemanager.namespace
            self.funclock = Synchronizer(identifier, True,
                                         self.namespacemanager.lock_dir)
        return self.funclock.acquire_write_lock(wait)

    def unlock_createfunc(self):
        self.funclock.release_write_lock()


def make_cache_table(metadata, table_name='beaker_cache'):
    """Return a ``Table`` object suitable for storing cached values for the
    namespace manager.  Do not create the table."""
    return sa.Table(table_name, metadata,
                    sa.Column('namespace', sa.String(255), primary_key=True),
                    sa.Column('accessed', sa.DateTime, nullable=False),
                    sa.Column('created', sa.DateTime, nullable=False),
                    sa.Column('data', sa.BLOB(), nullable=False))
