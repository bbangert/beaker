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
        if 'logged_in' in session:
            user = True
        else:
            user = False
        
        # Set some other session variable
        session['user_id'] = 10
        
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['User is logged in: %s' % user]
    
    # Configure the SessionMiddleware
    session_opts = {
        'session.type': 'file',
        'session.cookie_expires': 300
    }
    wsgi_app = SessionMiddleware(simple_app, session_opts)

.. note::
    This example does **not** actually save the session for the next request.
    Adding the :meth:`~beaker.session.Session.save` call explained below is
    required, or having the session set to auto-save.

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


Auto-save
---------

Saves can be done automatically by setting the ``auto`` configuration option
for sessions. When set, calling the :meth:`~beaker.session.Session.save` method
is no longer required, and the session will be saved automatically anytime its
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


Encryption
----------

In the event that the cookie-based sessions should also be encrypted to
prevent the user from being able to decode the data (in addition to not
being able to tamper with it), Beaker can use 256-bit AES encryption to
secure the contents of the cookie.

Beaker utilizes the `pycryptopp`_ library to provide AES encryption, since
256-bit AES encryption is used, both the ``encrypt_key`` and ``validate_key``
need to 16 characters in length.


.. _pycryptopp: http://pypi.python.org/pypi/pycryptopp