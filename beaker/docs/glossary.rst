.. _glossary:

Glossary
========

.. glossary::

    Cache Regions
        Bundles of configuration options keyed to a user-defined variable
        for use with the :meth:`beaker.cache.CacheManager.region`
        decorator.

    Container
        A Beaker container is a storage object for a specific cache value
        and the key under the namespace it has been assigned.

    Dog-Pile Effect
        What occurs when a cached object expires, and multiple requests to
        fetch it are made at the same time. In systems that don't lock or
        use a scheme to prevent multiple instances from simultaneously
        creating the same thing, every request will cause the system to
        create a new value to be cached.

        Beaker alleviates this with file locking to ensure that only a single
        copy is re-created while other requests for the same object are
        instead given the old value until the new one is ready.

    NamespaceManager
        A Beaker namespace manager, is best thought of as a collection of
        containers with various keys. For example, a single template to be
        cached might vary slightly depending on search term, or user login, so
        the template would be keyed based on the variable that changes its
        output.

        The namespace would be the template name, while each container would
        correspond to one of the values and the key it responds to.
