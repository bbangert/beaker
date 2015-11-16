=========================
Cache and Session Library
=========================

About
=====

Beaker is a web session and general caching library that includes WSGI
middleware for use in web applications.

As a general caching library, Beaker can handle storing for various times
any Python object that can be pickled with optional back-ends on a
fine-grained basis.

Beaker was built largely on the code from MyghtyUtils, then refactored and
extended with database support.

Beaker includes Cache and Session WSGI middleware to ease integration with
WSGI capable frameworks, and is automatically used by `Pylons
<http://www.pylonsproject.org/projects/pylons-framework/about>`_ and 
`TurboGears <http://www.turbogears.org/>`_.


Features
========

* Fast, robust performance
* Multiple reader/single writer lock system to avoid duplicate simultaneous
  cache creation
* Cache back-ends include dbm, file, memory, memcached, and database (Using
  SQLAlchemy for multiple-db vendor support)
* Signed cookie's to prevent session hijacking/spoofing
* Cookie-only sessions to remove the need for a db or file backend (ideal
  for clustered systems)
* Extensible Container object to support new back-ends
* Cache's can be divided into namespaces (to represent templates, objects,
  etc.) then keyed for different copies
* Create functions for automatic call-backs to create new cache copies after
  expiration
* Fine-grained toggling of back-ends, keys, and expiration per Cache object


Documentation
=============

Documentation can be found on the `Official Beaker Docs site
<http://beaker.groovie.org/>`_.


Source
======

The latest developer version is available in a `github repository
<https://github.com/bbangert/beaker>`_.

Contributing
============

Bugs can be filed on github, **should be accompanied by a test case** to
retain current code coverage, and should be in a Pull request when ready to be
accepted into the beaker code-base.
