import sys

from setuptools import setup, find_packages

version = '1.0.2'

pycryptopp = 'pycryptopp>=0.3.0'
tests_require = ['nose', 'python-memcached', 'webtest']
if not sys.platform.startswith('java') and not sys.platform == 'cli':
    tests_require.extend([pycryptopp, 'SQLALchemy'])
    try:
        import sqlite3
    except ImportError:
        tests_require.append('pysqlite')

setup(name='Beaker',
      version=version,
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
<http://wiki.pylonshq.com/display/beaker/Home>`_.

Examples
========

Caching
-------

Basic Example::
    
    from beaker.cache import CacheManager
    cm = CacheManager(type='dbm', data_dir='./cache')
    
    cache = cm.get_cache('mytemplate')
    
    def somethingslow():
        # slow stuff
        db_lookups()
    
    # Get the value, this will create the cache copy the first time
    # and any time it expires (in seconds, so 3600 = one hour)
    result = mycache.get_value(day, createfunc=somethingslow, expiretime=3600)

Using WSGI::
    
    from beaker.middleware import CacheMiddleware
    
    def simple_app(environ, start_response):
        cache = environ['beaker.cache'].get_cache('testcache')
        try:
            value = cache.get_value('value')
        except KeyError:
            value = 0
        cache.set_value('value', value+1)
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['The current value is: %s' % cache.get_value('value')]
    
    app = CacheMiddleware(simple_app, type='dbm', data_dir='./cache')

Sessions
--------

Using WSGI::
    
    from beaker.middleware import SessionMiddleware
    
    def simple_app(environ, start_response):
        session = environ['beaker.session']
        if not session.has_key('value'):
            session['value'] = 0
        session['value'] += 1
        session.save()
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['The current value is: %d' % session['value']]
    
    wsgi_app = SessionMiddleware(simple_app, type='dbm', data_dir='./cache')

Source
======

The latest developer version is available in a `Mercurial repository
<https://www.knowledgetap.com/hg/beaker/archive/tip.tar.gz#egg=Beaker-dev>`_.
""",
      classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Web Environment',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ],
      keywords='wsgi myghty session web cache middleware',
      author='Ben Bangart, Mike Bayer, Philip Jenvey',
      author_email='ben@groovie.org, pjenvey@groovie.org',
      url='http://beaker.groovie.org',
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
      """,
)
