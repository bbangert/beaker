# -*- coding: utf-8 -*-
"""This is a collection of annotated functions used by tests.

They are grouped here to provide an easy way to import them at runtime
to check whenever tests for annotated functions should be skipped or not
on current python version.
"""
from beaker.cache import cache_region
import time

class AnnotatedAlfredCacher(object):
    @cache_region('short_term')
    def alfred_self(self, xx: int, y=None) -> str:
        return str(time.time()) + str(self) + str(xx) + str(y)

