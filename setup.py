import os
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


TESTS_REQUIRE = ['pytest', 'pycryptodome', 'webtest', 'coverage', 'cryptography',
                 'sqlalchemy', 'pymongo', 'redis', 'python-memcached']


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
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.8',
      'Programming Language :: Python :: 3.9',
      'Programming Language :: Python :: 3.10',
      'Programming Language :: Python :: 3.11',
      'Programming Language :: Python :: 3.12',
      'Programming Language :: Python :: 3.13',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Internet :: WWW/HTTP :: WSGI',
      'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
      ],
      keywords='wsgi myghty session web cache middleware',
      author='Ben Bangert, Mike Bayer, Philip Jenvey, Alessandro Molina',
      author_email='ben@groovie.org, pjenvey@groovie.org, amol@turbogears.org',
      url='https://beaker.readthedocs.io/',
      license='BSD',
      license_files=['LICENSE'],
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests', 'tests.*']),
      python_requires='>=3.8',
      zip_safe=False,
      extras_require={
          'crypto': ['pycryptopp>=0.5.12'],
          'pycrypto': ['pycrypto'],
          'pycryptodome': ['pycryptodome'],
          'cryptography': ['cryptography'],
          'testsuite': [TESTS_REQUIRE]
      },
      test_suite='tests',
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
