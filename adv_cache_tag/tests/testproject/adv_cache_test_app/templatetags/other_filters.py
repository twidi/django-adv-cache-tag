from django import template

register = template.Library()


@register.filter
def double_upper(value):
    return (value + value).upper()
