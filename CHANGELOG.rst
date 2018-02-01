Changelog
=========

Release *v0.4.0* - ``2018-02-01``
---------------------------------
* Official support for Django up to version 1.11.x
* Remove support for Python 2.6

Release *v0.3.0* - ``2015-12-14``
---------------------------------
* Add support for `None` as a cache timeout value

Release *v0.2.1* - ``2015-10-29``
---------------------------------
* Mark release 0.2.1 as only compatible with python 2
* Mark status as `Development Status :: 5 - Production/Stable`

Release *v0.2.0* - ``2015-10-29``
---------------------------------
* Support for django 1.3 to 1.9 with python 2
* Last version to support python 2 (version 1.0 will support python 3 only)
* Add tests
* Correct inheritance problems
* Raise exceptions if TEMPLATE_DEBUG is True
* Template fragment names are resolvable from context (if new option set)
* Cache backend to use can be set in the template (as in recent Django versions)
* "nocache" blocks don't fail if they use a tag or filter loaded outside
* Still render the template fragment even if the cache fails

Release *v0.1.3* - ``2014-05-11``
---------------------------------
* Use hashlib instead of django hashcompat (to be used in django 1.6+)

Release *v0.1.2* - ``2013-09-06``
---------------------------------
* Add RST version of README

Release *v0.1.1* - ``2012-01-16``
---------------------------------
* Add a way to force invalidation of templates

Release *v0.1.0* - ``2012-01-15``
---------------------------------
* First version
