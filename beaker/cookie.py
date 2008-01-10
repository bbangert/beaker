"""
Cookie handling portions of this code are copied from mod_python and
licensed under the Apache license as follows:

Licensed under the Apache License, Version 2.0 (the "License"); you
may not use this file except in compliance with the License.  You
may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.  See the License for the specific language governing
permissions and limitations under the License.

Originally developed by Gregory Trubetskoy.
"""
import hmac
import re
import time

class CookieError(Exception):
    pass

class metaCookie(type):

    def __new__(cls, clsname, bases, clsdict):

        _valid_attr = (
            "version", "path", "domain", "secure",
            "comment", "expires", "max_age",
            # RFC 2965
            "commentURL", "discard", "port",
            # Microsoft Extension
            "httponly" )

        # _valid_attr + property values
        # (note __slots__ is a new Python feature, it
        # prevents any other attribute from being set)
        __slots__ = _valid_attr + ("name", "value", "_value",
                                   "_expires", "__data__")

        clsdict["_valid_attr"] = _valid_attr
        clsdict["__slots__"] = __slots__

        def set_expires(self, value):

            if type(value) == type(""):
                # if it's a string, it should be
                # valid format as per Netscape spec
                try:
                    t = time.strptime(value, "%a, %d-%b-%Y %H:%M:%S GMT")
                except ValueError:
                    raise ValueError, "Invalid expires time: %s" % value
                t = time.mktime(t)
            else:
                # otherwise assume it's a number
                # representing time as from time.time()
                t = value
                value = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT",
                                      time.gmtime(t))

            self._expires = "%s" % value

        def get_expires(self):
            return self._expires

        clsdict["expires"] = property(fget=get_expires, fset=set_expires)

        return type.__new__(cls, clsname, bases, clsdict)

class Cookie(object):
    """
    This class implements the basic Cookie functionality. Note that
    unlike the Python Standard Library Cookie class, this class represents
    a single cookie (not a list of Morsels).
    """

    __metaclass__ = metaCookie

    DOWNGRADE = 0
    IGNORE = 1
    EXCEPTION = 3

    def parse(Class, str, **kw):
        """
        Parse a Cookie or Set-Cookie header value, and return
        a dict of Cookies. Note: the string should NOT include the
        header name, only the value.
        """

        dict = _parse_cookie(str, Class, **kw)
        return dict

    parse = classmethod(parse)

    def __init__(self, name, value, **kw):

        """
        This constructor takes at least a name and value as the
        arguments, as well as optionally any of allowed cookie attributes
        as defined in the existing cookie standards. 
        """
        self.name, self.value = name, value

        for k in kw:
            setattr(self, k.lower(), kw[k])

        # subclasses can use this for internal stuff
        self.__data__ = {}


    def __str__(self):

        """
        Provides the string representation of the Cookie suitable for
        sending to the browser. Note that the actual header name will
        not be part of the string.

        This method makes no attempt to automatically double-quote
        strings that contain special characters, even though the RFC's
        dictate this. This is because doing so seems to confuse most
        browsers out there.
        """
        
        result = ["%s=%s" % (self.name, self.value)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard", "httponly"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)
    
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                                str(self))
    

class SignedCookie(Cookie):
    """
    This is a variation of Cookie that provides automatic
    cryptographic signing of cookies and verification. It uses
    the HMAC support in the Python standard library. This ensures
    that the cookie has not been tamprered with on the client side.

    Note that this class does not encrypt cookie data, thus it
    is still plainly visible as part of the cookie.
    """

    def parse(Class, s, secret, mismatch=Cookie.DOWNGRADE, **kw):

        dict = _parse_cookie(s, Class, **kw)

        del_list = []
        for k in dict:
            c = dict[k]
            try:
                c.unsign(secret)
            except CookieError:
                if mismatch == Cookie.EXCEPTION:
                     raise
                elif mismatch == Cookie.IGNORE:
                     del_list.append(k)
                else:
                     # downgrade to Cookie
                     dict[k] = Cookie.parse(Cookie.__str__(c))[k]

        for k in del_list:
            del dict[k]

        return dict

    parse = classmethod(parse)

    def __init__(self, name, value, secret=None, **kw):
        Cookie.__init__(self, name, value, **kw)

        self.__data__["secret"] = secret

    def hexdigest(self, str):
        if not self.__data__["secret"]:
            raise CookieError, "Cannot sign without a secret"
        _hmac = hmac.new(self.__data__["secret"], self.name)
        _hmac.update(str)
        return _hmac.hexdigest()

    def __str__(self):
        
        result = ["%s=%s%s" % (self.name, self.hexdigest(self.value),
                               self.value)]
        for name in self._valid_attr:
            if hasattr(self, name):
                if name in ("secure", "discard", "httponly"):
                    result.append(name)
                else:
                    result.append("%s=%s" % (name, getattr(self, name)))
        return "; ".join(result)

    def unsign(self, secret):

        sig, val = self.value[:32], self.value[32:]

        mac = hmac.new(secret, self.name)
        mac.update(val)

        if mac.hexdigest() == sig:
            self.value = val
            self.__data__["secret"] = secret
        else:
            raise CookieError, "Incorrectly Signed Cookie: %s=%s" % (self.name, self.value)

# This is a simplified and in some places corrected
# (at least I think it is) pattern from standard lib Cookie.py

_cookiePattern = re.compile(
    r"(?x)"                       # Verbose pattern
    r"[,\ ]*"                        # space/comma (RFC2616 4.2) before attr-val is eaten
    r"(?P<key>"                   # Start of group 'key'
    r"[^;\ =]+"                     # anything but ';', ' ' or '='
    r")"                          # End of group 'key'
    r"\ *(=\ *)?"                 # a space, then may be "=", more space
    r"(?P<val>"                   # Start of group 'val'
    r'"(?:[^\\"]|\\.)*"'            # a doublequoted string
    r"|"                            # or
    r"[^;]*"                        # any word or empty string
    r")"                          # End of group 'val'
    r"\s*;?"                      # probably ending in a semi-colon
    )

def _parse_cookie(str, Class, names=None):
    # XXX problem is we should allow duplicate
    # strings
    result = {}

    matchIter = _cookiePattern.finditer(str)

    for match in matchIter:
        key, val = match.group("key"), match.group("val")

        # We just ditch the cookies names which start with a dollar sign since
        # those are in fact RFC2965 cookies attributes. See bug [#MODPYTHON-3].
        if key[0]!='$' and names is None or key in names:
            result[key] = Class(key, val)

    return result
