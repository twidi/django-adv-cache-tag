from django import VERSION
from django.test import TestCase


if VERSION < (1, 7):
    from adv_cache_tag.compat import get_cache

    class TestCase(TestCase):
        def setUp(self):
            super(TestCase, self).setUp()

            # Override default cache in django < 1.7 because it is initialized before our
            # `override_settings`
            from django.core import cache
            cache.cache = get_cache('default')
