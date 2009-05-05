.. _glossary:

Glossary
========

.. glossary::
    
    Dog-Pile Effect
        What occurs when a cached object expires, and multiple requests to
        fetch it are made at the same time. In systems that don't lock or
        use a scheme to prevent multiple instances from simultaneously
        creating the same thing, every request will cause the system to
        create a new value to be cached.
        
        Beaker alleviates this with file locking to ensure that only a single
        copy is re-created while other requests for the same object are
        instead given the old value until the new one is ready.