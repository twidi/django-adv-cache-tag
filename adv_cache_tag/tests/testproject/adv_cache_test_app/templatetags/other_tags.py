from django import template


register = template.Library()


@register.simple_tag
def insert_foo():
    return 'FoOoO'
