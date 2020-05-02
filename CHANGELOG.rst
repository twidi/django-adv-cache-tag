Changelog
=========

Release *v1.1.3* - ``2020-05-01``
---------------------------------
* Fix failure when using ``internal_version``
* Add a way to chose compression level
* Add support for Django 2.2 and 3.0
* Add support for Python 3.8

Release *v1.1.2* - ``2018-11-27``
---------------------------------
* Add support for Django 2.1
* Add support for Python 3.7

Release *v1.1.1* - ``2018-02-01``
---------------------------------
* Official support for Django from 1.7 to version 2.0
* Remove support for Python < 3.4

Release *v1.1.0* - ``2015-12-14``
---------------------------------
* Add support for ``None`` as a cache timeout value

Release *v1.0* - ``2015-10-29``
-------------------------------
* WARNING: internal version changed, all existing cached fragment will be reset
* Remove support for Python 2
* Remove support for Django < 1.5

Release *v0.3.0* - ``2015-12-14``
---------------------------------
* Add support for ``None`` as a cache timeout value (Python 2 version)

Release *v0.2.1* - ``2015-10-29``
---------------------------------
* Mark release 0.2.1 as only compatible with Python 2
* Mark status as ``Development Status :: 5 - Production/Stable``

Release *v0.2.0* - ``2015-10-29``
---------------------------------
* Support for Django 1.3 to 1.9 with Python 2
* Last version to support Python 2 (version 1.0 will support Python 3 only)
* Add tests
* Correct inheritance problems
* Raise exceptions if ``TEMPLATE_DEBUG`` is ``True``
* Template fragment names are resolvable from context (if new option set)
* Cache backend to use can be set in the template (as in recent Django versions)
* "nocache" blocks don't fail if they use a tag or filter loaded outside
* Still render the template fragment even if the cache fails

Release *v0.1.3* - ``2014-05-11``
---------------------------------
* Use ``hashlib`` instead of Django ``hashcompat`` (to be used in Django 1.6+)

Release *v0.1.2* - ``2013-09-06``
---------------------------------
* Add RST version of README

Release *v0.1.1* - ``2012-01-16``
---------------------------------
* Add a way to force invalidation of templates

Release *v0.1.0* - ``2012-01-15``
---------------------------------
* First version
