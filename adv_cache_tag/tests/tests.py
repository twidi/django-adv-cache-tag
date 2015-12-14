import hashlib
import pickle
import time
import zlib

from datetime import datetime

from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.safestring import SafeText

from django.test.utils import override_settings
from django.utils.http import urlquote

from adv_cache_tag.compat import get_cache, template
from adv_cache_tag.tag import CacheTag

from .compat import TestCase


# Force some settings to not depend on the external ones
@override_settings(

    DEBUG = False,
    TEMPLATE_DEBUG = False,

    # Force using memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'default-cache',
        },
        'foo': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'foo-cache',
        },
    },

    # Used to compose RAW tags
    SECRET_KEY = 'm-92)2et+&&m5f&#jld7-_1qanq*n9!z90xc@+wx6y8d6y#w6t',

    # Reset default config
    ADV_CACHE_VERSIONING = False,
    ADV_CACHE_COMPRESS = False,
    ADV_CACHE_COMPRESS_SPACES= False,
    ADV_CACHE_INCLUDE_PK = False,
    ADV_CACHE_BACKEND = 'default',
    ADV_CACHE_VERSION = '',
    ADV_CACHE_RESOLVE_NAME = False,

    # For django >= 1.8 (RemovedInDjango110Warning appears in 1.9)
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'APP_DIRS': True,
        },
    ]
)
class BasicTestCase(TestCase):
    """First basic test case to be able to test python/django compatibility."""

    @classmethod
    def reload_config(cls):
        """Resest the ``CacheTag`` configuration from current settings"""
        CacheTag.options.versioning = getattr(settings, 'ADV_CACHE_VERSIONING', False)
        CacheTag.options.compress = getattr(settings, 'ADV_CACHE_COMPRESS', False)
        CacheTag.options.compress_spaces = getattr(settings, 'ADV_CACHE_COMPRESS_SPACES', False)
        CacheTag.options.include_pk = getattr(settings, 'ADV_CACHE_INCLUDE_PK', False)
        CacheTag.options.cache_backend = getattr(settings, 'ADV_CACHE_BACKEND', 'default')
        CacheTag.options.resolve_fragment = getattr(settings, 'ADV_CACHE_RESOLVE_NAME', False)

        # generate a token for this site, based on the secret_key
        CacheTag.RAW_TOKEN = 'RAW_' + hashlib.sha1(
            b'RAW_TOKEN_SALT1' + force_bytes(hashlib.sha1(
                b'RAW_TOKEN_SALT2' + force_bytes(settings.SECRET_KEY)
            ).hexdigest())
        ).hexdigest()

        # tokens to use around the already parsed parts of the cached template
        CacheTag.RAW_TOKEN_START = template.BLOCK_TAG_START + CacheTag.RAW_TOKEN + \
                                   template.BLOCK_TAG_END
        CacheTag.RAW_TOKEN_END = template.BLOCK_TAG_START + 'end' + CacheTag.RAW_TOKEN + \
                                 template.BLOCK_TAG_END

    def setUp(self):
        """Clean stuff and create an object to use in templates, and some counters."""
        super(BasicTestCase, self).setUp()

        # Clear the cache
        for cache_name in settings.CACHES:
            get_cache(cache_name).clear()

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        # And an object to cache in template
        self.obj = {
            'pk': 42,
            'name': 'foobar',
            'get_name': self.get_name,
            'get_foo': self.get_foo,
            'updated_at': datetime(2015, 10, 27, 0, 0, 0),
        }

        # To count the number of calls of ``get_name`` and ``get_foo``.
        self.get_name_called = 0
        self.get_foo_called = 0

    def get_name(self):
        """Called in template when asking for ``obj.get_name``."""
        self.get_name_called += 1
        return self.obj['name']

    def get_foo(self):
        """Called in template when asking for ``obj.get_foo``."""
        self.get_foo_called += 1
        return 'foo %d' % self.get_foo_called

    def tearDown(self):
        """Clear caches at the end."""

        for cache_name in settings.CACHES:
            get_cache(cache_name).clear()

        super(BasicTestCase, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        """At the very end of all theses tests, we reload the CacheTag config."""

        # Reset CacheTag config after the end of ``override_settings``
        cls.reload_config()

        super(BasicTestCase, cls).tearDownClass()

    @staticmethod
    def get_template_key(fragment_name, vary_on=None, prefix='template.cache'):
        """Compose the cache key of a template."""
        if vary_on is None:
            vary_on = ()
        key = ':'.join([urlquote(var) for var in vary_on])
        args = hashlib.md5(force_bytes(key))
        return (prefix + '.%s.%s') % (fragment_name, args.hexdigest())

    def render(self, template_text, extend_context_dict=None):
        """Utils to render a template text with a context given as a dict."""
        context_dict = {'obj': self.obj}
        if extend_context_dict:
            context_dict.update(extend_context_dict)
        return template.Template(template_text).render(template.Context(context_dict))

    def assertStripEqual(self, first, second):
        """Like ``assertEqual`` for strings, but after calling ``strip`` on both arguments."""
        if first:
            first = first.strip()
        if second:
            second = second.strip()

        self.assertEqual(first, second)

    def assertNotStripEqual(self, first, second):
        """Like ``assertNotEqual`` for strings, but after calling ``strip`` on both arguments."""
        if first:
            first = first.strip()
        if second:
            second = second.strip()

        self.assertNotEqual(first, second)

    def test_default_cache(self):
        """This test is only to validate the testing procedure."""

        expected = "foobar"

        t = """
            {% load cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        self.assertStripEqual(get_cache('default').get(key), expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    def test_adv_cache(self):
        """Test default behaviour with default settings."""

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # But it should NOT be the exact content as adv_cache_tag adds a version
        self.assertNotStripEqual(get_cache('default').get(key), expected)

        # It should be the version from `adv_cache_tag`
        cache_expected = b"1::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    def test_timeout_value(self):
        "Test that timeout value is ``None`` or an integer."""

        ok_values = ('0', '1', '9999', '"0"', '"1"', '"9999"', 'None')
        ko_values = ('-1', '-9999', '"-1"', '"-9999"', '"foo"', '""', '12.3', '"12.3"')

        t = """
            {%% load adv_cache %%}
            {%% cache %s test_cached_template obj.pk obj.updated_at %%}
                {{ obj.get_name }}
            {%% endcache %%}
        """

        for value in ok_values:
            def test_value(value):
                self.render(t % value)

            if hasattr(self, 'subTest'):
                with self.subTest(value=value):
                    test_value(value)
            else:
                test_value(value)

        for value in ko_values:
            def test_value(value):
                with self.assertRaises(template.TemplateSyntaxError) as raise_context:
                    self.render(t % value)
                self.assertIn(
                    'tag got a non-integer (or None) timeout value',
                    str(raise_context.exception)
                )

            if hasattr(self, 'subTest'):
                with self.subTest(value=value):
                    test_value(value)
            else:
                test_value(value)

    def test_quoted_fragment_name(self):
        """Test quotes behaviour around the fragment name."""

        t = """
            {% load adv_cache %}
            {% cache 1 "test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        with self.assertRaises(ValueError) as raise_context:
            self.render(t)
        self.assertIn('incoherent', str(raise_context.exception))

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template" obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        with self.assertRaises(ValueError) as raise_context:
            self.render(t)
        self.assertIn('incoherent', str(raise_context.exception))

        t = """
            {% load adv_cache %}
            {% cache 1 'test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        with self.assertRaises(ValueError) as raise_context:
            self.render(t)
        self.assertIn('incoherent', str(raise_context.exception))

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template" obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        with self.assertRaises(ValueError) as raise_context:
            self.render(t)
        self.assertIn('incoherent', str(raise_context.exception))

        t = """
            {% load adv_cache %}
            {% cache 1 "test_cached_template" obj.pk "foo" obj.updated_at %}
                {{ obj.get_name }} foo
            {% endcache %}
        """
        expected = "foobar foo"
        self.assertStripEqual(self.render(t), expected)
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], 'foo', self.obj['updated_at']])
        self.assertEqual(  # no quotes arround `test_cached_template`
            key, 'template.cache.test_cached_template.f2f294788f4c38512d3b544ce07befd0')
        cache_expected = b"1::\n                foobar foo"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        t = """
            {% load adv_cache %}
            {% cache 1 'test_cached_template' obj.pk "bar" obj.updated_at %}
                {{ obj.get_name }} bar
            {% endcache %}
        """
        expected = "foobar bar"
        self.assertStripEqual(self.render(t), expected)
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], 'bar', self.obj['updated_at']])
        self.assertEqual(  # no quotes arround `test_cached_template`
            key, 'template.cache.test_cached_template.8bccdefc91dc857fc02f6938bf69b816')
        cache_expected = b"1::\n                foobar bar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

    @override_settings(
        ADV_CACHE_VERSIONING = True,
    )
    def test_versioning(self):
        """Test with ``ADV_CACHE_VERSIONING`` set to ``True``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache

        # ``obj.updated_at`` is not in the key anymore, serving as the object version
        key = self.get_template_key('test_cached_template', vary_on=[self.obj['pk']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.a1d0c6e83f027327d8461063f4ac58a6')

        # It should be in the cache, with the ``updated_at`` in the version
        cache_expected = b"1::2015-10-27 00:00:00::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

        # We can update the date
        self.obj['updated_at'] = datetime(2015, 10, 28, 0, 0, 0)

        # Render with the new date, we should miss the cache because of the new "version
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 2)  # One more

        # It should be in the cache, with the new ``updated_at`` in the version
        cache_expected = b"1::2015-10-28 00:00:00::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 2)  # Still 2

    @override_settings(
        ADV_CACHE_INCLUDE_PK = True,
    )
    def test_primary_key(self):
        """Test with ``ADV_CACHE_INCLUDE_PK`` set to ``True``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache

        # We add the pk as a part to the fragment name
        key = self.get_template_key('test_cached_template.%s' % self.obj['pk'],
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.42.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache
        cache_expected = b"1::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_COMPRESS_SPACES = True,
    )
    def test_space_compression(self):
        """Test with ``ADV_CACHE_COMPRESS_SPACES`` set to ``True``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache, with only one space instead of many white spaces
        cache_expected = b"1:: foobar "
        # Test with ``assertEqual``, not ``assertStripEqual``
        self.assertEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_COMPRESS = True,
    )
    def test_compression(self):
        """Test with ``ADV_CACHE_COMPRESS`` set to ``True``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        # We don't use new lines here because too complicated to set empty lines with only
        # spaces in a docstring with we'll have to compute the compressed version
        t = "{% load adv_cache %}{% cache 1 test_cached_template obj.pk obj.updated_at %}" \
            "  {{ obj.get_name }}  {% endcache %}"

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache, compressed
        # We use ``SafeText`` as django does in templates
        compressed = zlib.compress(pickle.dumps(SafeText("  foobar  ")))
        cache_expected = b'1::' + compressed
        # Test with ``assertEqual``, not ``assertStripEqual``
        self.assertEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_COMPRESS = True,
        ADV_CACHE_COMPRESS_SPACES = True,
    )
    def test_full_compression(self):
        """Test with ``ADV_CACHE_COMPRESS`` and ``ADV_CACHE_COMPRESS_SPACES`` set to ``True``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache, compressed
        # We DON'T use ``SafeText`` as in ``test_compression`` because with was converted back
        # to a real string when removing spaces
        compressed = zlib.compress(pickle.dumps(" foobar "))
        cache_expected = b'1::' + compressed
        # Test with ``assertEqual``, not ``assertStripEqual``
        self.assertEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_BACKEND = 'foo',
    )
    def test_cache_backend(self):
        """Test with ``ADV_CACHE_BACKEND`` to another value than ``default``."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache
        cache_expected = b"1::\n                foobar"

        # But not in the ``default`` cache
        self.assertIsNone(get_cache('default').get(key))

        # But in the ``foo`` cache
        self.assertStripEqual(get_cache('foo').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_COMPRESS_SPACES = True,
    )
    def test_partial_cache(self):
        """Test the ``nocache`` templatetag."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar  foo 1  !!"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
                {% nocache %}
                    {{ obj.get_foo }}
                {% endnocache %}
                !!
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)
        self.assertEqual(self.get_foo_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache, with the RAW part
        cache_expected = b"1:: foobar {%endRAW_38a11088962625eb8c913e791931e2bc2e3c7228%} " \
                         b"{{obj.get_foo}} {%RAW_38a11088962625eb8c913e791931e2bc2e3c7228%} !! "
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache but not for ``get_foo``
        expected = "foobar  foo 2  !!"
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1
        self.assertEqual(self.get_foo_called, 2)  # One more call to the non-cached part

    def test_new_class(self):
        """Test a new class based on ``CacheTag``."""

        expected = "foobar  foo 1  !!"

        t = """
            {% load adv_cache_test %}
            {% cache_test 1 multiplicator test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
                {% nocache_test %}
                    {{ obj.get_foo }}
                {% endnocache_test %}
                !!
            {% endcache_test %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t, {'multiplicator': 10}), expected)
        self.assertEqual(self.get_name_called, 1)
        self.assertEqual(self.get_foo_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']],
                                    prefix='template.cache_test')
        self.assertEqual(
            key, 'template.cache_test.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache, with the RAW part
        cache_expected = b"1:: foobar {%endRAW_38a11088962625eb8c913e791931e2bc2e3c7228%} " \
                         b"{{obj.get_foo}} {%RAW_38a11088962625eb8c913e791931e2bc2e3c7228%} !! "
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # We'll check that our multiplicator was really applied
        cache = get_cache('default')
        expire_at = cache._expire_info[cache.make_key(key, version=None)]
        now = time.time()
        # In more that one second (default expiry we set) and less than ten
        self.assertTrue(now + 1 < expire_at < now + 10)

        # Render a second time, should hit the cache but not for ``get_foo``
        expected = "foobar  foo 2  !!"
        self.assertStripEqual(self.render(t, {'multiplicator': 10}), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1
        self.assertEqual(self.get_foo_called, 2)  # One more call to the non-cached part

    @override_settings(
        ADV_CACHE_RESOLVE_NAME = True,
    )
    def test_resolve_fragment_name(self):
        """Test passing the fragment name as a variable."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 fragment_name obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t, {'fragment_name': 'test_cached_template'}), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # But it should NOT be the exact content as adv_cache_tag adds a version
        self.assertNotStripEqual(get_cache('default').get(key), expected)

        # It should be the version from `adv_cache_tag`
        cache_expected = b"1::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t, {'fragment_name': 'test_cached_template'}), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

        # Using an undefined variable should fail
        t = """
            {% load adv_cache %}
            {% cache 1 undefined_fragment_name obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        with self.assertRaises(template.VariableDoesNotExist) as raise_context:
            self.render(t, {'fragment_name': 'test_cached_template'})
        self.assertIn('undefined_fragment_name', str(raise_context.exception))

    @override_settings(
        ADV_CACHE_RESOLVE_NAME = True,
    )
    def test_passing_fragment_name_as_string(self):
        """Test passing the fragment name as a variable."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 "test_cached_template" obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # But it should NOT be the exact content as adv_cache_tag adds a version
        self.assertNotStripEqual(get_cache('default').get(key), expected)

        # It should be the version from `adv_cache_tag`
        cache_expected = b"1::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    def test_using_argument(self):
        """Test passing the cache backend to use with the `using=` arg to the templatetag."""

        expected = "foobar"

        t = """
            {% load adv_cache %}
            {% cache 1 test_cached_template obj.pk obj.updated_at using=foo %}
                {{ obj.get_name }}
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']])
        self.assertEqual(
            key, 'template.cache.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache
        cache_expected = b"1::\n                foobar"

        # But not in the ``default`` cache
        self.assertIsNone(get_cache('default').get(key))

        # But in the ``foo`` cache
        self.assertStripEqual(get_cache('foo').get(key), cache_expected)

        # Render a second time, should hit the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1

    @override_settings(
        ADV_CACHE_COMPRESS_SPACES = True,
    )
    def test_loading_libraries_in_nocache(self):
        """Test that needed libraries are loaded in the nocache block."""

        # Reset CacheTag config with default value (from the ``override_settings``)
        self.reload_config()

        expected = "foobar FoOoO   FOO 1FOO 1 FoOoO  !!"

        t = """
            {% load adv_cache other_tags %}
            {% cache 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }} {% insert_foo %}
                {% nocache %}
                    {% load other_filters %}
                    {{ obj.get_foo|double_upper }} {% insert_foo %}
                {% endnocache %}
                !!
            {% endcache %}
        """

        # Render a first time, should miss the cache
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)
        self.assertEqual(self.get_foo_called, 1)

        # Render a second time, should hit the cache but not for ``get_foo``
        expected = "foobar FoOoO   FOO 2FOO 2 FoOoO  !!"
        self.assertStripEqual(self.render(t), expected)
        self.assertEqual(self.get_name_called, 1)  # Still 1
        self.assertEqual(self.get_foo_called, 2)  # One more call to the non-cached part

    def test_failure_when_setting_cache(self):
        """Test that the template is correctly rendered even if the cache cannot be filled."""

        expected = "foobar"

        t = """
            {% load adv_cache_test %}
            {% cache_set_fail 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache_set_fail %}
        """

        # Render a first time, should still be rendered
        self.assertStripEqual(self.render(t), expected)

        # Now the rendered template should NOT be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']],
                                    prefix='template.cache_set_fail')
        self.assertEqual(
            key, 'template.cache_set_fail.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # But not in the ``default`` cache
        self.assertIsNone(get_cache('default').get(key))

        # It should raise if ``TEMPLATE_DEBUG`` is ``True``
        with override_settings(TEMPLATE_DEBUG=True):
            with self.assertRaises(ValueError) as raise_context:
                self.render(t)
            self.assertIn('boom set', str(raise_context.exception))

    def test_failure_when_getting_cache(self):
        """Test that the template is correctly rendered even if the cache cannot be read."""

        expected = "foobar"

        t = """
            {% load adv_cache_test %}
            {% cache_get_fail 1 test_cached_template obj.pk obj.updated_at %}
                {{ obj.get_name }}
            {% endcache_get_fail %}
        """

        # Render a first time, should still be rendered
        self.assertStripEqual(self.render(t), expected)

        # Now the rendered template should be in cache
        key = self.get_template_key('test_cached_template',
                                    vary_on=[self.obj['pk'], self.obj['updated_at']],
                                    prefix='template.cache_get_fail')
        self.assertEqual(
            key, 'template.cache_get_fail.test_cached_template.0cac9a03d5330dd78ddc9a0c16f01403')

        # It should be in the cache
        cache_expected = b"1::\n                foobar"
        self.assertStripEqual(get_cache('default').get(key), cache_expected)

        # It should raise if ``TEMPLATE_DEBUG`` is ``True``
        with override_settings(TEMPLATE_DEBUG=True):
            with self.assertRaises(ValueError) as raise_context:
                self.render(t)
            self.assertIn('boom get', str(raise_context.exception))
