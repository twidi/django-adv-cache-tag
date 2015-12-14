# django-adv-cache-tag / Copyright Stephane "Twidi" Angel <s.angel@twidi.com> / MIT License

import hashlib
import logging
import re
import zlib

from django.conf import settings
from django.utils.encoding import smart_str
from django.utils.http import urlquote

from .compat import get_cache, get_template_libraries, pickle, template

logger = logging.getLogger('adv_cache_tag')


class Node(template.Node):
    """
    It's a normal template Node, with parameters defined in __init__ and rendering
    This class can be extended in your own main cache class, by redefining a `Node`
    class descending on this one.
    """

    def __init__(self, nodename, nodelist, expire_time, fragment_name, vary_on):
        """
        Define parameters to be used by the templatetag. The same as for
        the default `cache` templatetag in django, except for `nodename`
        which is the name used to call this templatetag ("cache" by default)

        If versioning is activated, the last argument in `vary_on` is popped
        and used for this purpose.

        If the `include_pk` option is activated, the first argument in `vary_on`
        will be used as the `pk` (but not removed from `vary_on`.
        """
        super(Node, self).__init__()
        self.nodename = nodename
        self.nodelist = nodelist
        self.expire_time = template.Variable(expire_time)
        self.fragment_name = template.Variable(fragment_name)

        self.cache_backend = None
        if vary_on and vary_on[-1].startswith('using='):
            self.cache_backend = vary_on.pop()[len('using='):]

        self.version = None
        if self._cachetag_class_.options.versioning:
            try:
                self.version = template.Variable(vary_on.pop())
            except Exception:
                self.version = None

        self.vary_on = vary_on

    def render(self, context):
        """
        Render the template by calling the render method of the main
        cache object.
        """
        return self._cachetag_class_(self, context).render()


class CacheTagMetaClass(type):
    """
    Metaclass used by CacheTag to save the Meta entries in a options field, and
    save the current class in the Node one.
    """

    def __new__(mcs, name, bases, attrs):
        klass = super(CacheTagMetaClass, mcs).__new__(mcs, name, bases, attrs)
        klass.options = klass._meta = klass.Meta()
        # One `Node` class for each `CacheTag` class, with a link on the reverse side too
        klass.Node = type('Node', (klass.Node, ), {'_cachetag_class_': klass})
        return klass


class CacheTag(object):
    """
    The main class of `django-adv-cache-tag` which does all the work.

    To change its behaviour, simply change one or more of these settings
    (see in the `Meta` class for details) :

        * ADV_CACHE_VERSIONING
        * ADV_CACHE_COMPRESS
        * ADV_CACHE_COMPRESS_SPACES
        * ADV_CACHE_INCLUDE_PK
        * ADV_CACHE_BACKEND
        * ADV_CACHE_VERSION
        * ADV_CACHE_RESOLVE_NAME

    Or inherit from this class and don't forget to register your tag :

        from adv_cache_tag.tag import CacheTag
        register = template.Library()
        class MyCacheTag(CacheTag):
            # change something
        MyCacheTag.register(register, 'my_cache')

    By inheriting you can change many things as CacheTag implements a lot of
    small methods
    """

    # Will change if the algorithm changes
    INTERNAL_VERSION = '0.1'
    # Used to separate internal version, template version, and the content
    VERSION_SEPARATOR = '::'

    # Regex used to reduce spaces/blanks (many spaces into one)
    RE_SPACELESS = re.compile(r'\s\s+')

    # generate a token for this site, based on the secret_key
    RAW_TOKEN = 'RAW_' + hashlib.sha1(
        'RAW_TOKEN_SALT1' + hashlib.sha1(
            'RAW_TOKEN_SALT2' + settings.SECRET_KEY
        ).digest()
    ).hexdigest()

    # tokens to use around the already parsed parts of the cached template
    RAW_TOKEN_START = template.BLOCK_TAG_START + RAW_TOKEN + template.BLOCK_TAG_END
    RAW_TOKEN_END = template.BLOCK_TAG_START + 'end' + RAW_TOKEN + template.BLOCK_TAG_END

    # internal use only: keep reference to templatetags functions
    _templatetags = {}
    # internal use only: name of the templatetags module to load for this class and subclasses
    _templatetags_modules = {}

    options = None
    Node = Node

    class Meta:
        """
        Options of this class. Accessible via cls.options or self.options.
        To force (and/or add) options in your own class, simply redefine a
        `Meta` class in your own main cache class with updated/add values
        """

        # If versioning is activated (internal versioning is always on)
        versioning = getattr(settings, 'ADV_CACHE_VERSIONING', False)

        # If the content will be compressed before caching
        compress = getattr(settings, 'ADV_CACHE_COMPRESS', False)

        # If many spaces/blanks will be converted into one
        compress_spaces = getattr(settings, 'ADV_CACHE_COMPRESS_SPACES', False)

        # If a "pk" (you can pass what you want) will be added to the cache key
        include_pk = getattr(settings, 'ADV_CACHE_INCLUDE_PK', False)

        # The cache backend to use (or use the "default" one)
        cache_backend = getattr(settings, 'ADV_CACHE_BACKEND', 'default')

        # Part of the INTERNAL_VERSION configurable via settings
        internal_version = getattr(settings, 'ADV_CACHE_VERSION', '')

        # If the fragment name should be resolved or taken as is
        resolve_fragment = getattr(settings, 'ADV_CACHE_RESOLVE_NAME', False)

    # Use a metaclass to use the right class in the Node class, and assign Meta to options
    __metaclass__ = CacheTagMetaClass

    def __init__(self, node, context):
        """
        Constructor of the Cache class:
            * preparing fields to be used later,
            * prepare the templatetag parameters
            * create the cache key
        """
        super(CacheTag, self).__init__()

        # the actual Node object
        self.node = node

        # the context used for the rendering
        self.context = context

        # indicate that we force regenerating the cache, even if it exists
        self.regenerate = bool(self.context.get('__regenerate__', False))

        # indicate if we only want html without parsing the nocache parts
        self.partial = bool(self.context.get('__partial__', False))

        # the content of the template, will be used through the whole process
        self.content = ''
        # the version used in the cached templatetag
        self.content_version = None

        # Final "INTERNAL_VERSION"
        if self.options.internal_version:
            self.INTERNAL_VERSION = '%s|%s' % (self.__class__.INTERNAL_VERSION,
                                               self.options.internal_version)

        # prepare all parameters passed to the templatetag
        self.expire_time = None
        self.version = None
        self.prepare_params()

        # get the cache and cache key
        self.cache = self.get_cache_object()
        self.cache_key = self.get_cache_key()

    def prepare_params(self):
        """
        Prepare the parameters passed to the templatetag
        """
        if self.options.resolve_fragment:
            self.fragment_name = self.node.fragment_name.resolve(self.context)
        else:
            self.fragment_name = str(self.node.fragment_name)
            # Remove quotes that surround the name
            for char in '\'\"':
                if self.fragment_name.startswith(char) or self.fragment_name.endswith(char):
                    if self.fragment_name.startswith(char) and self.fragment_name.endswith(char):
                        self.fragment_name = self.fragment_name[1:-1]
                        break
                    else:
                        raise ValueError('Number of quotes around the fragment name is incoherent')

        self.expire_time = self.get_expire_time()

        if self.options.versioning:
            self.version = self.get_version()

        self.vary_on = [template.Variable(var).resolve(self.context) for var in self.node.vary_on]

    def get_expire_time(self):
        """
        Return the expire time passed to the templatetag.
        Must be None or an integer.
        """
        try:
            expire_time = self.node.expire_time.resolve(self.context)
        except template.VariableDoesNotExist:
            if self.node.expire_time.var == 'None':
                # `None` was not valid before django 1.5
                expire_time = None
            else:
                raise template.TemplateSyntaxError('"%s" tag got an unknown variable: %r' %
                                                   (self.node.nodename, self.node.expire_time.var))
        try:
            if expire_time is not None:
                expire_time = str(expire_time)
                if not expire_time.isdigit():
                    raise TypeError
                expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise template.TemplateSyntaxError(
                '"%s" tag got a non-integer (or None) timeout value: %r' % (
                    self.node.nodename, expire_time
                )
            )

        return expire_time

    def get_version(self):
        """
        Return the stringified version passed to the templatetag.
        """
        if not self.node.version:
            return None
        try:
            version = smart_str('%s' % self.node.version.resolve(self.context))
        except template.VariableDoesNotExist:
            raise template.TemplateSyntaxError('"%s" tag got an unknown variable: %r' %
                                               (self.node.nodename, self.node.version.var))

        return '%s' % version

    def hash_args(self):
        """
        Take all the arguments passed after the fragment name and return a
        hashed version which will be used in the cache key
        """
        return hashlib.md5(u':'.join([urlquote(var) for var in self.vary_on])).hexdigest()

    def get_pk(self):
        """
        Return the pk to use in the cache key. It's the first version of the
        templatetag arguments after the fragment name
        """
        return self.vary_on[0]

    def get_base_cache_key(self):
        """
        Return a string with format placeholder used as a source to compute the
        final cache key.
        Placeholders are :
            * %(nodename)s : the name of the templatetag
            * %(name)s : the fragment name passed to the templatetag
            * %(pk)s : the return of the `get_pk` method, passed only if `include_pk` is True
            * %(hash)s : the return of the `hash_args` method
        """
        if self.options.include_pk:
            return 'template.%(nodename)s.%(name)s.%(pk)s.%(hash)s'
        else:
            return 'template.%(nodename)s.%(name)s.%(hash)s'

    def get_cache_key_args(self):
        """
        Return the arguments to be passed to the base cache key returned by `get_base_cache_key`.
        """
        cache_key_args = dict(
            nodename=self.node.nodename,
            name=self.fragment_name,
            hash=self.hash_args(),
        )
        if self.options.include_pk:
            cache_key_args['pk'] = self.get_pk()

        return cache_key_args

    def get_cache_key(self):
        """
        Compute and return the final cache key, using return values of
        `get_base_cache_key` and `get_cache_key_args`.
        """
        return self.get_base_cache_key() % self.get_cache_key_args()

    def get_cache_object(self):
        """
        Return the cache object to be used to set and get the values in cache.
        By default it's the default cache defined by django, but it can be
        every object with a `get` and a `set` method (or not, if `cache_get`
        and `cache_set` methods are overridden)
        """
        return get_cache(self.node.cache_backend or self.options.cache_backend)

    def cache_get(self):
        """
        Get content from the cache
        """
        return self.cache.get(self.cache_key)

    def cache_set(self, to_cache):
        """
        Set content into the cache
        """
        self.cache.set(self.cache_key, to_cache, self.expire_time)

    def join_content_version(self, to_cache):
        """
        Add the version(s) to the content to cache : internal version at first
        and then the template version if versioning is activated.
        Each version, and the content, are separated with `VERSION_SEPARATOR`.
        This method is called after the encoding (if "compress" or
        "compress_spaces" options are on)
        """
        parts = ['%s' % self.INTERNAL_VERSION]
        if self.options.versioning:
            parts.append('%s' % self.version)

        return self.VERSION_SEPARATOR.join(parts) + self.VERSION_SEPARATOR + to_cache

    def split_content_version(self):
        """
        Remove and return the version(s) from the cached content. First the
        internal version, and if versioning is activated, the template one.
        And finally save the content, but only if all versions match.
        The content saved is the encoded one (if "compress" or
        "compress_spaces" options are on). By doing so, we avoid decoding if
        the versions didn't match, to save some cpu cycles.
        """
        try:
            nb_parts = 2
            if self.options.versioning:
                nb_parts = 3

            parts = self.content.split(self.VERSION_SEPARATOR, nb_parts - 1)
            assert len(parts) == nb_parts

            self.content_internal_version = '%s' % parts[0]
            if self.options.versioning:
                self.content_version = '%s' % parts[1]

            self.content = parts[-1]
        except Exception:
            self.content = None

    def decode_content(self):
        """
        Decode (decompress...) the content got from the cache, to the final
        html
        """
        self.content = pickle.loads(zlib.decompress(self.content))

    def encode_content(self):
        """
        Encode (compress...) the html to the data to be cached
        """
        return zlib.compress(pickle.dumps(self.content))

    def render_node(self):
        """
        Render the template and save the generated content
        """
        self.content = self.node.nodelist.render(self.context)

    def create_content(self):
        """
        Render the template, apply options on it, and save it to the cache.
        """
        self.render_node()

        if self.options.compress_spaces:
            self.content = self.RE_SPACELESS.sub(' ', self.content)

        if self.options.compress:
            to_cache = self.encode_content()
        else:
            to_cache = self.content

        to_cache = self.join_content_version(to_cache)

        try:
            self.cache_set(to_cache)
        except Exception:
            if settings.TEMPLATE_DEBUG:
                raise
            logger.exception('Error when saving the cached template fragment')

    def load_content(self):
        """
        It's the main method of the class.
        Try to load the template from cache, get the versions and decode the
        content.
        If something was wrong during this process (or if we had a
        `__regenerate__` value to True in the context), create new content and
        save it in cache.
        """

        self.content = None

        if not self.regenerate:
            try:
                self.content = self.cache_get()
            except Exception:
                if settings.TEMPLATE_DEBUG:
                    raise
                logger.exception('Error when getting the cached template fragment')

        try:

            assert self.content

            self.split_content_version()

            assert self.content

            if self.content_internal_version != self.INTERNAL_VERSION or (
                    self.options.versioning and self.content_version != self.version):
                self.content = None

            assert self.content

            if self.options.compress:
                self.decode_content()

        except Exception:
            self.create_content()

    def render(self):
        """
        Try to load content (from cache or by rendering the template).
        If it fails, return an empty string or raise the exception if it's a
        TemplateSyntaxError.
        With this, we can no parse and render the content included in the
        {% nocache %} blocks, but only if we have have this tag and if we don't
        have `__partial__` to True in the context (in this case we simple
        return the html with the {% nocache %} block not parsed.
        """
        try:
            self.load_content()
        except template.TemplateSyntaxError:
            raise
        except Exception:
            if settings.TEMPLATE_DEBUG:
                raise
            logger.exception('Error when rendering template fragment')
            return ''

        if self.partial or self.RAW_TOKEN_START not in self.content:
            return self.content

        return self.render_nocache()

    @staticmethod
    def get_all_tags_and_filters_by_function():
        """
        Return a dict with all the template tags (in the `tags` entry) and filters (in the
        `filters` entry) that are available.
        Both entries are a dict with the function as key, and a tuple with (library name, function
        name) as value.
        This is cached after the first call.
        """

        libraries = get_template_libraries()

        force = False

        # We'll force the update of the cache if new libraries where added
        if hasattr(CacheTag.get_all_tags_and_filters_by_function, '_len_libraries'):
            if len(libraries) != CacheTag.get_all_tags_and_filters_by_function._len_libraries:
                force = True

        if force or not hasattr(CacheTag.get_all_tags_and_filters_by_function, '_cache'):
            CacheTag.get_all_tags_and_filters_by_function._len_libraries = len(libraries)
            available_tags = {}
            available_filters = {}

            for lib_name, lib in libraries.items():
                available_tags.update(
                    (function, (lib_name, tag_name))
                    for tag_name, function
                    in lib.tags.items()
                )
                available_filters.update(
                    (function, (lib_name, filter_name))
                    for filter_name, function
                    in lib.filters.items()
                )

            CacheTag.get_all_tags_and_filters_by_function._cache = {
                'tags': available_tags,
                'filters': available_filters
            }

        return CacheTag.get_all_tags_and_filters_by_function._cache

    @classmethod
    def get_templatetag_module(cls):
        """
        Return the templatetags module name for which the current class is used.
        It's used to render the nocache blocks by loading the correct module
        """
        if cls not in CacheTag._templatetags_modules:
            # find the library including the main templatetag of the current class
            all_tags = cls.get_all_tags_and_filters_by_function()['tags']
            CacheTag._templatetags_modules[cls] = all_tags[CacheTag._templatetags[cls]['cache']][0]
        return CacheTag._templatetags_modules[cls]

    def render_nocache(self):
        """
        Render the `nocache` blocks of the content and return the whole
        html
        """
        tmpl = template.Template(''.join([
            # start by loading the cache library
            template.BLOCK_TAG_START,
            'load %s' % self.get_templatetag_module(),
            template.BLOCK_TAG_END,
            # and surround the cached template by "raw" tags
            self.RAW_TOKEN_START,
            self.content,
            self.RAW_TOKEN_END,
        ]))
        return tmpl.render(self.context)

    @classmethod
    def get_template_node_arguments(cls, tokens):
        """
        Return the arguments taken from the templatetag that will be used to the
        Node class.
        Take a list of all tokens and return a list of real tokens. Here
        should be done some validations (number of tokens...) and eventually
        some parsing...
        """
        if len(tokens) < 3:
            raise template.TemplateSyntaxError(
                u"'%r' tag requires at least 2 arguments." % tokens[0])
        return tokens[1], tokens[2], tokens[3:]

    @classmethod
    def register(cls, library_register, nodename='cache', nocache_nodename='nocache'):
        """
        Register all needed templatetags, with these parameters :
            * library_register : the `register` object (result of
                `template.Library()`) in your templatetag module
            * nodename : the node to use for the cache templatetag (the default
                is "cache")
            * nocache_nodename : the node to use for the nocache templatetag
        """

        if cls in CacheTag._templatetags:
            raise RuntimeError('The adv-cache-tag class %s is already registered' % cls)

        CacheTag._templatetags[cls] = {}

        def templatetag_cache(parser, token):
            """
            Return a new Node object for the main cache templatetag
            """
            nodelist = parser.parse(('end%s' % nodename,))
            parser.delete_first_token()
            args = cls.get_template_node_arguments(token.contents.split())
            return cls.Node(nodename, nodelist, *args)

        library_register.tag(nodename, templatetag_cache)
        CacheTag._templatetags[cls]['cache'] = templatetag_cache

        def templatetag_raw(parser, token):
            """
            Return a TextNode with all html not parsed, used for templatetags
            that need to not be parsed : the `nocache` one and the `RAW` one,
            used to surround cached html (to be not parsed again)
            Based on http://www.holovaty.com/writing/django-two-phased-rendering/
            """

            # Whatever is between {% nocache %} and {% endnocache %} will be preserved as
            # raw, un-rendered template code.

            text = []
            parse_until = 'end%s' % token.contents
            tag_mapping = {
                template.TOKEN_TEXT: ('', ''),
                template.TOKEN_VAR: ('{{', '}}'),
                template.TOKEN_BLOCK: ('{%', '%}'),
                template.TOKEN_COMMENT: ('{#', '#}'),
            }
            # By the time this template tag is called, the template system has already
            # lexed the template into tokens. Here, we loop over the tokens until
            # {% endraw %} and parse them to TextNodes. We have to add the start and
            # end bits (e.g. "{{" for variables) because those have already been
            # stripped off in a previous part of the template-parsing process.
            while parser.tokens:
                token = parser.next_token()
                if token.token_type == template.TOKEN_BLOCK and token.contents == parse_until:
                    return template.TextNode(u''.join(text))
                start, end = tag_mapping[token.token_type]
                text.append(u'%s%s%s' % (start, token.contents, end))
            parser.unclosed_block_tag(parse_until)

        library_register.tag(cls.RAW_TOKEN, templatetag_raw)
        CacheTag._templatetags[cls]['raw'] = templatetag_raw

        def templatetag_nocache(parser, token):
            """
            Return a TextNode with raw html from the `nocache` templatetag,
            and surround it with `endRAW` and `RAW` (precisely
            `cls.RAW_TOKEN_END` and `cls.RAW_TOKEN_START`).
            So for
                {% nocache %}foo{% endnocache %}
            we get
                {% endRAW... %}foo{% RAW... %}
            When the main cache templatetag content will be loaded from cache,
            it will be surrounded by the same templatetags, reversed.
            So if at first we had
                {% cache %}bar{% nocache %}foo{% endnocache %}baz{% endcache %}
            The cached version will be
                bar{% endRAW... %}foo{% RAW... %}baz
            And the final html to be rendered will be
                {% RAW... %}bar{% endRAW... %}foo{% RAW... %}baz{% endRAW... %}
            And the html within `RAW` and `endRAW` will not be parsed, as wanted
            """

            # We'll load in the no-cache part all template tags and filters loaded in the main
            # template, to be able to use it when the no-cache will be rendered

            all_tags_and_filters = cls.get_all_tags_and_filters_by_function()
            available_tags = all_tags_and_filters['tags']
            available_filters = all_tags_and_filters['filters']

            needed = {}
            current_module = cls.get_templatetag_module()

            for function in parser.tags.values():
                if function in available_tags:
                    lib, name = available_tags[function]
                    if lib == current_module:
                        continue
                    needed.setdefault(lib, set()).add(name)

            for function in parser.filters.values():
                if function in available_filters:
                    lib, name = available_filters[function]
                    if lib == current_module:
                        continue
                    needed.setdefault(lib, set()).add(name)

            load_string = ''.join(
                '%sload %s from %s%s' % (
                    template.BLOCK_TAG_START,
                    ' '.join(names),
                    lib,
                    template.BLOCK_TAG_END,
                )
                for lib, names in needed.items()
            )

            node = templatetag_raw(parser, token)
            node.s = cls.RAW_TOKEN_END + load_string + node.s + cls.RAW_TOKEN_START
            return node

        library_register.tag(nocache_nodename, templatetag_nocache)
        CacheTag._templatetags['nocache'] = templatetag_nocache
