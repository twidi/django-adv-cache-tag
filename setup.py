#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import sys

from setuptools import setup, find_packages


import adv_cache_tag

if sys.version_info >= (3,):
    sys.stderr.write('Fatal error: django-adv-cache-tag %s only works with python 2. '
                     'Use version >=1.0 for python 3.\n' % adv_cache_tag.__version__)
    sys.exit(1)

long_description = codecs.open('README.rst', "r", "utf-8").read()

setup(
    name = "django-adv-cache-tag",
    version = adv_cache_tag.__version__,
    author = adv_cache_tag.__author__,
    author_email = adv_cache_tag.__contact__,
    description = adv_cache_tag.__doc__,
    keywords = "django cache templatetag template",
    url = adv_cache_tag.__homepage__,
    download_url = "https://github.com/twidi/django-adv-cache-tag/tags",
    packages = find_packages(),
    include_package_data=True,
    license = "MIT",
    platforms=["any"],
    zip_safe=True,

    long_description = long_description,

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2 :: Only",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Framework :: Django",
        "Framework :: Django :: 1.4",
        "Framework :: Django :: 1.5",
        "Framework :: Django :: 1.6",
        "Framework :: Django :: 1.7",
        "Framework :: Django :: 1.8",
#        "Framework :: Django :: 1.9",
    ],
)
