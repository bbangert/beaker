:mod:`beaker.session` -- Session classes 
========================================

.. automodule:: beaker.session

Module Contents
---------------

.. autoclass:: CookieSession
   :members: save, expire, delete, invalidate
.. autoclass:: Session
   :members: save, revert, lock, unlock, delete, invalidate
.. autoclass:: SessionObject
   :members: persist, get_by_id, accessed
.. autoclass:: SignedCookie
