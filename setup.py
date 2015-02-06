import os
import sys
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
v = open(os.path.join(here, 'beaker', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

try:
    README = open(os.path.join(here, 'README.rst')).read()
except IOError:
    README = ''

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
      long_description=README,
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
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests', 'tests.*']),
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
