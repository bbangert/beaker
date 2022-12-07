from beaker._compat import pickle

import logging
import pickle
from datetime import datetime

from beaker.container import OpenResourceNamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter
from beaker.synchronization import file_synchronizer, null_synchronizer
from beaker.util import verify_directory, SyncDict
from beaker.ext.sqla import SqlaNamespaceManager

log = logging.getLogger(__name__)

sa = None
types = None


class DatabaseNamespaceManager(SqlaNamespaceManager):

    @classmethod
    def _init_dependencies(cls):
        SqlaNamespaceManager._init_dependencies()

        global sa, types
        if sa is not None:
            return
        # SqlaNamespaceManager will already error
        import sqlalchemy as sa
        from sqlalchemy import types

    def __init__(self, namespace, url=None, sa_opts=None, table_name='beaker_cache', 
                 data_dir=None, lock_dir=None, schema_name=None, **params):
        """Creates a database namespace manager

        ``url``
            SQLAlchemy compliant db url
        ``sa_opts``
            A dictionary of SQLAlchemy keyword options to initialize the engine
            with.
        ``table_name``
            The table name to use in the database for the cache.
        ``schema_name``
            The schema name to use in the database for the cache.
        """
        if sa_opts is None:
            sa_opts = {}

        self.lock_dir = None

        if lock_dir:
            self.lock_dir = lock_dir
        elif data_dir:
            self.lock_dir = data_dir + "/container_db_lock"
        if self.lock_dir:
            verify_directory(self.lock_dir)

        # Check to see if the table's been created before
        sa_opts['sa.url'] = url = url or sa_opts['sa.url']
        table_key = url + table_name

        def make_table(engine):
            meta = sa.MetaData()
            meta.bind = engine
            cache_table = sa.Table(table_name, meta,
                                   sa.Column('id', types.Integer, primary_key=True),
                                   sa.Column('namespace', types.String(255), nullable=False),
                                   sa.Column('accessed', types.DateTime, nullable=False),
                                   sa.Column('created', types.DateTime, nullable=False),
                                   sa.Column('data', types.PickleType, nullable=False),
                                   sa.UniqueConstraint('namespace'),
                                   schema=schema_name if schema_name else meta.schema)
            cache_table.create(bind=engine, checkfirst=True)
            return cache_table

        engine = self.__class__.binds.get(url, lambda: sa.engine_from_config(sa_opts, 'sa.'))
        table = self.__class__.tables.get(table_key, lambda: make_table(engine))

        SqlaNamespaceManager.__init__(self, namespace, engine, table,
                                      data_dir=data_dir, lock_dir=lock_dir)


class DatabaseContainer(Container):
    namespace_manager = DatabaseNamespaceManager
