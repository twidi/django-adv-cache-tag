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
