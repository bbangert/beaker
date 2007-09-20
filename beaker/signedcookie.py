"""Signed Cookie middleware support"""
import md5
import os
import time
from datetime import datetime, timedelta

from beaker.cookie import SignedCookie

class SignedCookieMiddleware(object):
    def __init__(self, app, secret, key='beaker_cookie.id', timeout=None,
                 cookie_expires=True, environ_name='beaker.cookie'):
        """Create signed cookie middleware that loads into environ
        
        ``secret``
            The secret to use for signing the session data.
        ``key``
            Name to use for the data.
        ``timeout``
            Time in seconds that the cookie data is considered valid 
            for.
        ``cookie_expires``
            Time in seconds that will be set from now for when the 
            cookie expires. Set to True to expire at end of browser 
            session or False to never expire.
        
        """
        self.app = app
        self.secret = secret
        self.key = key
        self.timeout = timeout
        self.cookie_expires = cookie_expires
        self.environ_name = environ_name
    
    def __call__(self, environ, start_response):
        """Populate the environ with the session ID and tuple of data
        
        The cookie data is set as environ[environ_name] where 
        ``environ_name`` is set in the class instantiation.
        
        Anything set in this environ key will be sent back out in the
        cookie header. The data should be a plain string that doesn't
        contain characters not valid for cookie data and doesn't 
        contain the '#' char as thats used as a separator.
        
        """
        cookies = SignedCookie.parse(environ.get('HTTP_COOKIE'), 
                                     self.secret, 
                                     mismatch=1)
        cookie = cookies.get(self.key)
        
        cookie_id = None
        if cookie:
            cookie_id = cookie.value[:32]
            val = cookie.value[32:]
            
            # Check to see if we have a timeout, if so see if its passed
            if self.timeout is not None:
                past, val = val.split('#', 1)
                if time.time() - float(past) > self.timeout:
                    val = ''
            environ[self.environ_name] = val
        else:
            cookie_id = md5.new(md5.new(os.urandom(128)).hexdigest()).hexdigest()
            environ[self.environ_name] = ''
        environ['beaker.cookie_id'] = cookie_id
        environ['beaker.cookie_obj'] = cookie
        
        def cap_start_response(status, headers, exc_info=None):
            user_data = environ[self.environ_name]
            data = ''.join([cookie_id, user_data])
            
            cookie = environ['beaker.cookie_obj']
            # If we have a cookie already, and the value is the same as the 
            # data (its unchanged), and there's no timeout we don't need to
            # send it again
            if cookie and cookie.value == data and self.timeout is not None:
                return start_response(status, headers, exc_info)
            
            # If we have a timeout, set the time in the cookie
            if self.timeout:
                data = ''.join([cookie_id, str(time.time()) + '#' + user_data])
            
            headers.append(("Cache-Control", 'no-cache="set-cookie"'))
            cookie = SignedCookie(self.key, data, self.secret)
            cookie.path = '/'
            if self.cookie_expires is not True:
                
                if self.cookie_expires is False:
                    # No expiration, set it for the far future
                    expires = datetime.fromtimestamp( 0x7FFFFFFF )
                elif isinstance(self.cookie_expires, timedelta):
                    # Set it for the time difference from today
                    expires = datetime.today() + self.cookie_expires
                elif isinstance(self.cookie_expires, datetime):
                    expires = self.cookie_expires
                cookie.set_expires(expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT" ))
            
            headers.append(('Set-Cookie', str(cookie)))
            return start_response(status, headers, exc_info)
        return self.app(environ, cap_start_response)
