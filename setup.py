#!/usr/bin/env python

import sys

from setuptools import setup



if sys.version_info < (3,):
    sys.stderr.write('Fatal error: django-adv-cache-tag version >1 only works with python 3. '
                     'Use version <1.0 for python 2.\n')
    sys.exit(1)

setup()
