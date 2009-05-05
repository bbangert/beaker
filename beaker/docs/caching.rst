.. _caching:

=======
Caching
=======

About
=====

Beaker's caching system was originally based off the Perl Cache::Cache module,
which was ported for use in `Myghty`_. Beaker was then extracted from this
code, and has been substantially rewritten and modernized.

Several concepts still exist from this origin though. Beaker's caching (and
its sessions, though its behind the scenes) utilize the concept of 
:term:`NamespaceManager`, and :term:`Container` objects to handle storing
cached data.

Each back-end utilizes a customized version of each of these objects to handle
storing data appropriately depending on the type of the back-end.

The :class:`~beaker.cache.CacheManager` is responsible for getting the
appropriate NamespaceManager, which then stores the cached values. Each
namespace corresponds to a single ``thing`` that should be cached. Usually
a single ``thing`` to be cached might vary slightly depending on parameters,
for example a template might need several different copies of itself stored
depending on whether a user is logged in or not. Each one of these copies
is then ``keyed`` under the NamespaceManager and stored in a Container.

There are two schemes for using Beaker's caching, the first and more 
traditional style is the programmatic API. This exposes the namespace's
and retrieves a :class:`~beaker.cache.Cache` object that handles storing
keyed values in a NamespaceManager with Container objects.

The more elegant system, introduced in Beaker 1.3, is to use the
:ref:`cache decorators <decorator_api>`, these also support the
use of :term:`Cache Regions`.


Creating the CacheManager Instance
==================================

Before using Beaker's caching, an instance of the
:class:`~beaker.cache.CacheManager` class should be created. All of the
examples below assume that it has already been created.

Creating the cache instance::
    
    from beaker.cache import CacheManager
    from beaker.util import parse_cache_config_options

    cache_opts = {
        'cache.type': 'file',
        'cache.data_dir': '/tmp/cache/data',
        'cache.lock_dir': '/tmp/cache/lock'
    }

    cache = CacheManager(**parse_cache_config_options(cache_opts))

Additional configuration options are documented in the :ref:`Configuration`
section of the Beaker docs.


Programmatic API
================

.. _programmatic:

To store data for a cache value, first, a NamespaceManager has to be
retrieved to manage the keys for a ``thing`` to be cached::
    
    # Assuming that cache is an already created CacheManager instance
    tmpl_cache = cache.get_cache('mytemplate.html', expire=3600)

Individual values should be stored using a creation function, which will
be called anytime the cache has expired or a new copy needs to be made. The
creation function must not accept any arguments as it won't be called with
any. Options affecting the created value can be passed in by using closure
scope on the creation function::
    
    search_param = 'gophers'
    
    def get_results():
        # do something to retrieve data
        data = get_data(search_param)
        return data
    
    # Cache this function, based on the search_param, using the tmpl_cache
    # instance from the prior example
    results = tmpl_cache.get(key=search_param, createfunc=get_results)

All of the values for a particular namespace can be removed by calling the
:meth:`~beaker.cache.Cache.clear` method::
    
    tmpl_cache.clear()


Decorator API
=============

.. _decorator_api:

When using the decorator API, a namespace does not need to be specified and
will instead be created for you with the name of the module + the name of the
function that will have its output cached.

Since its possible that multiple functions in the same module might have the
same name, additional arguments can be provided to the decorators that will be
used in the namespace to prevent multiple functions from caching their values
in the same location.

For example::
    
    # Assuming that cache is an already created CacheManager instance
    @cache.cache('my_search_func', expire=3600)
    def get_results(search_param):
        # do something to retrieve data
        data = get_data(search_param)
        return data
    
    results = get_results('gophers')

The non-keyword arguments to the :meth:`~beaker.cache.CacheManager.cache`
method are the additional ones used to ensure this function's cache results
won't clash with another function in this module called ``get_results``.

The cache expire argument is specified as a keyword argument. Other valid
arguments to the :meth:`~beaker.cache.CacheManager.get_cache` method such
as ``type`` can also be passed in.

When using the decorator, the function to cache can have arguments, which will
be used as the key was in the :ref:`Programmatic API <programmatic>` for
the data generated.

.. warning::
    These arguments can **not** be keyword arguments.

Cache Regions
=============

Rather than having to specify the expiration, or toggle the type used for
caching different functions, commonly used cache parameters can be defined
as :term:`Cache Regions`. These user-defined regions than may be used
with the :meth:`~beaker.cache.CacheManager.region` decorator rather than
passing the configuration.

This can be useful if there are a few common cache schemes used by an
application that should be setup in a single place then used as appropriate
throughout the application.

Setting up cache region's is documented in the
:ref:`cache region options <cache_region_options>` section in
:ref:`configuration`.

Assuming a ``long_term`` and ``short_term`` region were setup, the 
:meth:`~beaker.cache.CacheManager.region` decorator can be used::
    
    @cache.region('short_term', 'my_search_func')
    def get_results(search_param):
        # do something to retrieve data
        data = get_data(search_param)
        return data
    
    results = get_results('gophers')



.. _Myghty: http://www.myghty.org/