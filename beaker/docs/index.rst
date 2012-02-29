Beaker Documentation
====================

Beaker is a library for caching and sessions for use with web applications and
stand-alone Python scripts and applications. It comes with WSGI middleware for
easy drop-in use with WSGI based web applications, and caching decorators for
ease of use with any Python based application.

* **Lazy-Loading Sessions**: No performance hit for having sessions active in a request unless they're actually used
* **Performance**: Utilizes a multiple-reader / single-writer locking system to prevent the Dog Pile effect when caching.
* **Mulitple Back-ends**: File-based, DBM files, memcached, memory, and database (via SQLAlchemy) back-ends available for sessions and caching
* **Cookie-based Sessions**: SHA-1 signatures with optional AES encryption for client-side cookie-based session storage
* **Flexible Caching**: Data can be cached per function to different back-ends, with different expirations, and different keys
* **Extensible Back-ends**: Add more backends using setuptools entrypoints to support new back-ends.

.. toctree::
   :maxdepth: 2

   configuration
   sessions
   caching

.. toctree::
   :maxdepth: 1

   changes


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :ref:`glossary`

Module Listing
--------------

.. toctree::
    :maxdepth: 2

    modules/cache
    modules/container
    modules/middleware
    modules/session
    modules/synchronization
    modules/util
    modules/database
    modules/google
    modules/memcached
    modules/sqla
    modules/pbkdf2


