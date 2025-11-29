"""Cookie handling utilities for Beaker.

This module provides a SimpleCookie class that gracefully handles
invalid cookie keys while keeping around the session.
"""
import http.cookies as http_cookies


# Adapted from Django.http.cookies and always enabled the bad_cookies
# behaviour to cope with any invalid cookie key while keeping around
# the session.
class SimpleCookie(http_cookies.SimpleCookie):
    def load(self, rawdata):
        self.bad_cookies = set()
        super().load(rawdata)
        for key in self.bad_cookies:
            del self[key]

    # override private __set() method:
    # (needed for using our Morsel, and for laxness with CookieError
    def _BaseCookie__set(self, key, real_value, coded_value):
        try:
            super()._BaseCookie__set(key, real_value, coded_value)
        except http_cookies.CookieError:
            if not hasattr(self, 'bad_cookies'):
                self.bad_cookies = set()
            self.bad_cookies.add(key)
            dict.__setitem__(self, key, http_cookies.Morsel())
