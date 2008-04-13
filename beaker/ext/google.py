from __future__ import absolute_import
import cPickle
import logging
import re
from datetime import datetime

from beaker.container import NamespaceManager, Container
from beaker.exceptions import InvalidCacheBackendError, MissingCacheParameter

log = logging.getLogger(__name__)

try:
    from google.appengine.ext import db
except ImportError:
    raise InvalidCacheBackendError("Datastore cache backend requires the "
                                   "'google.appengine.ext' library")


class GoogleNamespaceManager(NamespaceManager):
    tables = {}
    
    def __init__(self, namespace, table_name='beaker_cache', **params):
        """Creates a datastore namespace manager"""
        NamespaceManager.__init__(self, namespace, **params)
        
        def make_cache():
            table_dict = dict(created=db.DateTimeProperty(),
                              accessed=db.DateTimeProperty(),
                              data=db.TextProperty())
            table = type(table_name, (db.Model,), table_dict)
            return table
        self.table_name = table_name
        self.cache = GoogleNamespaceManager.tables.setdefault(table_name, make_cache())
        self.hash = {}
        self._is_new = False
        self.loaded = False
        self.log_debug = logging.DEBUG >= log.getEffectiveLevel()
        
        # Google wants namespaces to start with letters, change the namespace
        # to start with a letter
        self.namespace = 'p%s' % self.namespace
    
    # datastore does its own locking (or does it? who knows).  override our
    # own stuff
    def do_acquire_read_lock(self): pass
    def do_release_read_lock(self): pass
    def do_acquire_write_lock(self, wait = True): return True
    def do_release_write_lock(self): pass

    def do_open(self, flags):
        # If we already loaded the data, don't bother loading it again
        if self.loaded:
            self.flags = flags
            return
        
        item = self.cache.get_by_key_name(self.namespace)
        
        if not item:
            self._is_new = True
            self.hash = {}
        else:
            self._is_new = False
            try:
                self.hash = cPickle.loads(str(item.data))
            except (IOError, OSError, EOFError, cPickle.PickleError):
                if self.log_debug:
                    log.debug("Couln't load pickle data, creating new storage")
                self.hash = {}
                self._is_new = True
        self.flags = flags
        self.loaded = True
    
    def do_close(self):
        if self.flags is not None and (self.flags == 'c' or self.flags == 'w'):
            if self._is_new:
                item = self.cache(key_name=self.namespace)
                item.data = cPickle.dumps(self.hash)
                item.created = datetime.now()
                item.accessed = datetime.now()
                item.put()
                self._is_new = False
            else:
                item = self.cache.get_by_key_name(self.namespace)
                item.data = cPickle.dumps(self.hash)
                item.accessed = datetime.now()
                item.put()
        self.flags = None
    
    def do_remove(self):
        item = self.cache.get_by_key_name(self.namespace)
        item.delete()
        self.hash = {}
        
        # We can retain the fact that we did a load attempt, but since the
        # file is gone this will be a new namespace should it be saved.
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
        

class GoogleContainer(Container):

    def do_init(self, data_dir=None, lock_dir=None, **params):
        self.funclock = None

    def create_namespace(self, namespace, url, **params):
        return GoogleNamespaceManager(namespace, url, **params)
    create_namespace = classmethod(create_namespace)

    def lock_createfunc(self, wait = True):
        pass

    def unlock_createfunc(self):
        pass
