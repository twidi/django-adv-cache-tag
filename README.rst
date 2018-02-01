|PyPI Version| |Build Status|

django-adv-cache-tag
====================

Django advanced cache template tag:

-  versioning
-  compress
-  partial caching
-  easily extendable/customizable

Readable documentation on
http://documentup.com/twidi/django-adv-cache-tag

Introduction
------------

First, notice that the arguments of the ``{% cache %}`` templatetag
provided by ``django-adv-cache-tag`` are the same as for the default
cache templatetag included in django, so it's very easy to use this new
one.

With ``django-adv-cache-tag`` you can :

-  add a version number (int, string, date or whatever, it will be
   stringified) to your templatetag : the version will be compared to
   the cached one, and the exact same cache key will be used for the new
   cached template, avoiding keeping old unused keys in your cache,
   allowing you to cache forever.
-  avoid to be afraid of an incompatible update in our algorithm,
   because we also use an internal version number, updated only when the
   internal algorithm changes
-  define your own cache keys (or simply, just add the primary key (or
   what you want, it's a templatetag parameter) to this cache key
-  compress the data to be cached, to reduce memory consumption in your
   cache backend, and network latency (but it will use more time and cpu
   to compress/decompress, your choice)
-  choose which cache backend will be used
-  define ``{% nocache %}...{% endnocache %}`` blocks inside your cached
   template, that will only be rendered when asked (for these parts, the
   content of the template is cached, not the rendered result)
-  easily define your own algorithm, as we provide a single class (with
   short methods) you can inherit from, and simply change options or
   whatever behavior you want, and define your own tags for them
-  use a variable for the name of your cache fragment

Installation
------------

``django-adv-cache-tag`` is available on PyPI::

    pip install 'django-adv-cache-tag<1'

You must specify the version as the last one available (``>=1.0``) only support python 3.

Or you can find it on Github:
https://github.com/twidi/django-adv-cache-tag/tree/python2

(for python3 version: https://github.com/twidi/django-adv-cache-tag)

When installed, just add ``adv_cache_tag`` to your ``INSTALLED_APPS`` in
the ``settings.py`` file of your django project.

See examples in the next sections to see how it works (basically the
same way as the default django cache templatetag)

Features
--------

Versioning
~~~~~~~~~~

Description
^^^^^^^^^^^

With the default django cache templatetag, you can add as many arguments
as you want, including a version, or date, and then the cache key will
change if this version change. So your cache is updated, as expected.

But the older key is not deleted and if you have a long expire time, it
will stay there for a very long time, consuming your precious memory.

``django-adv-cache-tag`` provides a way to avoid this, while still
regenerating the cache when needed. For this, when activated, we use the
last argument passed to your templatetag as a "version number", and
remove it for the arguments used to generate the cache key.

This version will be used in the **content** of the cached template,
instead of the **key**, and when the cache exists and is loaded, the
cached version will be compared to the wanted one, and if the two match,
the cache is valid and returned, else it will be regenerated.

So if you like the principle of a unique key for a given template for a
given object/user or whatever, be sure to always use the same arguments,
except the last one, and activate the ``ADV_CACHE_VERSIONING`` setting.

Note that we also manage an internal version number, which will always
be compared to the cached one. This internal version number is only
updated when the internal algorithm of ``django-adv-cache-tag`` changes.
But you can update it to invalidate all cached templates by adding a
``ADV_CACHE_VERSION`` to your settings (our internal version and the
value from this settings will be concatenated to get the internal
version really used)

Settings
^^^^^^^^

``ADV_CACHE_VERSIONING``, default to ``False``

``ADV_CACHE_VERSION``, default to ``""``

Example
^^^^^^^

In the following template, if ``ADV_CACHE_VERSIONING`` is set to True,
the key will always be the same, based on the string
"myobj\_main\_template" and the value of ``obj.pk``, but the cached
value will be regenerated each time the ``obj.date_last_updated`` will
change.

So we set a ``expire_time`` of ``0``, to always keep the template
cached, because we now we won't have many copies (old ones and current
one) of it.

The value to set to have no expiry may depend of your cache backend (it's not always `0`).


.. code:: django

    {% load adv_cache %}
    {% cache 0 myobj_main_template obj.pk obj.date_last_updated %}
      {{ obj }}
    {% endcache %}

Primary key
~~~~~~~~~~~

Description
^^^^^^^^^^^

In the default django cache templatetag, the cache keys are like this
one ::

    :1:template.cache.your_fragment_name.64223ccf70bbb65a3a4aceac37e21016

You may want to have more explicit cache keys, so with
``django-adv-cache-tag`` you can add a "primary key" that will be added
between the fragment name and the hash ::

    :1:template.cache.your_fragment_name.your_pk.64223ccf70bbb65a3a4aceac37e21016

Although the main use of this primary key is to have one cached fragment
per object, so we can use the object primary key, you can use whatever
you want, an id, a string...

To add a primary key, simply set the ``ADV_CACHE_INCLUDE_PK`` setting to
``True``, and the first argument (after the fragment's name) will be
used as a pk.

If you want this only for a part of your cache templatetags, read the
``Extending the default cache tag`` part later in this readme (it's
easy, really).

Unlike the version, the primary key will be kept as an argument to
generate the cache key hash.

Settings
^^^^^^^^

``ADV_CACHE_INCLUDE_PK``, default to ``False``

Example
^^^^^^^

A common use of ``django-adv-cache-tag`` is to only use a primary key
and a version:

.. code:: django

    {% cache 0 myobj_main_template obj.pk obj.date_last_updated %}

Compression
~~~~~~~~~~~

Description
^^^^^^^^^^^

The default django cache templatetag simply saves the generated html in
the cache. Depending of your template, if may be a lot of html and your
cache memory will grow very quickly. Not to mention that we can have a
lot of spaces because of indentation in templates (two ways i know to
remove them without ``django-adv-cache-tag``: the ``{% spaceless %}``
templatetag, provided by django, and
`django-template-preprocessor <https://github.com/citylive/django-template-preprocessor/>`__).

``django-adv-cache-tag`` can do this for you. It is able to remove
duplicate spaces (including newlines, tabs) by replacing them by a
simple space (to keep the space behavior in html), and to compress the
html to be cached, via the ``zlib`` (and ``pickle``) module.

Of course, this cost some time and CPU cycles, but you can save a lot of
memory in your cache backend, and a lot of bandwidth, especially if your
backend is on a distant place. I haven't done any test for this, but for
some templates, the saved data can be reduced from 2 ko to less than
one.

To activate these feature, simply set to ``True`` one or both of the
settings defined below.

WARNING : If the cache backend used use pickle and its default protocol,
compression is useless because binary is not really well handled and the
final size stored in the cache will be largely bigger than the
compressed one. So check for this before activating this option. It's ok
for the default django backends (at least in 1.4), but not for
django-redis-cache, waiting for my pull-request, but you can check my
own version:
https://github.com/twidi/django-redis-cache/tree/pickle\_version

Settings
^^^^^^^^

``ADV_CACHE_COMPRESS``, default to ``False``, to activate the
compression via ``zlib``

``ADV_CACHE_COMPRESS_SPACES``, default to ``False``, to activate the
reduction of blank characters.

Example
^^^^^^^

No example since you don't have to change anything to your templatetag
call to use this, just set the settings.

Choose your cache backend
~~~~~~~~~~~~~~~~~~~~~~~~~

Description
^^^^^^^^^^^

In django, you can define many cache backends. But with the default
cache templatetag, you cannot say which one use, it will automatically
be the default one.

``django-adv-cache-tag`` can do this for your by providing a setting,
``ADV_CACHE_BACKEND`` which will take the name of a cache backend
defined in your settings. And by extending the provided ``CacheTag``
object, you can even define many backends to be used by many
templatetags, say one for heavily accessed templates, one for the
others... as you want. Read the ``Extending the default cache tag`` part
to know more about this (it's easy, really, but i already told you...)

Settings
^^^^^^^^

``ADV_CACHE_BACKEND``, default to "default"

Example
^^^^^^^

No example since, like for the compression, you don't have to change
anything to your templatetag to use this, just set the setting.

Partial caching
~~~~~~~~~~~~~~~

With the default django cache templatetag, your templates are cached and
you can't update them before display, so you can't cache big parts of
html with a little dynamic fragment in it, for the user name, the
current date or whatever. You can cheat and save two templates
surrounding your dynamic part, but you will have more accesses to your
cache backend.

``django-adv-cache-tag`` allow the use of one or many ``{% nocache %}``
blocks (closed by ``{% endnocache %}``) to put in your ``{% cache %}``
blocks. These ``{% nocache %}`` block will be saved "as is" in the
cache, while the rest of the block will be rendered to html. It's only
when the template is finally displayed that the no-cached parts will be
rendered.

You can have as many of these blocks you want.

Settings
^^^^^^^^

There is no settings for this feature, which is automatically activated.

Example
^^^^^^^

.. code:: django

    {% cache 0 myobj_main_template obj.pk obj.date_last_updated %}
        <p>This is the cached part of the template for {{ obj }}, evaluated at {% now "r" %}.</p>
        {% nocache %}
            <p>This part will be evaluated each time : {% now "r" %}</p>
        {% endnocache %}
        <p>This is another cached part</p>
    {% endcache %}

The fragment name
~~~~~~~~~~~~~~~~~

Description
^^^^^^^^^^^

The fragment name is the name to use as a base to create the cache key, and is defined just
after the expiry time.

The Django documentation states ``The name will be taken as is, do not use a variable``.

In ``django-adv-cache-tag``, by setting ``ADV_CACHE_RESOLVE_NAME`` to ``True``, a fragment name
that is not quoted will be resolved as a variable that should be in the context.

Settings
^^^^^^^^

``ADV_CACHE_RESOLVE_NAME``, default to ``False``

Example
^^^^^^^

With ``ADV_CACHE_RESOLVE_NAME`` set to ``True``, you can do this if you have a variable named
``fragment_name`` in your context:

.. code:: django

    {% cache 0 fragment_name obj.pk obj.date_last_updated %}

And if you want to pass a name, you have to surround it by quotes:

.. code:: django

    {% cache 0 "myobj_main_template" obj.pk obj.date_last_updated %}

With ``ADV_CACHE_RESOLVE_NAME`` set to ``False``, the default, the name is always seen as a string,
but if surrounded by quotes, they are removed.

In the following example, you see double-quotes, but it would be the same with single quotes, or
no quotes at all:

.. code:: django

    {% cache 0 "myobj_main_template" obj.pk obj.date_last_updated %}

Extending the default cache tag
-------------------------------

If the five settings explained in the previous sections are not enough
for you, or if you want to have a templatetag with a different behavior
as the default provided ones, you will be happy to know that
``django-adv-cache-tag`` was written with easily extending in mind.

It provides a class, ``CacheTag`` (in ``adv_cache_tag.tag``), which has
a lot of short and simple methods, and even a ``Meta`` class (idea
stolen from the django models :D ). So it's easy to override a simple
part.

All options defined in the ``Meta`` class are accessible in the class
via ``self.options.some_field``

Below we will show many ways of extending this class.

Basic override
~~~~~~~~~~~~~~

Imagine you don't want to change the default settings (all to ``False``,
and using the ``default`` backend) but want a templatetag with
versioning activated :

Create a new templatetag file (``myapp/templatetags/my_cache_tags.py``)
with this:

.. code:: python

    from adv_cache_tag.tag import CacheTag

    class VersionedCacheTag(CacheTag):
        class Meta(CacheTag.Meta):
            versioning = True

    from django import template
    register = template.Library()

    VersionedCacheTag.register(register, 'ver_cache')

With these simple lines, you now have a new templatetag to use when you
want versioning:

.. code:: django

    {% load my_cache_tags %}
    {% ver_cache 0 myobj_main_template obj.pk obj.date_last_updated %}
        obj
    {% endver_cache %}

As you see, just replace ``{% load adv_cache %}`` (or the django default
``{% load cache %}``) by ``{% load my_cache_tags %}`` (your templatetag
module), and the ``{% cache %}`` templatetag by your new defined one,
``{% ver_cache ... %}``. Don't forget to replace the closing tag too:
``{% endver_cache %}``. But the ``{% nocache %}`` will stay the same,
except if you want a new one. For this, just add a parameter to the
``register`` method:

.. code:: python

    MyCacheTag.register(register, 'ver_cache', 'ver_nocache')

.. code:: django

    {% ver_cache ... %}
        cached
        {% ver_nocache %}not cached{% endver_nocache %}
    {% endver_cache %}

Note that you can keep the name ``cache`` for your tag if you know that
you will not load in your template another templatetag module providing
a ``cache`` tag. To do so, the simplest way is:

.. code:: python

    MyCacheTag.register(register)  # 'cache' and 'nocache' are the default values

All the ``django-adv-cache-tag`` settings have a matching variable in
the ``Meta`` class, so you can override one or many of them in your own
classes. See the "Settings" part to see them.

Internal version
~~~~~~~~~~~~~~~~

When your template file is updated, the only way to invalidate all
cached versions of this template is to update the fragment name or the
arguments passed to the templatetag.

With ``django-adv-cache-tag`` you can do this with versioning, by
managing your own version as the last argument to the templatetag. But
if you want to use the power of the versioning system of
``django-adv-cache-tag``, it can be too verbose:

.. code:: django

    {% load adv_cache %}
    {% with template_version=obj.date_last_updated|stringformat:"s"|add:"v1" %}
        {% cache 0 myobj_main_template obj.pk template_version %}
        ...
        {% endcache %}
    {% endwith %}

``django-adv-cache-tag`` provides a way to do this easily, with the
``ADV_CACHE_VERSION`` setting. But by updating it, **all** cached
versions will be invalidated, not only those you updated.

To do this, simply create your own tag with a specific internal version:

.. code:: python

    class MyCacheTag(CacheTag):
        class Meta(CacheTag.Meta):
           internal_version = "v1"

    MyCacheTag.register('my_cache')

And then in your template, you can simply do

.. code:: django

    {% load my_cache_tags %}
    {% my_cache 0 myobj_main_template obj.pk obj.date_last_updated %}
    ...
    {% endmy_cache %}

Each time you update the content of your template and want invalidation,
simply change the ``internal_version`` in your ``MyCacheTag`` class (or
you can use a settings for this).

Change the cache backend
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to change the cache backend for one templatetag, it's easy:

.. code:: python

    class MyCacheTag(CacheTag):
        class Meta:
            cache_backend = 'templates'

But you can also to this by overriding a method:

.. code:: python

    from django.core.cache import get_cache

    class MyCacheTag(CacheTag):
        def get_cache_object(self):
            return get_cache('templates')

And if you want a cache backend for old objects, and another, faster,
for recent ones:

.. code:: python

    from django.core.cache import get_cache

    class MyCacheTag(CacheTag):
        class Meta:
            cache_backend = 'fast_templates'

        def get_cache_object(self):
            cache_backend = self.options.cache_backend
            if self.get_pk() < 1000:
                cache_backend = 'slow_templates'
            return get_cache(cache_backend)

The value returned by the ``get_cache_object`` should be a cache backend
object, but as we only use the ``set`` and ``get`` methods on this
object, it can be what you want if it provides these two methods. And
even more, you can override the ``cache_set`` and ``cache_get`` methods
of the ``CacheTag`` class if you don't want to use the default ``set``
and ``get`` methods of the cache backend object.

Note that we also support the django way of changing the cache backend in the template-tag, using
the ``using`` argument, to be set at the last parameter (without any space between `using` and the
name of the cache backend).

.. code:: django

    {% cache 0 myobj_main_template obj.pk obj.date_last_updated using=foo %}


Change the cache key
~~~~~~~~~~~~~~~~~~~~

The ``CacheTag`` class provides three classes to create the cache key:

-  ``get_base_cache_key``, which returns a formattable string
   ("template.%(nodename)s.%(name)s.%(pk)s.%(hash)s" by default if
   ``include_pk`` is ``True`` or
   "template.%(nodename)s.%(name)s.%(hash)s" if ``False``
-  ``get_cache_key_args``, which returns the arguments to use in the
   previous string
-  ``get_cache_key``, which combine the two

The arguments are:

-  ``nodename`` parameter is the name of the ``templatetag``: it's
   "my\_cache" in ``{% my_cache ... %}``
-  ``name`` is the "fragment name" of your templatetag, the value after
   the expire-time
-  ``pk`` is used only if ``self.options.include_pk`` is ``True``, and
   is returned by ``this.get_pk()``
-  ``hash`` is the hash of all arguments after the fragment name,
   excluding the last one which is the version number (this exclusion
   occurs only if ``self.options.versioning`` is ``True``)

If you want to remove the "template." part at the start of the cache key
(useless if you have a cache backend dedicated to template caching), you
can do this:

.. code:: python

    class MyCacheTag(CacheTag):
        def get_base_cache_key(self):
            cache_key = super(MyCacheTag, self).get_base_cache_key()
            return cache_key[len('template:'):]  # or [9:]

Add an argument to the templatetag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the templatetag provided by ``CacheTag`` takes the same
arguments as the default django cache templatetag.

If you want to add an argument, it's easy as the class provides a
``get_template_node_arguments`` method, which will work as for normal
django templatetags, taking a list of tokens, and returning ones that
will be passed to the real templatetag, a ``Node`` class tied to the
``CacheTag``.

Say you want to add a ``foo`` argument between the expire time and the
fragment name:

.. code:: python

    from django import template

    from adv_cache_tag.tag import CacheTag, Node

    class MyNode(Node):
        def __init__(self, nodename, nodelist, expire_time, foo, fragment_name, vary_on):
            """ Save the foo variable in the node (not resolved yet) """
            super(MyNode, self).__init__(self, nodename, nodelist, expire_time, fragment_name, vary_on)
            self.foo = foo


    class MyCacheTag(CacheTag):

        Node = MyNode

        def prepare_params(self):
            """ Resolve the foo variable to it's real content """
            super(MyCacheTag, self).prepare_params()
            self.foo = template.Variable(self.node.foo).resolve(self.context)

        @classmethod
        def get_template_node_arguments(cls, tokens):
            """ Check validity of tokens and return them as ready to be passed to the Node class """
            if len(tokens) < 4:
                raise template.TemplateSyntaxError(u"'%r' tag requires at least 3 arguments." % tokens[0])
            return (tokens[1], tokens[2], tokens[3], tokens[4:])

Prepare caching of templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This one is not about overriding the class, but it can be useful. When
an object is updated, it can be better to regenerate the cached template
at this moment rather than when we need to display it.

It's easy. You can do this by catching the ``post_save`` signal of your
model, or just by overriding its ``save`` method. For this example we
will use this last solution.

The only special thing is to know the path of the template where your
templatetag is. In my case, i have a template just for this (included in
other ones for general use), so it's easier to find it and regenerate it
as in this example.

As we are not in a request, we don't have the ``Request`` object here,
so context processors are not working, we must create a context object
that will be used to render the template, with all needed variables.

.. code:: python

    from django.template import loader, Context

    class MyModel(models.Model):
        # your fields

        def save(self, *args, **kwargs):
            super(MyModel, self.save(*args, **kwargs)

            template = 'path/to/my_template_file_with_my_cache_block.html'

            context = Context({
                'obj': self,

                # as you have no request, we have to add stuff from context processors manually if we need them
                'STATIC_URL': settings.STATIC_URL,

                # the line below indicates that we force regenerating the cache, even if it exists
                '__regenerate__': True,

                # the line below indicates if we only want html, without parsing the nocache parts
                '__partial__': True,

            })

            loader.get_template(template).render(context)

Load data from database before rendering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a special case. Say you want to display a list of objects but
you have only ids and versions retrieved from redis (with ``ZSET``, with
id as value and updated date (which is used as a version) as score , for
example)

If you know you always have a valid version of your template in cache,
because they are regenerated every time they are saved, as seen above,
it's fine, just add the object's primary key as the ``pk`` in your
templatetag arguments, and the cached template will be loaded.

But if it's not the case, you will have a problem: when django will
render the template, the only part of the object present in the context
is the primary key, so if you need the name or whatever field to render
the cached template, it won't work.

With ``django-adv-cache-tag`` it's easy to resolve this, as we can load
the object from the database and adding it to the context.

View
^^^^

.. code:: python

    def my_view(request):
        objects = [
            dict(
                pk=val[0],
                date_last_updated=val[1]
            )
            for val in
                redis.zrevrange('my_objects', 0, 19, withscores=True)
        ]
        return render(request, "my_results.html", dict(objects=objects))

Template "my\_results.html"
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: django

    {% for obj in objects %}
        {% include "my_result.html" %}
    {% endfor %}

Template "my\_result.html"
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: django

    {% load my_cache_tags %}
    {% my_cache 0 myobj_main_template obj.pk obj.date_last_updated %}
        {{ obj }}
    {% endmy_cache %}

Templatetag
^^^^^^^^^^^

In ``myapp/templatetags/my_cache_tags``

.. code:: python

    from my_app.models import MyModel

    class MyCacheTag(CacheTag):

        class Meta(CacheTag.Meta):
            """ Force options """
            include_pk = True
            versioning = True

        def create_content(self):
            """ If the object in context is not a real model, load it from db """
            if not isinstance(context['obj'], MyObject):
                context['obj'] = MyModel.objects.get(id=self.get_pk())
            super(MyCacheTag, self).create_content()

    MyCacheTag.register('my_cache')

Careful with this, it generates as database requests as objects to be
loaded.

And more...
~~~~~~~~~~~

If you want to do more, feel free to look at the source code of the
``CacheTag`` class (in ``tag.py``), all methods are documented.

Settings
--------

``django-adv-cache-tag`` provide 5 settings you can change. Here is the
list, with descriptions, default values, and corresponding fields in the
``Meta`` class (accessible via ``self.options.some_field`` in the
``CacheTag`` object)

-  ``ADV_CACHE_VERSIONING`` to activate versioning, default to ``False``
   (``versioning`` in the ``Meta`` class)
-  ``ADV_CACHE_COMPRESS`` to activate compression, default to ``False``
   (``compress`` in the ``Meta`` class)
-  ``ADV_CACHE_COMPRESS_SPACES`` to activate spaces compression, default
   to ``False`` (``compress_spaces`` in the ``Meta`` class)
-  ``ADV_CACHE_INCLUDE_PK`` to activate the "primary key" feature,
   default to ``False`` (``include_pk`` in the ``Meta`` class)
-  ``ADV_CACHE_BACKEND`` to choose the cache backend to use, default to
   ``"default"`` (``cache_backend`` in the ``Meta`` class)
-  ``ADV_CACHE_VERSION`` to create your own internal version (will be
   concatenated to the real internal version of
   ``django-adv-cache-tag``), default to ``""`` (``internal_version`` in
   the ``Meta`` class)

How it works
------------

Here is a quick overview on how things work in ``django-adv-cache-tag``

Partial caching
~~~~~~~~~~~~~~~

Your template :

.. code:: django

    {% load adv_cache %}
    {% cache ... %}
        foo
        {% nocache %}
            bar
        {% endnocache %}
        baz
    {% endcache %}

Cached version (we ignore versioning and compress here, just to see how
it works):

.. code:: django

    foo
    {% endRAW_xyz %}
        bar
    {% RAW_xyz %}
    baz

When cached version is loaded, we parse :

.. code:: django

    {% RAW_xyz %}
    foo
    {% endRAW_xyz %}
        bar
    {% RAW_xyz %}
    baz
    {% endRAW_xyz %}

The first ``{% RAW_xyz %}`` and the last ``{% endRAW_xyz %}`` are not
included in the cached version and added before parsing, only to save
some bytes.

Parts between ``{% RAW_xyz %}`` and ``{% endRAW_xyz %}`` are not parsed
at all (seen as a ``TextNode`` by django)

The ``xyz`` part of the ``RAW`` and ``endRAW`` templatetags depends on
the ``SECRET_KEY`` and so is unique for a given site.

It allows to avoid at max the possible collisions with parsed content in
the cached version.

We could have used ``{% nocache %}`` and ``{% endnocache %}`` instead of
``{% RAW_xyz %}`` and ``{% endRAW_xyz %}`` but in the parsed template,
stored in the cache, if the html includes one of these strings, our
final template would be broken, so we use long ones with a hash (but we
can not be sure at 100% these strings could not be in the cached html,
but for common usages it should suffice)

License
-------

``django-adv-cache-tag`` is published under the MIT License (see the
LICENSE file)

Running tests
-------------

If ``adv_cache_tag`` is in the ``INSTALLE_APPS`` of your project, simply
run::

    django-admin test adv_cache_tag

(you may want to use ``django-admin`` or ``./manage.py`` depending on
your installation)

If you are in a fresh virtualenv to work on ``adv_cache_tag``, install
the django version you want::

    pip install django

Then make the ``adv_cache_tag`` module available in your python path.
For example, with ``virtualenv-wrapper``, considering you are at the
root of the ``django-adv-cache-tag`` repository, simply do::

    add2virtualenv .

Or simply, to install all at once::

    pip install -e .[dev]

Then to run the tests, this library provides a test project, so you can
launch them this way::

    DJANGO_SETTINGS_MODULE=adv_cache_tag.tests.testproject.settings django-admin.py test adv_cache_tag

Or simply launch the ``runtests.sh`` script (it will run this exact
command)::

    ./runtests.sh

Supported versions
------------------

============== ============== ===============
Django version Python version Library version
============== ============== ===============
1.4 to 1.11    2.7            0.4
1.11, 2.0      3.4, 3.5, 3.6  1.1.1
============== ============== ==============



.. |PyPI Version| image:: https://img.shields.io/pypi/v/django-adv-cache-tag.png
   :target: https://pypi.python.org/pypi/django-adv-cache-tag
   :alt: PyPI Version
.. |Build Status| image:: https://travis-ci.org/twidi/django-adv-cache-tag.png
   :target: https://travis-ci.org/twidi/django-adv-cache-tag
   :alt: Build Status on Travis CI
