import os
import sys
import re
import inspect

from setuptools import setup, find_packages

py_version = sys.version_info[:2]
here = os.path.abspath(os.path.dirname(__file__))
v = open(os.path.join(here, 'beaker', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

try:
    README = open(os.path.join(here, 'README.rst')).read()
except IOError:
    README = ''


INSTALL_REQUIRES = []
if not hasattr(inspect, 'signature'):
    # On Python 2.6, 2.7 and 3.2 we need funcsigs dependency
    INSTALL_REQUIRES.append('funcsigs')


TESTS_REQUIRE = ['nose', 'webtest', 'Mock', 'pycrypto']

if py_version == (3, 2):
    TESTS_REQUIRE.append('coverage < 4.0')
else:
    TESTS_REQUIRE.append('coverage')

if not sys.platform.startswith('java') and not sys.platform == 'cli':
    TESTS_REQUIRE.extend(['SQLALchemy'])
    try:
        import sqlite3
    except ImportError:
        TESTS_REQUIRE.append('pysqlite')

setup(name='Beaker',
      version=VERSION,
      description="A Session and Caching library with WSGI Middleware",
      long_description=README,
      classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Environment :: Web Environment',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python',
      'Programming Language :: Python :: 2.6',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.2',
      'Programming Language :: Python :: 3.3',
      'Programming Language :: Python :: 3.4',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Internet :: WWW/HTTP :: WSGI',
      'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
      ],
      keywords='wsgi myghty session web cache middleware',
      author='Ben Bangert, Mike Bayer, Philip Jenvey',
      author_email='ben@groovie.org, pjenvey@groovie.org',
      url='http://beaker.rtfd.org/',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests', 'tests.*']),
      zip_safe=False,
      install_requires=INSTALL_REQUIRES,
      extras_require={
          'crypto': ['pycryptopp>=0.5.12'],
          'pycrypto': ['pycrypto'],
          'testsuite': [TESTS_REQUIRE]
      },
      test_suite='nose.collector',
      tests_require=TESTS_REQUIRE,
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
      """
)
