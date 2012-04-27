import os
import sys
import re

from setuptools import setup, find_packages

v = open(os.path.join(os.path.dirname(__file__), 'beaker', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

extra = {}
tests_require = ['nose', 'webtest', 'Mock']
pycryptopp = 'pycryptopp>=0.5.12'
if sys.version_info >= (3, 0):
    extra.update(
        use_2to3=True,
    )
else:
    tests_require.append(pycryptopp)

if not sys.platform.startswith('java') and not sys.platform == 'cli':
    tests_require.extend(['SQLALchemy'])
    try:
        import sqlite3
    except ImportError:
        tests_require.append('pysqlite')

setup(name='Beaker',
      version=VERSION,
      description="A Session and Caching library with WSGI Middleware",
      long_description="""\
Cache and Session Library
+++++++++++++++++++++++++

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
<http://pylonshq.com/>`_.


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
""",
      classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Web Environment',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python',
      'Programming Language :: Python :: 2.4',
      'Programming Language :: Python :: 2.5',
      'Programming Language :: Python :: 2.6',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.2',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Internet :: WWW/HTTP :: WSGI',
      'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
      ],
      keywords='wsgi myghty session web cache middleware',
      author='Ben Bangert, Mike Bayer, Philip Jenvey',
      author_email='ben@groovie.org, pjenvey@groovie.org',
      url='http://beaker.rtfd.org/',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      zip_safe=False,
      install_requires=[],
      extras_require={
          'crypto':[pycryptopp]
      },
      test_suite='nose.collector',
      tests_require=tests_require,
      entry_points="""
          [paste.filter_factory]
          beaker_session = beaker.middleware:session_filter_factory

          [paste.filter_app_factory]
          beaker_session = beaker.middleware:session_filter_app_factory

          [beaker.backends]
          database = beaker.ext.database:DatabaseNamespaceManager
          memcached = beaker.ext.memcached:MemcachedNamespaceManager
          google = beaker.ext.google:GoogleNamespaceManager
          sqla = beaker.ext.sqla:SqlaNamespaceManager
      """,
      **extra
)
