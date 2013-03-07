.. _sessions:

========
Sessions
========

About
=====

Sessions provide a place to persist data in web applications, Beaker's session
system simplifies session implementation details by providing WSGI middleware
that handles them.

All cookies are signed with an HMAC signature to prevent tampering by the
client.

Lazy-Loading
------------

Only when a session object is actually accessed will the session be loaded
from the file-system, preventing performance hits on pages that don't use
the session.

Using
=====

The session object provided by Beaker's
:class:`~beaker.middleware.SessionMiddleware` implements a dict-style interface
with a few additional object methods. Once the SessionMiddleware is in place,
a session object will be made available as ``beaker.session`` in the WSGI
environ.

Getting data out of the session::

    myvar = session['somekey']

Testing for a value::

    logged_in = 'user_id' in session

Adding data to the session::

    session['name'] = 'Fred Smith'

Complete example using a basic WSGI app with sessions::

    from beaker.middleware import SessionMiddleware

    def simple_app(environ, start_response):
        # Get the session object from the environ
        session = environ['beaker.session']

        # Check to see if a value is in the session
        user = 'logged_in' in session

        # Set some other session variable
        session['user_id'] = 10

        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['User is logged in: %s' % user]

    # Configure the SessionMiddleware
    session_opts = {
        'session.type': 'file',
        'session.cookie_expires': True,
    }
    wsgi_app = SessionMiddleware(simple_app, session_opts)

.. note::
    This example does **not** actually save the session for the next request.
    Adding the :meth:`~beaker.session.Session.save` call explained below is
    required, or having the session set to auto-save.

.. _cookie_attributes:

Session Attributes / Keys
-------------------------

Sessions have several special attributes that can be used as needed by an
application.

* id - Unique 40 char SHA-generated session ID
* last_accessed - The last time the session was accessed before the current
  access, will be None if the session was just made

There's several special session keys populated as well:

* _accessed_time - Current accessed time of the session, when it was loaded
* _creation_time - When the session was created


Saving
======

Sessions can be saved using the :meth:`~beaker.session.Session.save` method
on the session object::

    session.save()

.. warning::

    Beaker relies on Python's pickle module to pickle data objects for storage
    in the session. Objects that cannot be pickled should **not** be stored in
    the session.

This flags a session to be saved, and it will be stored on the chosen back-end
at the end of the request.

If it's necessary to immediately save the session to the back-end, the
:meth:`~beaker.session.SessionObject.persist` method should be used::

    session.persist()

This is not usually the case however, as a session generally should not be
saved should something catastrophic happen during a request.

**Order Matters**: When using the Beaker middleware, you **must call save before
the headers are sent to the client**. Since Beaker's middleware watches for when
the ``start_response`` function is called to know that it should add its cookie
header, the session must be saved before it is called.

Keep in mind that Response objects in popular frameworks (WebOb, Werkzeug,
etc.) call start_response immediately, so if you are using one of those
objects to handle your Response, you must call .save() before the Response
object is called::

    # this would apply to WebOb and possibly others too
    from werkzeug.wrappers import Response

    # this will work
    def sessions_work(environ, start_response):
        environ['beaker.session']['count'] += 1
        resp = Response('hello')
        environ['beaker.session'].save()
        return resp(environ, start_response)

    # this will not work
    def sessions_broken(environ, start_response):
        environ['beaker.session']['count'] += 1
        resp = Response('hello')
        retval = resp(environ, start_response)
        environ['beaker.session'].save()
        return retval



Auto-save
---------

Saves can be done automatically by setting the ``auto`` configuration option
for sessions. When set, calling the :meth:`~beaker.session.Session.save` method
is no longer required, and the session will be saved automatically anytime it is
accessed during a request.


Deleting
========

Calling the :meth:`~beaker.session.Session.delete` method deletes the session
from the back-end storage and sends an expiration on the cookie requesting the
browser to clear it::

    session.delete()

This should be used at the end of a request when the session should be deleted
and will not be used further in the request.

If a session should be invalidated, and a new session created and used during
the request, the :meth:`~beaker.session.Session.invalidate` method should be
used::

    session.invalidate()

Removing Expired/Old Sessions
-----------------------------

Beaker does **not** automatically delete expired or old cookies on any of its
back-ends. This task is left up to the developer based on how sessions are
being used, and on what back-end.

The database backend records the last accessed time as a column in the database
so a script could be run to delete session rows in the database that haven't
been used in a long time.

When using the file-based sessions, a script could run to remove files that
haven't been touched in a long time, for example (in the session's data dir):

.. code-block:: bash

    find . -mtime +3 -exec rm {} \;


Cookie Domain and Path
======================

In addition to setting a default cookie domain with the
:ref:`cookie domain setting <cookie_domain_config>`, the cookie's domain and
path can be set dynamically for a session with the domain and path properties.

These settings will persist as long as the cookie exists, or until changed.

Example::

    # Setting the session's cookie domain and path
    session.domain = '.domain.com'
    session.path = '/admin'


Cookie-Based
============

Session can be stored purely on the client-side using cookie-based sessions.
This option can be turned on by setting the session type to ``cookie``.

Using cookie-based session carries the limitation of how large a cookie can
be (generally 4096 bytes). An exception will be thrown should a session get
too large to fit in a cookie, so using cookie-based session should be done
carefully and only small bits of data should be stored in them (the users login
name, admin status, etc.).

Large cookies can slow down page-loads as they increase latency to every
page request since the cookie is sent for every request under that domain.
Static content such as images and Javascript should be served off a domain
that the cookie is not valid for to prevent this.

Cookie-based sessions scale easily in a clustered environment as there's no
need for a shared storage system when different servers handle the same
session.

.. _encryption:

Encryption
----------

In the event that the cookie-based sessions should also be encrypted to
prevent the user from being able to decode the data (in addition to not
being able to tamper with it), Beaker can use 256-bit AES encryption to
secure the contents of the cookie.

Depending on the Python implementation used, Beaker may require an additional
library to provide AES encryption.

On CPython (the regular Python), the `pycryptopp`_ library or `PyCrypto`_ library
 is required.

On Jython, no additional packages are required, but at least on the Sun JRE,
the size of the encryption key is by default limited to 128 bits, which causes
generated sessions to be incompatible with those generated in CPython, and vice
versa. To overcome this limitation, you need to install the unlimited strength
juristiction policy files from Sun:

* `Policy files for Java 5 <https://cds.sun.com/is-bin/INTERSHOP.enfinity/WFS/CDS-CDS_Developer-Site/en_US/-/USD/ViewProductDetail-Start?ProductRef=jce_policy-1.5.0-oth-JPR@CDS-CDS_Developer>`_
* `Policy files for Java 6 <https://cds.sun.com/is-bin/INTERSHOP.enfinity/WFS/CDS-CDS_Developer-Site/en_US/-/USD/ViewProductDetail-Start?ProductRef=jce_policy-6-oth-JPR@CDS-CDS_Developer>`_

.. _pycryptopp: http://pypi.python.org/pypi/pycryptopp
.. _PyCrypto: http://pypi.python.org/pypi/pycrypto/2.0.1
