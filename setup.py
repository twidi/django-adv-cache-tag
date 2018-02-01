#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from setuptools import setup

if sys.version_info >= (3,):
    sys.stderr.write('Fatal error: django-adv-cache-tag version <1 only works with python 2. '
                     'Use version >=1.0 for python 3.\n')
    sys.exit(1)

setup()
