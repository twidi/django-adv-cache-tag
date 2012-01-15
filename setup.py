#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs

from setuptools import setup, find_packages

import adv_cache_tag

long_description = codecs.open('README.md', "r", "utf-8").read()

setup(
    name = "django-adv-cache-tag",
    version = adv_cache_tag.__version__,
    author = adv_cache_tag.__author__,
    author_email = adv_cache_tag.__contact__,
    description = adv_cache_tag.__doc__,
    keywords = "django cache templatetag template",
    url = adv_cache_tag.__homepage__,
    download_url = "https://github.com/twidi/django-adv-cache-tag/downloads",
    packages = find_packages(),
    include_package_data=True,
    license = "MIT",
    platforms=["any"],
    zip_safe=True,

    long_description = long_description,

    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Framework :: Django",
    ],
)
