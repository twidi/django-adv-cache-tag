# django-adv-cache-tag / Copyright Stephane "TWidi" Angel <s.angel@twidi.com> / MIT License

from django import template
from adv_cache_tag.tag import CacheTag

register = template.Library()

# Register the default class with the "cache" and "nocache" block names
CacheTag.register(register);
