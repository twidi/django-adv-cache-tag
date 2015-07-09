try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from django.core.cache import caches
except ImportError:
    # Django < 1.7
    from django.core.cache import get_cache
else:
    def get_cache(name):
        return caches[name]

try:
    from django.template import BLOCK_TAG_START
except ImportError:
    # Django >= 1.8
    from django.template import base as template
else:
    from django import template
