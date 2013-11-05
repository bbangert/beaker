.. _configuration:

=============
Configuration
=============

Beaker can be configured several different ways, depending on how it is to be
used.  The most recommended style is to use a dictionary of preferences that
are to be passed to either the :class:`~beaker.middleware.SessionMiddleware` or
the :class:`~beaker.cache.CacheManager`.

Since both Beaker's sessions and caching use the same back-end container
storage system, there's some options that are applicable to both of them in
addition to session and cache specific configuration.

Most options can be specified as a string (necessary to config options that
are setup in INI files), and will be coerced to the appropriate value. Only
datetime's and timedelta's cannot be coerced and must be the actual objects.

Frameworks using Beaker usually allow both caching and sessions to be
configured in the same spot, Beaker assumes this condition as well and
requires options for caching and sessions to be prefixed appropriately.

For example, to configure the ``cookie_expires`` option for Beaker sessions
below, an appropriate entry in a `Pylons`_ INI file would be::

    # Setting cookie_expires = true causes Beaker to omit the
    # expires= field from the Set-Cookie: header, signaling the cookie 
    # should be discarded when the browser closes.
    beaker.session.cookie_expires = true

.. note::

    When using the options in a framework like `Pylons`_ or `TurboGears2`_, these
    options must be prefixed by ``beaker.``, for example in a `Pylons`_ INI file::

        beaker.session.data_dir = %(here)s/data/sessions/data
        beaker.session.lock_dir = %(here)s/data/sessions/lock

Or when using stand-alone with the :class:`~beaker.middleware.SessionMiddleware`:

.. code-block:: python

    from beaker.middleware import SessionMiddleware

    session_opts = {
        'session.cookie_expires': True
    }

    app = SomeWSGIAPP()
    app = SessionMiddleware(app, session_opts)


Or when using the :class:`~beaker.cache.CacheManager`:

.. code-block:: python

    from beaker.cache import CacheManager
    from beaker.util import parse_cache_config_options

    cache_opts = {
        'cache.type': 'file',
        'cache.data_dir': '/tmp/cache/data',
        'cache.lock_dir': '/tmp/cache/lock'
    }

    cache = CacheManager(**parse_cache_config_options(cache_opts))

.. note::

    When using the CacheManager directly, all dict options must be run through the
    :func:`beaker.util.parse_cache_config_options` function to ensure they're valid
    and of the appropriate type.


Options For Sessions and Caching
================================

data_dir (**optional**, string)
    Used with any back-end that stores its data in physical files, such as the
    dbm or file-based back-ends. This path should be an absolute path to the
    directory that stores the files.

lock_dir (**required**, string)
    Used with every back-end, to coordinate locking. With caching, this lock
    file is used to ensure that multiple processes/threads aren't attempting
    to re-create the same value at the same time (The :term:`Dog-Pile Effect`)

memcache_module (**optional**, string)
    One of the names ``memcache``, ``cmemcache``, ``pylibmc``, or ``auto``.
    Default is ``auto``.  Specifies which memcached client library should
    be imported when using the ext:memcached backend.  If left at its
    default of ``auto``, ``pylibmc`` is favored first, then ``cmemcache``,
    then ``memcache``.  New in 1.5.5.

type (**required**, string)
    The name of the back-end to use for storing the sessions or cache objects.

    Available back-ends supplied with Beaker: ``file``, ``dbm``, ``memory``,
    ``ext:memcached``, ``ext:database``, ``ext:google``

    For sessions, the additional type of ``cookie`` is available which
    will store all the session data in the cookie itself. As such, size
    limitations apply (4096 bytes).

    Some of these back-ends require the url option as listed below.

webtest_varname (**optional**, string)
    The name of the attribute to use when stashing the session object into
    the environ for use with WebTest. The name provided here is where the 
    session object will be attached to the WebTest TestApp return value.

url (**optional**, string)
    URL is specific to use of either ext:memcached or ext:database. When using
    one of those types, this option is **required**.

    When used with ext:memcached, this should be either a single, or
    semi-colon separated list of memcached servers::

        session_opts = {
            'session.type': 'ext:memcached',
            'session.url': '127.0.0.1:11211',
        }

    When used with ext:database, this should be a valid `SQLAlchemy`_ database
    string.


Session Options
===============

The Session handling takes a variety of additional options relevant to how it
stores session id's in cookies, and when using the optional encryption.

auto (**optional**, bool)
    When set to True, the session will save itself anytime it is accessed
    during a request, negating the need to issue the 
    :meth:`~beaker.session.Session.save` method.

    Defaults to False.

cookie_expires (**optional**, bool, datetime, timedelta, int)
    Determines when the cookie used to track the client-side of the session
    will expire. When set to a boolean value, it will either expire at the
    end of the browsers session, or never expire.

    Setting to a datetime forces a hard ending time for the session (generally
    used for setting a session to a far off date).
    
    Setting to an integer will result in the cookie being set to expire in
    that many seconds. I.e. a value of ``300`` will result in the cookie being
    set to expire in 300 seconds.

    Defaults to never expiring.


.. _cookie_domain_config:

cookie_domain (**optional**, string)
    What domain the cookie should be set to. When using sub-domains, this
    should be set to the main domain the cookie should be valid for. For
    example, if a cookie should be valid under ``www.nowhere.com`` **and**
    ``files.nowhere.com`` then it should be set to ``.nowhere.com``.

    Defaults to the current domain in its entirety.

    Alternatively, the domain can be set dynamically on the session by
    calling, see :ref:`cookie_attributes`.

key (**required**, string)
    Name of the cookie key used to save the session under.

secret (**required**, string)
    Used with the HMAC to ensure session integrity. This value should
    ideally be a randomly generated string.

    When using in a cluster environment, the secret must be the same on
    every machine.

secure (**optional**, bool)
    Whether or not the session cookie should be marked as secure. When
    marked as secure, browsers are instructed to not send the cookie over
    anything other than an SSL connection.

timeout (**optional**, integer)
    Seconds until the session is considered invalid, after which it will
    be ignored and invalidated. This number is based on the time since
    the session was last accessed, not from when the session was created.

    Defaults to never expiring.


Encryption Options
------------------

These options should then be used *instead* of the ``secret``
option listed above.

encrypt_key (**required**, string)
    Encryption key to use for the AES cipher. This should be a fairly long
    randomly generated string.

validate_key (**required**, string)
    Validation key used to sign the AES encrypted data.

.. note::

	You may need to install additional libraries to use Beaker's
	cookie-based session encryption. See the :ref:`encryption` section for
	more information.

Cache Options
=============

For caching, options may be directly specified on a per-use basis with the
:meth:`~beaker.cache.CacheManager.cache` decorator, with the rest of these
options used as fallback should one of them not be specified in the call.

Only the ``lock_dir`` option is strictly required, unless using the file-based
back-ends as noted with the sessions.

expire (**optional**, integer)
    Seconds until the cache is considered old and a new value is created.


Cache Region Options
--------------------

.. _cache_region_options:

Starting in Beaker 1.3, cache regions are now supported. These can be thought
of as bundles of configuration options to apply, rather than specifying the
type and expiration on a per-usage basis.

enabled (**optional**, bool)
    Quick toggle to disable or enable caching across an entire application.

    This should generally be used when testing an application or in
    development when caching should be ignored.

    Defaults to True.


regions (**optional**, list, tuple)
    Names of the regions that are to be configured.

    For each region, all of the other cache options are valid and will
    be read out of the cache options for that key. Options that are not
    listed under a region will be used globally in the cache unless a
    region specifies a different value.

    For example, to specify two batches of options, one called ``long-term``,
    and one called ``short-term``::

        cache_opts = {
            'cache.data_dir': '/tmp/cache/data',
            'cache.lock_dir': '/tmp/cache/lock'
            'cache.regions': 'short_term, long_term',
            'cache.short_term.type': 'ext:memcached',
            'cache.short_term.url': '127.0.0.1.11211',
            'cache.short_term.expire': '3600',
            'cache.long_term.type': 'file',
            'cache.long_term.expire': '86400',


.. _Pylons: http://pylonshq.com/
.. _TurboGears2: http://turbogears.org/2.0/
.. _SQLAlchemy: http://www.sqlalchemy.org/
.. _pycryptopp: http://pypi.python.org/pypi/pycryptopp
