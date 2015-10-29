from django import VERSION
from django.conf import settings
from django.test import TestCase

from adv_cache_tag.compat import template

try:
    from django.test.utils import override_settings
except ImportError:
    # Django < 1.4
    from django.conf import UserSettingsHolder
    from django.utils.functional import wraps

    class override_settings(object):
        """
        Acts as either a decorator, or a context manager. If it's a decorator it
        takes a function and returns a wrapped function. If it's a contextmanager
        it's used with the ``with`` statement. In either event entering/exiting
        are called before and after, respectively, the function/block is executed.
        """
        def __init__(self, **kwargs):
            self.options = kwargs

        def __enter__(self):
            self.enable()

        def __exit__(self, exc_type, exc_value, traceback):
            self.disable()

        def __call__(self, test_func):
            from django.test import TransactionTestCase
            if isinstance(test_func, type):
                if not issubclass(test_func, TransactionTestCase):
                    raise Exception(
                        "Only subclasses of Django TransactionTestCase can be decorated "
                        "with override_settings")
                original_pre_setup = test_func._pre_setup
                original_post_teardown = test_func._post_teardown

                def _pre_setup(innerself):
                    self.enable()
                    original_pre_setup(innerself)

                def _post_teardown(innerself):
                    original_post_teardown(innerself)
                    self.disable()
                test_func._pre_setup = _pre_setup
                test_func._post_teardown = _post_teardown
                return test_func
            else:
                @wraps(test_func)
                def inner(*args, **kwargs):
                    with self:
                        return test_func(*args, **kwargs)
            return inner

        def enable(self):
            override = UserSettingsHolder(settings._wrapped)
            for key, new_value in self.options.items():
                setattr(override, key, new_value)
            self.wrapped = settings._wrapped
            settings._wrapped = override

        def disable(self):
            settings._wrapped = self.wrapped
            del self.wrapped
            for key in self.options:
                new_value = getattr(settings, key, None)

if VERSION < (1, 7):
    from adv_cache_tag.compat import get_cache

    class TestCase(TestCase):
        def setUp(self):
            super(TestCase, self).setUp()

            # Override default cache in django < 1.7 because it is initialized before our
            # `override_settings`
            from django.core import cache
            cache.cache = get_cache('default')


try:
    from django.utils.safestring import SafeText
except ImportError:
    # Django < 1.4
    from django.utils.safestring import SafeUnicode as SafeText


if VERSION < (1, 4):
    # In Django 1.3, original errors where catched and a ``TemplateSyntaxError`` was raised
    ValueErrorInRender = template.TemplateSyntaxError
else:
    ValueErrorInRender = ValueError
