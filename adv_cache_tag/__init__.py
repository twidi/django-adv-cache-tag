"""An advanced template tag for caching in django: versioning, compress, partial caching, easy inheritance"""

from importlib.metadata import version, PackageNotFoundError


def _extract_version(package_name):
    try:
        return version(package_name.replace('_', '-'))
    except PackageNotFoundError:
        # if not installed, return a default dev version
        return '0.0.0.dev'


EXACT_VERSION = _extract_version('django_adv_cache_tag')
VERSION = tuple(int(part) for part in EXACT_VERSION.split('.') if str(part).isnumeric())
